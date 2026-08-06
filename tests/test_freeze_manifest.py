from scripts.build_freeze_manifest import (
    ARTIFACT_INPUTS,
    TRACKED_INPUTS,
    expanded_tracked_inputs,
)


def test_freeze_manifest_covers_required_identity_files() -> None:
    required = {
        "configs/runs/confirmatory-v1.json",
        "docs/experiments/preregistration.md",
        "docs/experiments/deviations.md",
        "src/pprs/prompts.py",
        "src/pprs/analysis/response_sets.py",
        "uv.lock",
    }
    assert required <= set(TRACKED_INPUTS)
    assert "artifacts/wp4-leakage-audit-v5/summary.json" in ARTIFACT_INPUTS
    expanded = set(expanded_tracked_inputs())
    assert "src/pprs/collector.py" in expanded
    assert "src/pprs/parsing.py" in expanded
    assert "src/pprs/cache.py" in expanded
