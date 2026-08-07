from pathlib import Path

from scripts.full_progress import snapshot


def test_empty_progress_snapshot(tmp_path: Path) -> None:
    assert snapshot(tmp_path) == {
        "records": 0,
        "bytes": 0,
        "sampled": 0,
        "status_counts": {},
        "model_status_counts": {},
    }
