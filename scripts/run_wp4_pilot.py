from __future__ import annotations

import argparse
import asyncio
import subprocess
from pathlib import Path

from pprs.data.schema import TaskId
from pprs.pilot import (
    load_and_validate_sample,
    run_pilot,
    select_pilot_records,
    write_pilot_summary,
)


def _require_committed_pprs_assets() -> None:
    subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--"],
        check=True,
    )
    subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        check=True,
    )
    untracked = subprocess.check_output(
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "configs",
            "docs",
            "src",
            "tests",
            "scripts",
            "pyproject.toml",
            "uv.lock",
            "README.md",
            ".gitignore",
        ],
        text=True,
    ).strip()
    if untracked:
        raise RuntimeError(
            "pilot assets must be committed before model calls: "
            f"{untracked}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", required=True)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("artifacts/wp4-pilot/cache"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("artifacts/wp4-pilot/summary.json"),
    )
    parser.add_argument(
        "--run-tag",
        default="wp4-prompt-pilot-20260807",
    )
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    _require_committed_pprs_assets()
    git_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()
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
    records_by_task = {}
    sample_manifest_ids = {}
    for task, (parquet_path, manifest_path) in sample_paths.items():
        task_records, _manifest, manifest_id = load_and_validate_sample(
            parquet_path,
            manifest_path,
        )
        records_by_task[task] = task_records
        sample_manifest_ids[task] = manifest_id
    records = select_pilot_records(records_by_task)
    _results, summary = asyncio.run(
        run_pilot(
            api_base=args.api_base,
            git_sha=git_sha,
            records=records,
            cache_dir=args.cache_dir,
            run_tag=args.run_tag,
            sample_manifest_ids=sample_manifest_ids,
            concurrency=args.concurrency,
        )
    )
    write_pilot_summary(summary, args.summary)
    print(args.summary)
    print(summary.parse_status_counts)


if __name__ == "__main__":
    main()
