from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path

from pprs.data.schema import TaskId
from pprs.leakage_audit import (
    audit_record,
    select_audit_records,
)
from pprs.pilot import load_and_validate_sample
from pprs.prompts import load_task_framings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", required=True)
    parser.add_argument(
        "--template-id",
        default="premise-disclosure-inventory-v2",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("artifacts/wp4-leakage-audit/cache"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/wp4-leakage-audit/summary.json"),
    )
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    paths = {
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
    records_by_task = {
        task: load_and_validate_sample(parquet, manifest)[0]
        for task, (parquet, manifest) in paths.items()
    }
    records = select_audit_records(records_by_task)
    framings = load_task_framings(
        Path("configs/prompts/task-framings.json")
    )

    async def run():
        semaphore = asyncio.Semaphore(args.concurrency)

        async def one(index, record):
            async with semaphore:
                return await audit_record(
                    api_base=args.api_base,
                    framing=framings[record.task],
                    record=record,
                    disclosure_template_id=args.template_id,
                    seed=9000 + index,
                    cache_dir=args.cache_dir,
                )

        return await asyncio.gather(
            *(one(index, record) for index, record in enumerate(records))
        )

    results = asyncio.run(run())
    counts = Counter(result.status for result in results)
    leakage = Counter(
        str(result.parsed.leakage).lower()
        for result in results
        if result.parsed is not None
    )
    payload = {
        "template_id": args.template_id,
        "auditor_model": "mai-code-1-flash-picker",
        "total": len(results),
        "status_counts": dict(sorted(counts.items())),
        "leakage_counts": dict(sorted(leakage.items())),
        "records": [result.model_dump(mode="json") for result in results],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    print(payload["status_counts"], payload["leakage_counts"])


if __name__ == "__main__":
    main()
