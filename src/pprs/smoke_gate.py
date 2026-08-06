from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class SmokeApproval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    approver: str = Field(min_length=1)
    summary_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_packet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_manifest_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    basis: str = Field(min_length=1)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_smoke_gate(
    *,
    summary_path: Path,
    review_path: Path,
    approval_path: Path,
    expected_git_sha: str,
    run_manifest_path: Path,
) -> None:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary["parse_success"] < 0.95:
        raise ValueError("smoke parse success gate failed")
    if summary["cache_rerun_provider_invocations"] != 0:
        raise ValueError("smoke cache rerun gate failed")
    if summary["first_run"]["git_sha"] != expected_git_sha:
        raise ValueError("smoke summary Git SHA differs from freeze")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if len(review["records"]) != 20:
        raise ValueError("smoke review packet must contain 20 records")
    if any(
        not all(record["review_checks"].values())
        for record in review["records"]
    ):
        raise ValueError("smoke review packet contains failed checks")
    approval = SmokeApproval.model_validate_json(
        approval_path.read_text(encoding="utf-8")
    )
    if approval.status != "approved":
        raise ValueError("smoke review is not approved")
    if approval.summary_sha256 != sha256_file(summary_path):
        raise ValueError("smoke approval references a different summary")
    if approval.review_packet_sha256 != sha256_file(review_path):
        raise ValueError("smoke approval references a different review packet")
    if review.get("run_tag") != summary["first_run"]["run_tag"]:
        raise ValueError("smoke review and summary run tags differ")
    if review.get("git_sha") != summary["first_run"]["git_sha"]:
        raise ValueError("smoke review and summary Git SHAs differ")
    if review.get("subset_id") != summary["first_run"]["subset_id"]:
        raise ValueError("smoke review and summary subsets differ")
    from pprs.run_manifest import validate_raw_run_manifest

    manifest = validate_raw_run_manifest(
        run_manifest_path,
        expected_git_sha=expected_git_sha,
    )
    if approval.raw_manifest_sha256 != sha256_file(run_manifest_path):
        raise ValueError("smoke approval references a different run manifest")
    if approval.raw_manifest_id != manifest.manifest_id():
        raise ValueError("smoke approval references a different manifest ID")
