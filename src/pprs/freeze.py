from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_freeze(
    *,
    freeze_path: Path,
    expected_tag: str,
) -> str:
    payload = json.loads(freeze_path.read_text(encoding="utf-8"))
    if payload["prereg_tag"] != expected_tag:
        raise ValueError("freeze manifest tag does not match")
    manifest_hash = payload.pop("manifest_sha256")
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != manifest_hash:
        raise ValueError("freeze manifest hash does not match")
    for path, expected in payload["tracked_file_sha256"].items():
        if _sha256(Path(path)) != expected:
            raise ValueError(f"frozen tracked file changed: {path}")
    for path, expected in payload["artifact_sha256"].items():
        if _sha256(Path(path)) != expected:
            raise ValueError(f"frozen artifact changed: {path}")

    tag_commit = subprocess.check_output(
        ["git", "rev-list", "-n", "1", expected_tag],
        text=True,
    ).strip()
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if tag_commit != head:
        raise ValueError("smoke must run exactly at the preregistration tag")
    if subprocess.run(["git", "diff", "--quiet", "HEAD", "--"]).returncode:
        raise ValueError("tracked worktree changes exist after freeze")
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode:
        raise ValueError("staged changes exist after freeze")
    untracked = subprocess.check_output(
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "src",
            "scripts",
            "configs",
            "pyproject.toml",
            "uv.lock",
        ],
        text=True,
    ).strip()
    if untracked:
        raise ValueError(
            f"untracked execution files exist after freeze: {untracked}"
        )
    return head
