from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from pprs.pilot_review import load_review, write_review


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("artifacts/wp4-pilot/summary.json"),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("artifacts/wp4-pilot/cache"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/wp4-pilot/review.json"),
    )
    args = parser.parse_args()
    review = asyncio.run(load_review(args.summary, args.cache_dir))
    write_review(review, args.output)
    print(args.output)
    print(review.category_counts)


if __name__ == "__main__":
    main()
