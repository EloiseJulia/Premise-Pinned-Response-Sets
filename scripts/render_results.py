from __future__ import annotations

import argparse
from pathlib import Path

from pprs.reporting import render_all


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--analysis",
        type=Path,
        default=Path("artifacts/wp7-full-v3/analysis.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/wp7-full-v3/figures"),
    )
    args = parser.parse_args()
    for name, path in render_all(args.analysis, args.output_dir).items():
        print(name, path)


if __name__ == "__main__":
    main()
