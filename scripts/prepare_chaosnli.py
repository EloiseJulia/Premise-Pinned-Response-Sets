from __future__ import annotations

import argparse
import json
from pathlib import Path

from pprs.data.chaosnli import download_source, prepare_sample
from pprs.data.schema import SampleManifest, TaskConfig


def _write_manifest(manifest: SampleManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **manifest.model_dump(mode="json"),
        "manifest_id": manifest.manifest_id(),
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--task-config",
        type=Path,
        action="append",
        required=True,
    )
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed"),
    )
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=Path("configs/samples"),
    )
    args = parser.parse_args()

    for config_path in args.task_config:
        config = TaskConfig.model_validate_json(
            config_path.read_text(encoding="utf-8")
        )
        stem = config.task_id.value.replace("_", "-")
        source_path = args.raw_dir / f"{stem}.jsonl"
        parquet_path = args.processed_dir / f"{stem}.parquet"
        manifest_path = args.manifest_dir / f"{stem}-seed42.json"
        download_source(config, source_path)
        manifest = prepare_sample(config, source_path, parquet_path)
        _write_manifest(manifest, manifest_path)
        print(f"{config.task_id.value}: {manifest.manifest_id()}")


if __name__ == "__main__":
    main()
