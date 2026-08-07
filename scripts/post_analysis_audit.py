from __future__ import annotations

import argparse
from pathlib import Path

from pprs.post_analysis_audit import (
    build_post_analysis_supplement,
    write_post_analysis_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument(
        "--subset",
        type=Path,
        default=Path("configs/samples/full-grid-ablation-v1.json"),
    )
    args = parser.parse_args()
    supplement = build_post_analysis_supplement(
        args.artifact_root,
        args.subset,
    )
    supplement_path = args.artifact_root / "audit-supplement.json"
    manifest_path = args.artifact_root / "post-analysis-manifest.json"
    write_post_analysis_manifest(
        supplement,
        supplement_path,
        manifest_path,
    )
    print(supplement_path)
    print(manifest_path)


if __name__ == "__main__":
    main()
