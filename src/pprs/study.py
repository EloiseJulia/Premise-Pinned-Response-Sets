from __future__ import annotations

import asyncio
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path
from urllib.request import urlopen

from pydantic import BaseModel, ConfigDict, Field

from pprs.cache import ParquetRecordCache
from pprs.collector import CollectionContext, Collector
from pprs.data.schema import DatasetRecord, TaskId
from pprs.pilot import load_and_validate_sample
from pprs.prompts import (
    PromptOption,
    load_task_framings,
    matched_placebo_components,
    render_disclosure_prompt,
    render_forced_choice_prompt,
    render_full_grid_prompt,
    render_pinned_prompt,
    render_placebo_prompt,
    render_response_set_prompt,
)
from pprs.providers.base import (
    CallIdentity,
    ProviderRequest,
)
from pprs.providers.litellm import (
    LiteLLMProvider,
    LiteLLMProviderSettings,
)
from pprs.records.schema import (
    ElicitationPath,
    PinAssignment,
    RawResult,
)
from pprs.seeding import SeedRegistry


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StudySummary(StrictModel):
    run_tag: str
    git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    prereg_tag: str
    subset_id: str
    models: tuple[str, ...]
    temperatures: tuple[float, ...]
    total_records: int
    parse_status_counts: dict[str, int]
    path_counts: dict[str, int]
    provider_invocations: int
    planning_errors: tuple[str, ...]
    system_fingerprints: dict[str, tuple[str, ...]]
    cache_keys: tuple[str, ...]


class FullGridSummary(StrictModel):
    total_records: int
    provider_invocations: int
    parse_status_counts: dict[str, int]
    planning_errors: tuple[str, ...]
    cache_keys: tuple[str, ...]


def task_options(task: TaskId) -> tuple[PromptOption, ...]:
    if task in {TaskId.CHAOSNLI_SNLI, TaskId.CHAOSNLI_MNLI}:
        return (
            PromptOption(
                token="A",
                label="Entailment",
                description="The statement follows from the context.",
            ),
            PromptOption(
                token="B",
                label="Neutral",
                description="The relationship is unresolved by the context.",
            ),
            PromptOption(
                token="C",
                label="Contradiction",
                description="The statement conflicts with the context.",
            ),
        )
    return (
        PromptOption(
            token="A",
            label="Relevant",
            description=(
                "The summary captures important source content with minimal "
                "redundancy."
            ),
        ),
        PromptOption(
            token="B",
            label="Not Relevant",
            description=(
                "The summary misses key content or includes excessive "
                "irrelevant information."
            ),
        ),
    )


def load_subset_records(
    subset_path: Path,
) -> tuple[str, tuple[DatasetRecord, ...]]:
    subset = json.loads(subset_path.read_text(encoding="utf-8"))
    sample_paths = {
        TaskId.CHAOSNLI_SNLI: (
            Path("data/processed/chaosnli-snli.parquet"),
            Path("configs/samples/chaosnli-snli-seed42.json"),
        ),
        TaskId.CHAOSNLI_MNLI: (
            Path("data/processed/chaosnli-mnli.parquet"),
            Path("configs/samples/chaosnli-mnli-seed42.json"),
        ),
        TaskId.SUMMEVAL_RELEVANCE: (
            Path("data/processed/summeval-relevance.parquet"),
            Path("configs/samples/summeval-relevance-seed42.json"),
        ),
    }
    selected = []
    for task in TaskId:
        records, _manifest, _manifest_id = load_and_validate_sample(
            *sample_paths[task]
        )
        by_id = {record.item_id: record for record in records}
        requested = subset["items"][task.value]
        if len(set(requested)) != len(requested):
            raise ValueError("subset IDs must be unique")
        try:
            selected.extend(by_id[item_id] for item_id in requested)
        except KeyError as exc:
            raise ValueError("subset item is absent from sample manifest") from exc
    return subset["subset_id"], tuple(selected)


def canonical_models_roster_sha256(api_base: str) -> str:
    with urlopen(
        f"{api_base.rstrip('/')}/models",
        timeout=10,
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return models_roster_sha256_from_payload(payload)


def models_roster_sha256_from_payload(payload: dict) -> str:
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("models endpoint has no data list")
    canonical_rows = [
        {
            "id": row.get("id"),
            "owned_by": row.get("owned_by"),
            "created": row.get("created"),
        }
        for row in sorted(data, key=lambda row: row.get("id", ""))
    ]
    canonical = json.dumps(
        canonical_rows,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _coordinates(
    *,
    record: DatasetRecord,
    model: str,
    temperature: float,
    path: str,
    sample_id: int,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    values: dict[str, object] = {
        "task": record.task.value,
        "item_id": record.item_id,
        "model": model,
        "temperature": temperature,
        "path": path,
        "sample_id": sample_id,
    }
    if extra:
        values.update(extra)
    return values


async def run_study_subset(
    *,
    api_base: str,
    git_sha: str,
    prereg_tag: str,
    subset_id: str,
    records: tuple[DatasetRecord, ...],
    models: tuple[str, ...],
    temperatures: tuple[float, ...],
    cache_dir: Path,
    run_tag: str,
    expected_models_roster_hash: str,
    forced_repetitions: int = 20,
    response_set_repetitions: int = 20,
    disclosure_repetitions: int = 3,
    concurrency: int = 8,
) -> tuple[tuple[RawResult, ...], StudySummary]:
    actual_roster_hash = await asyncio.to_thread(
        canonical_models_roster_sha256,
        api_base,
    )
    if actual_roster_hash != expected_models_roster_hash:
        raise RuntimeError(
            "ghc-api model roster hash changed: "
            f"{actual_roster_hash}"
        )
    framings = load_task_framings(
        Path("configs/prompts/task-framings.json")
    )
    provider = LiteLLMProvider(
        LiteLLMProviderSettings(
            api_base=api_base,
            allow_unauthenticated_local=True,
        )
    )
    collector = Collector(provider, ParquetRecordCache(cache_dir))
    semaphore = asyncio.Semaphore(concurrency)
    fingerprint_lock = asyncio.Lock()
    observed_fingerprint: dict[str, str] = {}
    seed_registry = SeedRegistry()

    async def collect(
        request: ProviderRequest,
        context: CollectionContext,
    ) -> RawResult:
        async with semaphore:
            result = await collector.collect(request, context)
            if result.system_fingerprint:
                async with fingerprint_lock:
                    existing = observed_fingerprint.get(
                        result.model_snapshot
                    )
                    if (
                        existing is not None
                        and existing != result.system_fingerprint
                    ):
                        raise RuntimeError(
                            "system fingerprint drift for "
                            f"{result.model_snapshot}: {existing} -> "
                            f"{result.system_fingerprint}"
                        )
                    observed_fingerprint[result.model_snapshot] = (
                        result.system_fingerprint
                    )
            return result

    fixed_jobs = []
    for record in records:
        framing = framings[record.task]
        options = task_options(record.task)
        valid_tokens = tuple(option.token for option in options)
        for model in models:
            for temperature in temperatures:
                for path, repetitions in (
                    (ElicitationPath.FORCED_CHOICE, forced_repetitions),
                    (ElicitationPath.MULTI_LABEL, response_set_repetitions),
                ):
                    for sample_id in range(repetitions):
                        coords = _coordinates(
                            record=record,
                            model=model,
                            temperature=temperature,
                            path=path.value,
                            sample_id=sample_id,
                        )
                        option_seed = seed_registry.get(
                            "option_permutation",
                            coords,
                        )
                        rendered = (
                            render_forced_choice_prompt(
                                framing,
                                record.inputs,
                                options,
                                option_seed,
                            )
                            if path is ElicitationPath.FORCED_CHOICE
                            else render_response_set_prompt(
                                framing,
                                record.inputs,
                                options,
                                option_seed,
                            )
                        )
                        call_seed = seed_registry.get("call", coords)
                        request = ProviderRequest(
                            identity=CallIdentity(
                                rendered_prompt=rendered.text,
                                model_snapshot=model,
                                temperature=temperature,
                                top_p=1.0,
                                seed=call_seed,
                                response_format=rendered.response_format,
                            ),
                            provider="openai",
                        )
                        context = CollectionContext(
                            run_tag=run_tag,
                            git_sha=git_sha,
                            prereg_tag=prereg_tag,
                            task=record.task,
                            item_id=record.item_id,
                            judge_id=model,
                            path=path,
                            sample_id=sample_id,
                            prompt_template_id=rendered.template_id,
                            option_permutation_seed=option_seed,
                            valid_tokens=valid_tokens,
                        )
                        fixed_jobs.append(collect(request, context))

    fixed_results = list(await asyncio.gather(*fixed_jobs))

    disclosure_jobs = []
    disclosure_coordinates = []
    for record in records:
        framing = framings[record.task]
        valid_tokens = (
            ("A", "B")
            if record.task is TaskId.SUMMEVAL_RELEVANCE
            else ("A", "B", "C")
        )
        for model in models:
            for temperature in temperatures:
                for premise_round in range(disclosure_repetitions):
                    coords = _coordinates(
                        record=record,
                        model=model,
                        temperature=temperature,
                        path="premise_disclosure",
                        sample_id=premise_round,
                    )
                    rendered = render_disclosure_prompt(
                        framing,
                        record.inputs,
                        "premise-disclosure-inventory-v2",
                    )
                    request = ProviderRequest(
                        identity=CallIdentity(
                            rendered_prompt=rendered.text,
                            model_snapshot=model,
                            temperature=temperature,
                            top_p=1.0,
                            seed=seed_registry.get("call", coords),
                            response_format=rendered.response_format,
                        ),
                        provider="openai",
                    )
                    context = CollectionContext(
                        run_tag=run_tag,
                        git_sha=git_sha,
                        prereg_tag=prereg_tag,
                        task=record.task,
                        item_id=record.item_id,
                        judge_id=model,
                        path=ElicitationPath.PREMISE_PINNED,
                        sample_id=premise_round,
                        premise_round=premise_round,
                        prompt_template_id=rendered.template_id,
                        option_permutation_seed=0,
                        valid_tokens=valid_tokens,
                    )
                    disclosure_jobs.append(collect(request, context))
                    disclosure_coordinates.append(
                        (record, model, temperature, premise_round)
                    )

    disclosure_results = list(await asyncio.gather(*disclosure_jobs))
    pin_jobs = []
    planning_errors = []
    for disclosure, coordinates in zip(
        disclosure_results,
        disclosure_coordinates,
        strict=True,
    ):
        record, model, temperature, premise_round = coordinates
        if disclosure.parsed_premises is None:
            continue
        framing = framings[record.task]
        options = task_options(record.task)
        valid_tokens = tuple(option.token for option in options)
        for premise in disclosure.parsed_premises:
            for value_index, premise_value in enumerate(
                premise.candidate_values
            ):
                extra = {
                    "premise_round": premise_round,
                    "premise_id": premise.premise_id,
                    "premise_value_index": value_index,
                }
                coords = _coordinates(
                    record=record,
                    model=model,
                    temperature=temperature,
                    path="premise_pinned",
                    sample_id=value_index,
                    extra=extra,
                )
                option_seed = seed_registry.get(
                    "option_permutation",
                    coords,
                )
                try:
                    rendered = render_pinned_prompt(
                        framing,
                        record.inputs,
                        options,
                        option_seed,
                        premise_statement=premise.statement,
                        premise_value=premise_value,
                    )
                    placebo = render_placebo_prompt(
                        framing,
                        record.inputs,
                        options,
                        option_seed,
                        matched_premise_statement=premise.statement,
                        matched_premise_value=premise_value,
                    )
                    placebo_statement, placebo_value = (
                        matched_placebo_components(
                            premise.statement,
                            premise_value,
                        )
                    )
                except ValueError as exc:
                    planning_errors.append(
                        f"{record.task.value}/{record.item_id}/{model}/"
                        f"{premise_round}/{premise.premise_id}/"
                        f"{value_index}: {exc}"
                    )
                    continue

                for path, prompt, premise_id, stored_value in (
                    (
                        ElicitationPath.PREMISE_PINNED,
                        rendered,
                        premise.premise_id,
                        premise_value,
                    ),
                    (
                        ElicitationPath.PLACEBO,
                        placebo,
                        f"placebo:{premise.premise_id}",
                        placebo_value,
                    ),
                ):
                    path_coords = {**coords, "path": path.value}
                    request = ProviderRequest(
                        identity=CallIdentity(
                            rendered_prompt=prompt.text,
                            model_snapshot=model,
                            temperature=temperature,
                            top_p=1.0,
                            seed=seed_registry.get("call", path_coords),
                            response_format=prompt.response_format,
                        ),
                        provider="openai",
                    )
                    context = CollectionContext(
                        run_tag=run_tag,
                        git_sha=git_sha,
                        prereg_tag=prereg_tag,
                        task=record.task,
                        item_id=record.item_id,
                        judge_id=model,
                        path=path,
                        sample_id=value_index,
                        premise_id=premise_id,
                        premise_type=premise.premise_type,
                        premise_value=stored_value,
                        premise_round=premise_round,
                        prompt_template_id=prompt.template_id,
                        option_permutation_seed=option_seed,
                        valid_tokens=valid_tokens,
                    )
                    pin_jobs.append(collect(request, context))

    pin_results = list(await asyncio.gather(*pin_jobs))
    results = tuple(
        [*fixed_results, *disclosure_results, *pin_results]
    )
    status_counts = Counter(result.parse_status.value for result in results)
    path_counts = Counter(result.path.value for result in results)
    fingerprints: dict[str, set[str]] = defaultdict(set)
    for result in results:
        if result.system_fingerprint:
            fingerprints[result.model_snapshot].add(
                result.system_fingerprint
            )
    summary = StudySummary(
        run_tag=run_tag,
        git_sha=git_sha,
        prereg_tag=prereg_tag,
        subset_id=subset_id,
        models=models,
        temperatures=temperatures,
        total_records=len(results),
        parse_status_counts=dict(sorted(status_counts.items())),
        path_counts=dict(sorted(path_counts.items())),
        provider_invocations=provider.invocation_count,
        planning_errors=tuple(planning_errors),
        system_fingerprints={
            model: tuple(sorted(values))
            for model, values in sorted(fingerprints.items())
        },
        cache_keys=tuple(result.cache_key for result in results),
    )
    return results, summary


async def run_full_grid_ablation(
    *,
    api_base: str,
    expected_models_roster_hash: str,
    git_sha: str,
    prereg_tag: str,
    disclosure_results: Sequence[RawResult],
    records: tuple[DatasetRecord, ...],
    cache_dir: Path,
    run_tag: str,
    expected_fingerprints: dict[str, tuple[str, ...]],
    concurrency: int = 8,
) -> tuple[tuple[RawResult, ...], FullGridSummary]:
    actual_roster_hash = await asyncio.to_thread(
        canonical_models_roster_sha256,
        api_base,
    )
    if actual_roster_hash != expected_models_roster_hash:
        raise RuntimeError("ghc-api model roster hash changed")
    records_by_id = {
        (record.task, record.item_id): record for record in records
    }
    framings = load_task_framings(
        Path("configs/prompts/task-framings.json")
    )
    provider = LiteLLMProvider(
        LiteLLMProviderSettings(
            api_base=api_base,
            allow_unauthenticated_local=True,
        )
    )
    collector = Collector(provider, ParquetRecordCache(cache_dir))
    semaphore = asyncio.Semaphore(concurrency)
    seed_registry = SeedRegistry()
    fingerprint_lock = asyncio.Lock()
    observed_fingerprint: dict[str, str] = {}
    for model, values in expected_fingerprints.items():
        if len(values) > 1:
            raise RuntimeError(
                f"primary phase already observed fingerprint drift for {model}"
            )
        if values:
            observed_fingerprint[model] = values[0]
    jobs = []
    planning_errors = []

    async def collect(
        request: ProviderRequest,
        context: CollectionContext,
    ) -> RawResult:
        async with semaphore:
            result = await collector.collect(request, context)
            if result.system_fingerprint:
                async with fingerprint_lock:
                    existing = observed_fingerprint.get(
                        result.model_snapshot
                    )
                    if (
                        existing is not None
                        and existing != result.system_fingerprint
                    ):
                        raise RuntimeError(
                            "system fingerprint drift for "
                            f"{result.model_snapshot}"
                        )
                    observed_fingerprint[result.model_snapshot] = (
                        result.system_fingerprint
                    )
            return result

    for disclosure in disclosure_results:
        if (
            disclosure.path is not ElicitationPath.PREMISE_PINNED
            or disclosure.parsed_premises is None
            or disclosure.premise_id is not None
        ):
            continue
        record = records_by_id.get((disclosure.task, disclosure.item_id))
        if record is None:
            continue
        premises = disclosure.parsed_premises
        if len(premises) > 4:
            planning_errors.append(
                f"{record.task.value}/{record.item_id}: more than four premises"
            )
            continue
        options = task_options(record.task)
        valid_tokens = tuple(option.token for option in options)
        value_products = itertools.product(
            *(premise.candidate_values for premise in premises)
        )
        for combo_index, values in enumerate(value_products):
            assignments = tuple(
                PinAssignment(
                    premise_id=premise.premise_id,
                    premise_type=premise.premise_type,
                    premise_value=value,
                )
                for premise, value in zip(premises, values, strict=True)
            )
            canonical_assignments = json.dumps(
                [
                    assignment.model_dump(mode="json")
                    for assignment in assignments
                ],
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            coords = {
                "task": record.task.value,
                "item_id": record.item_id,
                "model": disclosure.model_snapshot,
                "temperature": disclosure.temperature,
                "path": "full_grid",
                "premise_round": disclosure.premise_round,
                "combo_index": combo_index,
                "assignments": canonical_assignments,
            }
            option_seed = seed_registry.get(
                "option_permutation",
                coords,
            )
            try:
                rendered = render_full_grid_prompt(
                    framings[record.task],
                    record.inputs,
                    options,
                    option_seed,
                    assignments=tuple(
                        (premise.statement, value)
                        for premise, value in zip(
                            premises,
                            values,
                            strict=True,
                        )
                    ),
                )
            except ValueError as exc:
                planning_errors.append(
                    f"{record.task.value}/{record.item_id}/"
                    f"{disclosure.judge_id}/{combo_index}: {exc}"
                )
                continue
            request = ProviderRequest(
                identity=CallIdentity(
                    rendered_prompt=rendered.text,
                    model_snapshot=disclosure.model_snapshot,
                    temperature=disclosure.temperature,
                    top_p=1.0,
                    seed=seed_registry.get("call", coords),
                    response_format=rendered.response_format,
                ),
                provider="openai",
            )
            context = CollectionContext(
                run_tag=run_tag,
                git_sha=git_sha,
                prereg_tag=prereg_tag,
                task=record.task,
                item_id=record.item_id,
                judge_id=disclosure.model_snapshot,
                path=ElicitationPath.PREMISE_PINNED,
                sample_id=combo_index,
                premise_id="__full_grid__",
                premise_type=None,
                premise_value=canonical_assignments,
                premise_round=disclosure.premise_round,
                pinning_assignments=assignments,
                prompt_template_id=rendered.template_id,
                option_permutation_seed=option_seed,
                valid_tokens=valid_tokens,
            )
            jobs.append(collect(request, context))

    results = tuple(await asyncio.gather(*jobs))
    counts = Counter(result.parse_status.value for result in results)
    return results, FullGridSummary(
        total_records=len(results),
        provider_invocations=provider.invocation_count,
        parse_status_counts=dict(sorted(counts.items())),
        planning_errors=tuple(planning_errors),
        cache_keys=tuple(result.cache_key for result in results),
    )
