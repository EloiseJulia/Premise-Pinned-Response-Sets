from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from pprs.freeze import validate_freeze
from pprs.pilot import load_and_validate_sample
from pprs.smoke_gate import validate_smoke_gate
from pprs.run_manifest import (
    create_raw_run_manifest,
    write_prompt_ledger,
    write_raw_inventory,
    write_run_manifest,
    sha256_file,
)
from pprs.study import (
    load_subset_records,
    run_full_grid_ablation,
    run_study_subset,
)
from pprs.data.schema import TaskId

ROSTER_HASH = "0f17e867c0fd3d36c30232982bd4e43a30d31bbb1dd65d64d72ad38839513ac0"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", required=True)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("artifacts/wp7-full-v3/cache"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/wp7-full-v3/summary.json"),
    )
    parser.add_argument("--concurrency", type=int, default=16)
    args = parser.parse_args()
    git_sha = validate_freeze(
        freeze_path=Path("configs/runs/confirmatory-v3.freeze.json"),
        expected_tag="pprs-prereg-v3",
    )
    validate_smoke_gate(
        summary_path=Path("artifacts/wp6-smoke-v2/summary.json"),
        review_path=Path("artifacts/wp6-smoke-v2/review-20.json"),
        approval_path=Path(
            "artifacts/wp6-smoke-v2/review-approval.json"
        ),
        expected_git_sha="280a6f46e4d3a66ca38e2747abfa7524642a5f4c",
        run_manifest_path=Path(
            "artifacts/wp6-smoke-v2/run-manifest.json"
        ),
        expected_prereg_tag="pprs-prereg-v2",
    )
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
    records = tuple(
        record
        for task in TaskId
        for record in load_and_validate_sample(*sample_paths[task])[0]
    )
    results, primary = asyncio.run(
        run_study_subset(
            api_base=args.api_base,
            expected_models_roster_hash=ROSTER_HASH,
            git_sha=git_sha,
            prereg_tag="pprs-prereg-v3",
            subset_id="confirmatory-v1",
            records=records,
            models=(
                "gpt-5.4",
                "gpt-4o-mini-2024-07-18",
                "gemini-3.1-pro-preview",
                "gemini-3.5-flash",
            ),
            temperatures=(0.0, 0.7),
            cache_dir=args.cache_dir,
            run_tag="wp7-full-v3",
            concurrency=args.concurrency,
        )
    )
    _subset_id, grid_records = load_subset_records(
        Path("configs/samples/full-grid-ablation-v1.json")
    )
    disclosures = tuple(
        result
        for result in results
        if result.path.value == "premise_pinned"
        and result.premise_id is None
    )
    _grid_results, grid = asyncio.run(
        run_full_grid_ablation(
            api_base=args.api_base,
            expected_models_roster_hash=ROSTER_HASH,
            git_sha=git_sha,
            prereg_tag="pprs-prereg-v3",
            disclosure_results=disclosures,
            records=grid_records,
            cache_dir=args.cache_dir,
            run_tag="wp7-full-grid-v3",
            expected_fingerprints=primary.system_fingerprints,
            concurrency=args.concurrency,
        )
    )
    payload = {
        "primary": primary.model_dump(mode="json"),
        "full_grid": grid.model_dump(mode="json"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    all_results = tuple([*results, *_grid_results])
    raw_inventory_path = args.output.parent / "raw-records.jsonl"
    prompt_ledger_path = args.output.parent / "prompt-ledger.json"
    write_raw_inventory(all_results, raw_inventory_path)
    write_prompt_ledger(all_results, prompt_ledger_path)
    manifest = create_raw_run_manifest(
        results=all_results,
        config=json.loads(
            Path("configs/runs/confirmatory-v1.json").read_text()
        ),
        run_tag=primary.run_tag,
        git_sha=git_sha,
        prereg_tag="pprs-prereg-v3",
        output_files={
            "summary": args.output,
            "raw_inventory": raw_inventory_path,
            "prompt_ledger": prompt_ledger_path,
        },
    )
    run_manifest_path = args.output.parent / "run-manifest.json"
    write_run_manifest(
        manifest,
        run_manifest_path,
    )
    print("trusted_raw_manifest_sha256", sha256_file(run_manifest_path))
    print("trusted_raw_manifest_id", manifest.manifest_id())
    print(args.output)


if __name__ == "__main__":
    main()
