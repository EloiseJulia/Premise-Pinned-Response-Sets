from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from pprs.smoke_review import build_review


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("artifacts/wp6-smoke-v2/summary.json"),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("artifacts/wp6-smoke-v2/cache"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/wp6-smoke-v2/review-20.json"),
    )
    args = parser.parse_args()
    payload = asyncio.run(build_review(args.summary, args.cache_dir))
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
