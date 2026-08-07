from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ReproducibilityManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prereg_tag: str = Field(min_length=1)
    prereg_git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    reporting_git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    input_sha256: dict[str, str]
    output_sha256: dict[str, str]
    rebuild_commands: tuple[str, ...] = Field(min_length=1)
    caveats: tuple[str, ...] = Field(min_length=1)

    def manifest_id(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_reproducibility_manifest(
    *,
    prereg_tag: str,
    prereg_git_sha: str,
    reporting_git_sha: str,
    trusted_raw_manifest_sha256: str,
    trusted_raw_manifest_id: str,
    inputs: dict[str, Path],
    outputs: dict[str, Path],
) -> ReproducibilityManifest:
    missing = [
        str(path)
        for path in (*inputs.values(), *outputs.values())
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"reproducibility inputs/outputs missing: {missing}"
        )
    return ReproducibilityManifest(
        prereg_tag=prereg_tag,
        prereg_git_sha=prereg_git_sha,
        reporting_git_sha=reporting_git_sha,
        input_sha256={
            name: sha256_file(path) for name, path in inputs.items()
        },
        output_sha256={
            name: sha256_file(path) for name, path in outputs.items()
        },
        rebuild_commands=(
            "uv sync --dev",
            (
                "uv run python scripts/prepare_chaosnli.py "
                "--task-config configs/tasks/chaosnli-snli.json "
                "--task-config configs/tasks/chaosnli-mnli.json"
            ),
            "uv run python scripts/prepare_summeval.py",
            (
                "uv run python scripts/run_confirmatory_analysis.py "
                f"--trusted-raw-manifest-sha256 {trusted_raw_manifest_sha256} "
                f"--trusted-raw-manifest-id {trusted_raw_manifest_id}"
            ),
            "uv run python scripts/render_results.py",
            "uv run python scripts/build_reproducibility.py",
        ),
        caveats=(
            "Google service IDs are exact call-time slugs but not dated deployment IDs.",
            "SummEval has eight human ratings per item; NLI has one hundred.",
            "Premise-pilot and smoke line reviews were AI reviews under owner preauthorization, not human owner line review.",
            "The study measures an observable failure mode, not deployment prevalence.",
        ),
    )
