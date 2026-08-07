from __future__ import annotations

import argparse
import random
import time
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

from pprs.records.schema import RawResult


def snapshot(
    cache_dir: Path,
    *,
    sample_size: int = 500,
) -> dict:
    files = list(cache_dir.glob("*.parquet"))
    sampled = files.copy()
    random.Random(42).shuffle(sampled)
    sampled = sampled[:sample_size]
    records = [
        RawResult.model_validate(pq.read_table(path).to_pylist()[0])
        for path in sampled
    ]
    return {
        "records": len(files),
        "bytes": sum(path.stat().st_size for path in files),
        "sampled": len(records),
        "status_counts": dict(
            Counter(record.parse_status.value for record in records)
        ),
        "model_status_counts": {
            f"{model}|{status}": count
            for (model, status), count in Counter(
                (
                    record.model_snapshot,
                    record.parse_status.value,
                )
                for record in records
            ).items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("artifacts/wp7-full-v3/cache"),
    )
    parser.add_argument("--interval", type=int, default=0)
    args = parser.parse_args()
    while True:
        print(snapshot(args.cache_dir), flush=True)
        if args.interval <= 0:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
