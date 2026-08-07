from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from pprs.reproducibility import build_reproducibility_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("artifacts/wp7-full-v3"),
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data/processed"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/wp8/reproducibility-manifest.json"),
    )
    args = parser.parse_args()
    root = args.artifact_root
    raw_manifest_path = root / "run-manifest.json"
    raw_manifest_payload = json.loads(
        raw_manifest_path.read_text(encoding="utf-8")
    )
    manifest = build_reproducibility_manifest(
        prereg_tag="pprs-prereg-v3",
        prereg_git_sha=subprocess.check_output(
            ["git", "rev-parse", "pprs-prereg-v3^{}"],
            text=True,
        ).strip(),
        reporting_git_sha=subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
        ).strip(),
        trusted_raw_manifest_sha256=hashlib.sha256(
            raw_manifest_path.read_bytes()
        ).hexdigest(),
        trusted_raw_manifest_id=raw_manifest_payload["manifest_id"],
        inputs={
            "raw_run_manifest": raw_manifest_path,
            "raw_inventory": root / "raw-records.jsonl",
            "prompt_ledger": root / "prompt-ledger.json",
            "analysis": root / "analysis.json",
            "specification_curve": (
                root / "specification-curve-manifest.json"
            ),
            "snli_parquet": (
                args.data_root / "chaosnli-snli.parquet"
            ),
            "mnli_parquet": (
                args.data_root / "chaosnli-mnli.parquet"
            ),
            "summeval_parquet": (
                args.data_root / "summeval-relevance.parquet"
            ),
            "analysis_upstream": (
                root / "analysis-upstream_behavior.json"
            ),
            "analysis_semantic": (
                root / "analysis-semantic_aligned.json"
            ),
            "manifest_upstream": (
                root / "manifest-upstream_behavior.json"
            ),
            "manifest_semantic": (
                root / "manifest-semantic_aligned.json"
            ),
            "audit_supplement": root / "audit-supplement.json",
            "post_analysis_manifest": (
                root / "post-analysis-manifest.json"
            ),
        },
        outputs={
            "figure_1": root / "figures/figure-1-beta-scatter.png",
            "figure_2": (
                root / "figures/figure-2-seed-context-entropy.png"
            ),
            "figure_3": root / "figures/figure-3-regret.png",
            "regret_surface": root / "figures/regret-surface.csv",
            "high_risk": root / "figures/high-risk-items.json",
            "technical_brief": Path("docs/brief/technical-brief.md"),
            "email_draft": Path("docs/brief/email-draft.md"),
            "experiment_notes_zh": Path(
                "docs/brief/pprs-experiment-notes-zh.md"
            ),
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **manifest.model_dump(mode="json"),
        "manifest_id": manifest.manifest_id(),
    }
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
