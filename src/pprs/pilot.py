from __future__ import annotations

import asyncio
import json
from collections import Counter
from pathlib import Path
from typing import Iterable

import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field

from pprs.cache import ParquetRecordCache
from pprs.collector import CollectionContext, Collector
from pprs.data.chaosnli import record_content_sha256, sha256_file
from pprs.data.schema import (
    DatasetRecord,
    SampleManifest,
    TaskId,
)
from pprs.prompts import (
    disclosure_template_ids,
    load_task_framings,
    render_disclosure_prompt,
)
from pprs.providers.base import (
    CallIdentity,
    ProviderRequest,
    ResponseFormat,
)
from pprs.providers.litellm import (
    LiteLLMProvider,
    LiteLLMProviderSettings,
)
from pprs.records.schema import ElicitationPath, ParseStatus, RawResult

PILOT_TASK_COUNTS = {
    TaskId.CHAOSNLI_SNLI: 7,
    TaskId.CHAOSNLI_MNLI: 7,
    TaskId.SUMMEVAL_RELEVANCE: 6,
}
PILOT_MODELS = ("gpt-5.4", "gemini-3.5-flash")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PilotCell(StrictModel):
    task: TaskId
    item_id: str
    model_snapshot: str
    template_id: str
    seed: int


class PilotSummary(StrictModel):
    run_tag: str
    git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    models: tuple[str, ...]
    template_ids: tuple[str, ...]
    task_counts: dict[TaskId, int]
    sample_manifest_ids: dict[TaskId, str]
    pilot_item_ids: dict[TaskId, tuple[str, ...]]
    total_cells: int
    parse_status_counts: dict[str, int]
    result_cache_keys: tuple[str, ...]


def load_dataset_records(path: Path) -> list[DatasetRecord]:
    rows = pq.read_table(path).to_pylist()
    return [DatasetRecord.model_validate(row) for row in rows]


def load_and_validate_sample(
    parquet_path: Path,
    manifest_path: Path,
) -> tuple[list[DatasetRecord], SampleManifest, str]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    recorded_manifest_id = payload.pop("manifest_id")
    manifest = SampleManifest.model_validate(payload)
    if manifest.manifest_id() != recorded_manifest_id:
        raise ValueError("sample manifest ID does not match its content")
    if sha256_file(parquet_path) != manifest.parquet_sha256:
        raise ValueError("sample Parquet hash does not match manifest")
    records = load_dataset_records(parquet_path)
    if tuple(record.item_id for record in records) != manifest.ordered_item_ids:
        raise ValueError("sample Parquet item order does not match manifest")
    if record_content_sha256(records) != manifest.record_content_sha256:
        raise ValueError("sample record content does not match manifest")
    return records, manifest, recorded_manifest_id


def select_pilot_records(
    records_by_task: dict[TaskId, list[DatasetRecord]],
) -> tuple[DatasetRecord, ...]:
    selected = []
    for task, count in PILOT_TASK_COUNTS.items():
        records = records_by_task.get(task)
        if records is None or len(records) < count:
            raise ValueError(f"not enough records for {task.value}")
        selected.extend(records[:count])
    if len({(record.task, record.item_id) for record in selected}) != 20:
        raise ValueError("pilot items must be unique within task")
    return tuple(selected)


def build_pilot_cells(
    records: Iterable[DatasetRecord],
    models: tuple[str, ...] = PILOT_MODELS,
    template_ids: tuple[str, ...] = disclosure_template_ids(),
) -> tuple[PilotCell, ...]:
    cells = []
    for item_index, record in enumerate(records):
        for model_index, model in enumerate(models):
            for template_index, template_id in enumerate(template_ids):
                seed = (
                    42
                    + item_index * 100
                    + model_index * 10
                    + template_index
                )
                cells.append(
                    PilotCell(
                        task=record.task,
                        item_id=record.item_id,
                        model_snapshot=model,
                        template_id=template_id,
                        seed=seed,
                    )
                )
    return tuple(cells)


async def run_pilot(
    *,
    api_base: str,
    git_sha: str,
    records: tuple[DatasetRecord, ...],
    cache_dir: Path,
    run_tag: str,
    sample_manifest_ids: dict[TaskId, str],
    concurrency: int = 4,
) -> tuple[tuple[RawResult, ...], PilotSummary]:
    if concurrency <= 0:
        raise ValueError("concurrency must be positive")
    framings = load_task_framings(
        Path("configs/prompts/task-framings.json")
    )
    records_by_identity = {
        (record.task, record.item_id): record for record in records
    }
    cells = build_pilot_cells(records)
    semaphore = asyncio.Semaphore(concurrency)
    provider = LiteLLMProvider(
        LiteLLMProviderSettings(
            api_base=api_base,
            allow_unauthenticated_local=True,
        )
    )
    collector = Collector(provider, ParquetRecordCache(cache_dir))

    async def collect_cell(cell: PilotCell) -> RawResult:
        record = records_by_identity[(cell.task, cell.item_id)]
        rendered = render_disclosure_prompt(
            framings[cell.task],
            record.inputs,
            cell.template_id,
        )
        valid_tokens = (
            ("A", "B")
            if cell.task is TaskId.SUMMEVAL_RELEVANCE
            else ("A", "B", "C")
        )
        request = ProviderRequest(
            identity=CallIdentity(
                rendered_prompt=rendered.text,
                model_snapshot=cell.model_snapshot,
                temperature=0.0,
                top_p=1.0,
                seed=cell.seed,
                response_format=ResponseFormat.PREMISE_DISCLOSURE_JSON,
            ),
            provider="openai",
        )
        context = CollectionContext(
            run_tag=run_tag,
            git_sha=git_sha,
            prereg_tag=None,
            task=cell.task,
            item_id=cell.item_id,
            judge_id=cell.model_snapshot,
            path=ElicitationPath.PREMISE_PINNED,
            sample_id=0,
            premise_round=0,
            prompt_template_id=cell.template_id,
            option_permutation_seed=0,
            valid_tokens=valid_tokens,
        )
        async with semaphore:
            return await collector.collect(request, context)

    results = tuple(await asyncio.gather(*(collect_cell(cell) for cell in cells)))
    counts = Counter(result.parse_status.value for result in results)
    summary = PilotSummary(
        run_tag=run_tag,
        git_sha=git_sha,
        models=PILOT_MODELS,
        template_ids=disclosure_template_ids(),
        task_counts=PILOT_TASK_COUNTS,
        sample_manifest_ids=sample_manifest_ids,
        pilot_item_ids={
            task: tuple(
                record.item_id for record in records if record.task is task
            )
            for task in PILOT_TASK_COUNTS
        },
        total_cells=len(cells),
        parse_status_counts=dict(sorted(counts.items())),
        result_cache_keys=tuple(result.cache_key for result in results),
    )
    return results, summary


def write_pilot_summary(summary: PilotSummary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            summary.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
