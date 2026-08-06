from pathlib import Path

from pprs.run_manifest import (
    rendered_prompt_ledger_hash,
    write_prompt_ledger,
    write_raw_inventory,
    validate_raw_run_manifest,
)


def test_rendered_prompt_ledger_is_order_independent(raw_result) -> None:
    other = raw_result.model_copy(
        update={
            "cache_key": "b" * 64,
            "prompt_hash": "d" * 64,
            "sample_id": 1,
        }
    )
    assert rendered_prompt_ledger_hash(
        (raw_result, other)
    ) == rendered_prompt_ledger_hash((other, raw_result))


def test_raw_inventory_and_prompt_ledger_are_emitted(
    tmp_path: Path,
    raw_result,
) -> None:
    inventory = tmp_path / "raw.jsonl"
    ledger = tmp_path / "ledger.json"
    write_raw_inventory((raw_result,), inventory)
    write_prompt_ledger((raw_result,), ledger)
    assert raw_result.raw_text in inventory.read_text()
    assert raw_result.prompt_hash in ledger.read_text()


def test_trusted_manifest_digest_is_checked(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("{}")
    try:
        validate_raw_run_manifest(
            path,
            expected_git_sha="a" * 40,
            trusted_manifest_sha256="0" * 64,
            trusted_manifest_id="1" * 64,
        )
    except ValueError as exc:
        assert "trusted SHA-256" in str(exc)
    else:
        raise AssertionError("untrusted manifest must fail")
