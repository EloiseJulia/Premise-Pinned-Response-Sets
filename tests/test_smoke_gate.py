import json
from pathlib import Path

import pytest

from pprs.smoke_gate import sha256_file, validate_smoke_gate


def test_smoke_gate_requires_approved_packet(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.json"
    approval = tmp_path / "approval.json"
    run_manifest = tmp_path / "run-manifest.json"
    summary.write_text(
        json.dumps(
            {
                "first_run": {
                    "run_tag": "smoke",
                    "git_sha": "a" * 40,
                    "subset_id": "smoke-v1",
                },
                "parse_success": 0.95,
                "cache_rerun_provider_invocations": 0,
            }
        )
    )
    review.write_text(
        json.dumps(
            {
                "run_tag": "smoke",
                "git_sha": "a" * 40,
                "subset_id": "smoke-v1",
                "records": [
                    {"review_checks": {"ok": True}}
                    for _ in range(20)
                ]
            }
        )
    )
    approval.write_text(
        json.dumps(
            {
                "status": "approved",
                "approver": "owner",
                "summary_sha256": sha256_file(summary),
                "review_packet_sha256": sha256_file(review),
                "raw_manifest_sha256": "b" * 64,
                "raw_manifest_id": "c" * 64,
                "basis": "reviewed",
            }
        )
    )
    # Raw-manifest validation is covered separately; use a monkeypatch-sized
    # valid fixture through the public function's imported validator.
    import pprs.run_manifest

    original = pprs.run_manifest.validate_raw_run_manifest
    class FakeManifest:
        def manifest_id(self):
            return "c" * 64

    pprs.run_manifest.validate_raw_run_manifest = (
        lambda *args, **kwargs: FakeManifest()
    )
    run_manifest.write_text("manifest")
    # Match the approval to the concrete manifest file.
    approved_payload = json.loads(approval.read_text())
    approved_payload["raw_manifest_sha256"] = sha256_file(run_manifest)
    approval.write_text(json.dumps(approved_payload))
    try:
        validate_smoke_gate(
            summary_path=summary,
            review_path=review,
            approval_path=approval,
            expected_git_sha="a" * 40,
            run_manifest_path=run_manifest,
        )
    finally:
        pprs.run_manifest.validate_raw_run_manifest = original
    approval.write_text(
        json.dumps(
            {
                "status": "pending",
                "approver": "owner",
                "summary_sha256": sha256_file(summary),
                "review_packet_sha256": sha256_file(review),
                "raw_manifest_sha256": sha256_file(run_manifest),
                "raw_manifest_id": "c" * 64,
                "basis": "not reviewed",
            }
        )
    )
    with pytest.raises(ValueError, match="not approved"):
        original = pprs.run_manifest.validate_raw_run_manifest
        pprs.run_manifest.validate_raw_run_manifest = (
            lambda *args, **kwargs: FakeManifest()
        )
        try:
            validate_smoke_gate(
                summary_path=summary,
                review_path=review,
                approval_path=approval,
                expected_git_sha="a" * 40,
                run_manifest_path=run_manifest,
            )
        finally:
            pprs.run_manifest.validate_raw_run_manifest = original
