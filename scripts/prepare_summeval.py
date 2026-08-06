from __future__ import annotations

import json
from pathlib import Path

from pprs.data.chaosnli import download_source
from pprs.data.schema import TaskConfig
from pprs.data.summeval import prepare_sample


def main() -> None:
    config = TaskConfig.model_validate_json(
        Path("configs/tasks/summeval-relevance.json").read_text(
            encoding="utf-8"
        )
    )
    source = download_source(
        config,
        Path("data/raw/summeval-relevance.csv"),
    )
    manifest = prepare_sample(
        config,
        source,
        Path("data/processed/summeval-relevance.parquet"),
    )
    payload = {
        **manifest.model_dump(mode="json"),
        "manifest_id": manifest.manifest_id(),
    }
    output = Path("configs/samples/summeval-relevance-seed42.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"{config.task_id.value}: {manifest.manifest_id()}")


if __name__ == "__main__":
    main()
