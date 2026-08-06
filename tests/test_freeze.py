import json
from pathlib import Path

import pytest

from pprs.freeze import validate_freeze


def test_missing_freeze_manifest_fails(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        validate_freeze(
            freeze_path=tmp_path / "missing.json",
            expected_tag="pprs-prereg-v1",
        )


def test_tampered_freeze_hash_fails(tmp_path: Path) -> None:
    path = tmp_path / "freeze.json"
    path.write_text(
        json.dumps(
            {
                "prereg_tag": "pprs-prereg-v1",
                "tracked_file_sha256": {},
                "artifact_sha256": {},
                "manifest_sha256": "0" * 64,
            }
        )
    )
    with pytest.raises(ValueError, match="manifest hash"):
        validate_freeze(
            freeze_path=path,
            expected_tag="pprs-prereg-v1",
        )
