from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


TRACKED_INPUTS = (
    "开题报告-Premise-Pinned-Response-Sets-实施规格.md",
    "configs/runs/confirmatory-v1.json",
    "configs/prompts/task-framings.json",
    "configs/tasks/chaosnli-snli.json",
    "configs/tasks/chaosnli-mnli.json",
    "configs/tasks/summeval-relevance.json",
    "configs/samples/chaosnli-snli-seed42.json",
    "configs/samples/chaosnli-mnli-seed42.json",
    "configs/samples/summeval-relevance-seed42.json",
    "configs/samples/smoke-v1.json",
    "configs/samples/full-grid-ablation-v1.json",
    "docs/experiments/preregistration.md",
    "docs/experiments/deviations.md",
    "docs/experiments/wp4-pilot-review.md",
    "docs/experiments/wp4-leakage-audit.md",
    "docs/research/model-snapshots.md",
    "src/pprs/prompts.py",
    "src/pprs/providers/base.py",
    "src/pprs/providers/litellm.py",
    "src/pprs/records/schema.py",
    "src/pprs/analysis/metrics.py",
    "src/pprs/analysis/inference.py",
    "src/pprs/analysis/runner.py",
    "src/pprs/analysis/response_sets.py",
    "src/pprs/leakage_audit.py",
    "src/pprs/study.py",
    "src/pprs/smoke_gate.py",
    "src/pprs/freeze.py",
    "src/pprs/seeding.py",
    "scripts/run_wp6_smoke.py",
    "scripts/review_wp6_smoke.py",
    "scripts/run_wp7_full.py",
    "scripts/run_confirmatory_analysis.py",
    "uv.lock",
)

ARTIFACT_INPUTS = (
    "artifacts/wp4-pilot-rerun1/summary.json",
    "artifacts/wp4-pilot-rerun1/review.json",
    "artifacts/wp4-pilot-v2/summary.json",
    "artifacts/wp4-pilot-v2/review.json",
    "artifacts/wp4-leakage-audit-v5/summary.json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expanded_tracked_inputs() -> tuple[str, ...]:
    discovered = {
        str(path).replace("\\", "/")
        for root in (
            Path("src/pprs"),
            Path("scripts"),
        )
        for path in root.rglob("*.py")
    }
    return tuple(sorted(set(TRACKED_INPUTS) | discovered))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="pprs-prereg-v3")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("configs/runs/confirmatory-v3.freeze.json"),
    )
    args = parser.parse_args()
    tracked = {
        path: _sha256(Path(path)) for path in expanded_tracked_inputs()
    }
    artifacts = {path: _sha256(Path(path)) for path in ARTIFACT_INPUTS}
    payload = {
        "freeze_manifest_id": "confirmatory-v3-freeze",
        "prereg_tag": args.tag,
        "tracked_file_sha256": tracked,
        "artifact_sha256": artifacts,
        "dynamic_rendered_prompt_identity": {
            "rule": "each rendered prompt is hashed into the six-field call cache key and included in the run prompt ledger",
            "renderer_file": "src/pprs/prompts.py",
            "selected_template_id": "premise-disclosure-inventory-v2"
        }
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    payload["manifest_sha256"] = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    print(payload["manifest_sha256"])


if __name__ == "__main__":
    main()
