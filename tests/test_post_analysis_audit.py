from pathlib import Path

from pprs.post_analysis_audit import write_post_analysis_manifest


def test_post_analysis_manifest_binds_supplement(tmp_path: Path) -> None:
    supplement = {
        "authoritative_artifact_hashes": {
            "analysis_json": "a" * 64,
            "raw_run_manifest": "b" * 64,
            "specification_curve_manifest": "c" * 64,
            "analysis_upstream": "d" * 64,
            "analysis_semantic": "e" * 64,
        }
    }
    supplement_path = tmp_path / "supplement.json"
    manifest_path = tmp_path / "manifest.json"
    write_post_analysis_manifest(
        supplement,
        supplement_path,
        manifest_path,
    )
    assert supplement_path.exists()
    assert '"manifest_id"' in manifest_path.read_text()
