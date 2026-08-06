from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from pprs.data.schema import (
    DatasetRecord,
    SampleManifest,
    TaskConfig,
    TaskId,
)

SAMPLING_ALGORITHM = (
    "pandas.DataFrame.sample(n=150, random_state=42);"
    "preserve-sampled-order"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def verify_source_object(config: TaskConfig, path: Path) -> None:
    actual = git_blob_sha1(path)
    if actual != config.source_object_id:
        raise ValueError(
            f"source object mismatch: expected {config.source_object_id}, "
            f"got {actual}"
        )


def download_source(config: TaskConfig, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        verify_source_object(config, destination)
        return destination
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with urlopen(config.source_download_uri, timeout=60) as response:
        temporary.write_bytes(response.read())
    try:
        verify_source_object(config, temporary)
    except ValueError:
        temporary.unlink(missing_ok=True)
        raise
    temporary.replace(destination)
    return destination


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid JSONL at line {line_number}"
                ) from exc
            if not isinstance(row, dict):
                raise ValueError(f"line {line_number} is not a JSON object")
            rows.append(row)
    if not rows:
        raise ValueError("ChaosNLI source file is empty")
    return rows


def sample_rows(
    rows: list[dict],
    config: TaskConfig,
) -> list[dict]:
    if config.task_id not in {
        TaskId.CHAOSNLI_SNLI,
        TaskId.CHAOSNLI_MNLI,
    }:
        raise ValueError("ChaosNLI sampler only accepts SNLI or MNLI")
    if config.sampling_seed is None:
        raise ValueError("sampling seed must be locked")
    if len(rows) < config.sample_size:
        raise ValueError("source has fewer rows than the locked sample size")
    frame = pd.DataFrame(rows)
    sampled = frame.sample(
        n=config.sample_size,
        random_state=config.sampling_seed,
    ).reset_index(drop=True)
    return sampled.to_dict(orient="records")


def to_dataset_record(row: dict, config: TaskConfig) -> DatasetRecord:
    uid = row.get("uid")
    counter = row.get("label_counter")
    example = row.get("example")
    if not isinstance(uid, str) or not uid:
        raise ValueError("ChaosNLI row has no valid uid")
    if not isinstance(counter, dict) or not isinstance(example, dict):
        raise ValueError("ChaosNLI row lacks labels or example fields")
    try:
        source_counts = {
            "A": counter.get("e", 0),
            "B": counter.get("n", 0),
            "C": counter.get("c", 0),
        }
        premise = example["premise"]
        hypothesis = example["hypothesis"]
    except KeyError as exc:
        raise ValueError("ChaosNLI row has malformed task fields") from exc
    if any(type(value) is not int for value in source_counts.values()):
        raise ValueError("ChaosNLI label counts must be integers")
    if any(value < 0 for value in source_counts.values()):
        raise ValueError("ChaosNLI label counts cannot be negative")
    if (
        not isinstance(premise, str)
        or not premise.strip()
        or not isinstance(hypothesis, str)
        or not hypothesis.strip()
    ):
        raise ValueError("ChaosNLI premise and hypothesis must be strings")
    counts = source_counts
    inputs = {
        "context": premise,
        "statement": hypothesis,
    }
    distribution = {
        token: count / config.ratings_per_item
        for token, count in counts.items()
    }
    return DatasetRecord(
        task=config.task_id,
        item_id=uid,
        source_dataset=config.source_dataset,
        source_revision=config.source_revision,
        source_object_id=config.source_object_id,
        source_split=config.source_split,
        source_original_id=uid,
        sampling_seed=config.sampling_seed,
        inputs=inputs,
        human_label_counts=counts,
        human_label_distribution=distribution,
        ratings_per_item=config.ratings_per_item,
        license_identifier=config.license.identifier,
        license_source=config.license.source_url,
        data_card_source=config.data_card.source_url,
        data_card_revision=config.data_card.source_revision,
        data_card_blob=config.data_card.source_blob,
    )


def record_content_sha256(records: list[DatasetRecord]) -> str:
    canonical = "\n".join(
        json.dumps(
            record.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        for record in records
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_records_parquet(
    records: list[DatasetRecord],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [record.model_dump(mode="json") for record in records]
    table = pa.Table.from_pylist(rows)
    temporary = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(table, temporary)
    temporary.replace(path)


def prepare_sample(
    config: TaskConfig,
    source_path: Path,
    parquet_path: Path,
) -> SampleManifest:
    verify_source_object(config, source_path)
    rows = load_jsonl(source_path)
    sampled_rows = sample_rows(rows, config)
    records = [to_dataset_record(row, config) for row in sampled_rows]
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
