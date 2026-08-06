from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pprs.manifests.schema import RunManifest
from pprs.records.schema import RawResult


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rendered_prompt_ledger_hash(results: tuple[RawResult, ...]) -> str:
    ledger = _prompt_ledger(results)
    canonical = json.dumps(
        ledger,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _prompt_ledger(results: tuple[RawResult, ...]) -> list[dict]:
    return [
        {
            "cache_key": result.cache_key,
            "prompt_hash": result.prompt_hash,
            "task": result.task.value,
            "item_id": result.item_id,
            "judge_id": result.judge_id,
            "path": result.path.value,
            "sample_id": result.sample_id,
            "premise_round": result.premise_round,
            "premise_id": result.premise_id,
            "premise_value": result.premise_value,
        }
        for result in sorted(results, key=lambda result: result.cache_key)
    ]


def write_prompt_ledger(
    results: tuple[RawResult, ...],
    path: Path,
) -> None:
    path.write_text(
        json.dumps(
            _prompt_ledger(results),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_raw_inventory(
    results: tuple[RawResult, ...],
    path: Path,
) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for result in sorted(results, key=lambda item: item.cache_key):
            handle.write(
                json.dumps(
                    result.model_dump(mode="json"),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            )


def create_raw_run_manifest(
    *,
    results: tuple[RawResult, ...],
    config: dict,
    run_tag: str,
    git_sha: str,
    prereg_tag: str,
    output_files: dict[str, Path],
) -> RunManifest:
    task_ids = tuple(config["tasks"])
    dataset_revisions = {
        task: json.loads(
            Path(f"configs/tasks/{_task_filename(task)}").read_text()
        )["source_revision"]
        for task in task_ids
    }
    sample_hashes = {
        task: json.loads(
            Path(f"configs/samples/{_sample_filename(task)}").read_text()
        )["record_content_sha256"]
        for task in task_ids
    }
    task_config_hashes = {
        task: sha256_file(
            Path(f"configs/tasks/{_task_filename(task)}")
        )
        for task in task_ids
    }
    template_hashes = {
        "task-framings": sha256_file(
            Path("configs/prompts/task-framings.json")
        ),
        "prompt-renderer": sha256_file(Path("src/pprs/prompts.py")),
    }
    ledger_hash = rendered_prompt_ledger_hash(results)
    return RunManifest(
        manifest_role="raw_collection",
        run_tag=run_tag,
        git_sha=git_sha,
        prereg_tag=prereg_tag,
        dataset_revisions=dataset_revisions,
        sampled_item_list_hashes=sample_hashes,
        task_config_hashes=task_config_hashes,
        prompt_template_hashes=template_hashes,
        rendered_prompt_ledger_hashes={
            task: ledger_hash for task in task_ids
        },
        model_provider_map={
            model["model_snapshot"]: "local_ghc_api"
            for model in config["models"]
            if model["model_snapshot"]
            in {result.model_snapshot for result in results}
        },
        temperatures=tuple(config["temperatures"]),
        top_ps=(config["top_p"],),
        seeds=tuple(sorted({result.seed for result in results})),
        response_formats=tuple(
            sorted(
                {
                    _response_format_for_result(result)
                    for result in results
                }
            )
        ),
        option_permutation_policy=(
            config["option_permutation"]["seed_policy"]
        ),
        option_permutation_seeds=tuple(
            sorted({result.option_permutation_seed for result in results})
        ),
        path_repetitions={
            key: value.get(
                "repetitions",
                value.get("repetitions_per_premise_value", 1),
            )
            for key, value in config["paths"].items()
        },
        summ_eval_polarity=None,
        output_locations={
            key: str(path) for key, path in output_files.items()
        },
        output_hashes={
            key: sha256_file(path) for key, path in output_files.items()
        },
    )


def write_run_manifest(manifest: RunManifest, path: Path) -> None:
    payload = {
        **manifest.model_dump(mode="json"),
        "manifest_id": manifest.manifest_id(),
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_raw_run_manifest(
    path: Path,
    *,
    expected_git_sha: str,
    trusted_manifest_sha256: str | None = None,
    trusted_manifest_id: str | None = None,
    expected_prereg_tag: str = "pprs-prereg-v3",
) -> RunManifest:
    if (
        trusted_manifest_sha256 is not None
        and sha256_file(path) != trusted_manifest_sha256
    ):
        raise ValueError("raw run manifest differs from trusted SHA-256")
    payload = json.loads(path.read_text(encoding="utf-8"))
    manifest_id = payload.pop("manifest_id")
    if trusted_manifest_id is not None and manifest_id != trusted_manifest_id:
        raise ValueError("raw run manifest differs from trusted manifest ID")
    manifest = RunManifest.model_validate(payload)
    if manifest.manifest_role != "raw_collection":
        raise ValueError("expected a raw collection manifest")
    if manifest.manifest_id() != manifest_id:
        raise ValueError("raw run manifest ID does not match")
    if manifest.git_sha != expected_git_sha:
        raise ValueError("raw run manifest Git SHA differs from freeze")
    if manifest.prereg_tag != expected_prereg_tag:
        raise ValueError("raw run manifest preregistration tag differs")
    for key, location in manifest.output_locations.items():
        output_path = Path(location)
        if sha256_file(output_path) != manifest.output_hashes[key]:
            raise ValueError(f"raw run output hash differs: {key}")
    ledger_path = Path(manifest.output_locations["prompt_ledger"])
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    canonical = json.dumps(
        ledger,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    ledger_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if set(manifest.rendered_prompt_ledger_hashes.values()) != {
        ledger_hash
    }:
        raise ValueError("rendered prompt ledger hash differs")
    return manifest


def _task_filename(task: str) -> str:
    return {
        "chaosnli_snli": "chaosnli-snli.json",
        "chaosnli_mnli": "chaosnli-mnli.json",
        "summeval_relevance": "summeval-relevance.json",
    }[task]


def _sample_filename(task: str) -> str:
    return {
        "chaosnli_snli": "chaosnli-snli-seed42.json",
        "chaosnli_mnli": "chaosnli-mnli-seed42.json",
        "summeval_relevance": "summeval-relevance-seed42.json",
    }[task]


def _response_format_for_result(result: RawResult) -> str:
    if result.path.value == "multi_label":
        return "response_set_json_v1"
    if (
        result.path.value == "premise_pinned"
        and result.premise_id is None
    ):
        return "premise_disclosure_json_v1"
    return "forced_choice_json_v1"
