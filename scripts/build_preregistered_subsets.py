from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _load_ids(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["ordered_item_ids"]


def _write(payload: dict, path: Path) -> None:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    payload["subset_hash"] = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    samples = Path("configs/samples")
    ids = {
        "chaosnli_snli": _load_ids(
            samples / "chaosnli-snli-seed42.json"
        ),
        "chaosnli_mnli": _load_ids(
            samples / "chaosnli-mnli-seed42.json"
        ),
        "summeval_relevance": _load_ids(
            samples / "summeval-relevance-seed42.json"
        ),
    }
    smoke = {
        "subset_id": "smoke-v1",
        "selection_policy": "first committed sample-manifest IDs",
        "items": {
            "chaosnli_snli": ids["chaosnli_snli"][:4],
            "chaosnli_mnli": ids["chaosnli_mnli"][:3],
            "summeval_relevance": ids["summeval_relevance"][:3],
        },
    }
    full_grid = {
        "subset_id": "full-grid-ablation-v1",
        "selection_policy": "first 20 committed sample-manifest IDs per task",
        "items": {
            task: task_ids[:20] for task, task_ids in ids.items()
        },
    }
    _write(smoke, samples / "smoke-v1.json")
    _write(full_grid, samples / "full-grid-ablation-v1.json")


if __name__ == "__main__":
    main()
