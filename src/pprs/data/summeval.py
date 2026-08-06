from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from pprs.data.chaosnli import (
    SAMPLING_ALGORITHM,
    record_content_sha256,
    sha256_file,
    verify_source_object,
    write_records_parquet,
)
from pprs.data.schema import (
    DatasetRecord,
    SampleManifest,
    TaskConfig,
    TaskId,
)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("SummEval source file is empty")
    return rows


def sample_rows(
    rows: list[dict[str, str]],
    config: TaskConfig,
) -> list[dict[str, str]]:
    if config.task_id is not TaskId.SUMMEVAL_RELEVANCE:
        raise ValueError("SummEval sampler requires the relevance task")
    frame = pd.DataFrame(rows).reset_index(names="_source_row_index")
    sampled = frame.sample(
        n=config.sample_size,
        random_state=config.sampling_seed,
    ).reset_index(drop=True)
    return sampled.to_dict(orient="records")


def to_dataset_record(
    row: dict[str, str],
    config: TaskConfig,
    *,
    row_index: int,
) -> DatasetRecord:
    article_id = row.get("id")
    article = row.get("article")
    summary = row.get("summary")
    if not all(
        isinstance(value, str) and value.strip()
        for value in (article_id, article, summary)
    ):
        raise ValueError("SummEval row lacks nonempty ID/article/summary")
    try:
        source_counts = {
            "relevance_0": _parse_integer_count(row["relevance_0"]),
            "relevance_1": _parse_integer_count(row["relevance_1"]),
        }
    except KeyError as exc:
        raise ValueError("SummEval row lacks relevance counts") from exc
    source_original_id = f"{article_id}::row-{row_index}"
    distribution = {
        key: count / config.ratings_per_item
        for key, count in source_counts.items()
    }
    return DatasetRecord(
        task=config.task_id,
        item_id=source_original_id,
        source_dataset=config.source_dataset,
        source_revision=config.source_revision,
        source_object_id=config.source_object_id,
        source_split=config.source_split,
        source_original_id=source_original_id,
        sampling_seed=config.sampling_seed,
        inputs={"article": article, "summary": summary},
        human_label_counts=source_counts,
        human_label_distribution=distribution,
        ratings_per_item=config.ratings_per_item,
        license_identifier=config.license.identifier,
        license_source=config.license.source_url,
        data_card_source=config.data_card.source_url,
        data_card_revision=config.data_card.source_revision,
        data_card_blob=config.data_card.source_blob,
    )


def _parse_integer_count(value: str) -> int:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("SummEval counts must be numeric") from exc
    if not numeric.is_integer() or numeric < 0:
        raise ValueError("SummEval counts must be nonnegative integers")
    return int(numeric)


def prepare_sample(
    config: TaskConfig,
    source_path: Path,
    parquet_path: Path,
) -> SampleManifest:
    verify_source_object(config, source_path)
    rows = load_csv(source_path)
    sampled = sample_rows(rows, config)
    records = []
    for sampled_row in sampled:
        matching_index = int(sampled_row.pop("_source_row_index"))
        records.append(
            to_dataset_record(
                sampled_row,
                config,
                row_index=matching_index,
            )
        )
    write_records_parquet(records, parquet_path)
    return SampleManifest(
        task=config.task_id,
        source_revision=config.source_revision,
        source_object_id=config.source_object_id,
        source_file_sha256=sha256_file(source_path),
        sampling_seed=config.sampling_seed,
        sampling_algorithm=SAMPLING_ALGORITHM,
        sample_size=config.sample_size,
        ordered_item_ids=tuple(record.item_id for record in records),
        record_content_sha256=record_content_sha256(records),
        parquet_sha256=sha256_file(parquet_path),
    )
