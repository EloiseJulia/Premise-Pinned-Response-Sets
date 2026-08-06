from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from pathlib import Path

from pprs.freeze import validate_freeze
from pprs.run_manifest import (
    create_raw_run_manifest,
    write_prompt_ledger,
    write_raw_inventory,
    write_run_manifest,
)
from pprs.smoke_review import build_review
from pprs.study import load_subset_records, run_study_subset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", required=True)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("artifacts/wp6-smoke-v2/cache"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("artifacts/wp6-smoke-v2/summary.json"),
    )
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()
    git_sha = validate_freeze(
        freeze_path=Path(
            "configs/runs/confirmatory-v2.freeze.json"
        ),
        expected_tag="pprs-prereg-v2",
    )
    subset_id, records = load_subset_records(
        Path("configs/samples/smoke-v1.json")
    )
    _results, first_summary = asyncio.run(
        run_study_subset(
            api_base=args.api_base,
            git_sha=git_sha,
            prereg_tag="pprs-prereg-v2",
            subset_id=subset_id,
            records=records,
            models=("gpt-5.4", "gemini-3.5-flash"),
            temperatures=(0.0, 0.7),
            cache_dir=args.cache_dir,
            run_tag="wp6-smoke-v2",
            expected_models_roster_hash=(
                "0f17e867c0fd3d36c30232982bd4e43a30d31bbb1dd65d64d72ad38839513ac0"
            ),
            concurrency=args.concurrency,
        )
    )
    parse_success = (
        first_summary.parse_status_counts.get("ok", 0)
        / first_summary.total_records
    )
    if parse_success < 0.95:
        raise RuntimeError(
            f"smoke parse success {parse_success:.3f} is below 0.95"
        )
    if first_summary.planning_errors:
        raise RuntimeError("smoke contains premise-planning errors")
    _cached_results, second_summary = asyncio.run(
        run_study_subset(
            api_base=args.api_base,
            git_sha=git_sha,
            prereg_tag="pprs-prereg-v2",
            subset_id=subset_id,
            records=records,
            models=("gpt-5.4", "gemini-3.5-flash"),
            temperatures=(0.0, 0.7),
            cache_dir=args.cache_dir,
            run_tag="wp6-smoke-v2",
            expected_models_roster_hash=(
                "0f17e867c0fd3d36c30232982bd4e43a30d31bbb1dd65d64d72ad38839513ac0"
            ),
            concurrency=args.concurrency,
        )
    )
    if second_summary.provider_invocations != 0:
        raise RuntimeError("smoke rerun cache hit rate is below 100%")
    payload = {
        "parse_success": parse_success,
        "cache_rerun_provider_invocations": (
            second_summary.provider_invocations
        ),
        "first_run": first_summary.model_dump(mode="json"),
        "second_run": second_summary.model_dump(mode="json"),
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(payload, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    review_path = args.summary.parent / "review-20.json"
    review_payload = asyncio.run(build_review(args.summary, args.cache_dir))
    review_path.write_text(
        json.dumps(
            review_payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    raw_inventory_path = args.summary.parent / "raw-records.jsonl"
    prompt_ledger_path = args.summary.parent / "prompt-ledger.json"
    write_raw_inventory(_results, raw_inventory_path)
    write_prompt_ledger(_results, prompt_ledger_path)
    manifest = create_raw_run_manifest(
        results=_results,
        config=json.loads(
            Path("configs/runs/confirmatory-v1.json").read_text()
        ),
        run_tag=first_summary.run_tag,
        git_sha=git_sha,
        prereg_tag="pprs-prereg-v2",
        output_files={
            "summary": args.summary,
            "review": review_path,
            "raw_inventory": raw_inventory_path,
            "prompt_ledger": prompt_ledger_path,
        },
    )
    manifest_path = args.summary.parent / "run-manifest.json"
    write_run_manifest(manifest, manifest_path)
    print(args.summary)
    print(first_summary.parse_status_counts)
    print(first_summary.path_counts)
    print("provider_invocations", first_summary.provider_invocations)
    print("planning_errors", len(first_summary.planning_errors))
    print("parse_success", parse_success)
    print("rerun_provider_invocations", second_summary.provider_invocations)
    print("review_packet", review_path)
    print("run_manifest", manifest_path)


if __name__ == "__main__":
    main()
