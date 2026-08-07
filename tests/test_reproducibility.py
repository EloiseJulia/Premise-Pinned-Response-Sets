from pathlib import Path

from pprs.reproducibility import build_reproducibility_manifest


def test_reproducibility_manifest_hashes_inputs_and_outputs(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.write_text("source")
    output.write_text("output")
    manifest = build_reproducibility_manifest(
        prereg_tag="pprs-prereg-v3",
        prereg_git_sha="a" * 40,
        reporting_git_sha="b" * 40,
        trusted_raw_manifest_sha256="c" * 64,
        trusted_raw_manifest_id="d" * 64,
        inputs={"source": source},
        outputs={"output": output},
    )
    assert len(manifest.input_sha256["source"]) == 64
    assert len(manifest.output_sha256["output"]) == 64
    assert len(manifest.manifest_id()) == 64
