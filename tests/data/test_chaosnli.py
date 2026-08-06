import json
from pathlib import Path

import pytest

from pprs.data.chaosnli import (
    git_blob_sha1,
    record_content_sha256,
    sample_rows,
    to_dataset_record,
    verify_source_object,
)
from pprs.data.schema import TaskConfig


@pytest.fixture
def snli_config() -> TaskConfig:
    return TaskConfig.model_validate_json(
        Path("configs/tasks/chaosnli-snli.json").read_text()
    )


def _row(index: int, counts: tuple[int, int, int] = (50, 30, 20)) -> dict:
    return {
        "uid": f"item-{index}",
        "label_counter": {
            "e": counts[0],
            "n": counts[1],
            "c": counts[2],
        },
        "example": {
            "premise": f"premise {index}",
            "hypothesis": f"hypothesis {index}",
        },
    }


def test_sampling_is_deterministic_and_locked(
    snli_config: TaskConfig,
) -> None:
    rows = [_row(index) for index in range(200)]
    first = sample_rows(rows, snli_config)
    second = sample_rows(rows, snli_config)
    first_ids = [row["uid"] for row in first]
    second_ids = [row["uid"] for row in second]
    assert first_ids == second_ids
    assert len(first_ids) == 150
    assert len(set(first_ids)) == 150


def test_dataset_record_preserves_labels_and_inputs(
    snli_config: TaskConfig,
) -> None:
    record = to_dataset_record(_row(1), snli_config)
    assert record.human_label_counts == {"A": 50, "B": 30, "C": 20}
    assert record.inputs == {
        "context": "premise 1",
        "statement": "hypothesis 1",
    }


def test_invalid_label_total_fails(snli_config: TaskConfig) -> None:
    with pytest.raises(ValueError, match="sum to 100"):
        to_dataset_record(_row(1, (50, 30, 19)), snli_config)


def test_missing_zero_count_label_is_supported(
    snli_config: TaskConfig,
) -> None:
    row = _row(1, (70, 30, 0))
    del row["label_counter"]["c"]
    record = to_dataset_record(row, snli_config)
    assert record.human_label_counts == {"A": 70, "B": 30, "C": 0}


def test_record_hash_is_order_sensitive(snli_config: TaskConfig) -> None:
    first = [
        to_dataset_record(_row(1), snli_config),
        to_dataset_record(_row(2), snli_config),
    ]
    second = list(reversed(first))
    assert record_content_sha256(first) != record_content_sha256(second)


def test_source_object_mismatch_fails(
    tmp_path: Path,
    snli_config: TaskConfig,
) -> None:
    source = tmp_path / "source.jsonl"
    source.write_text("{}\n", encoding="utf-8")
    assert git_blob_sha1(source) != snli_config.source_object_id
    with pytest.raises(ValueError, match="source object mismatch"):
        verify_source_object(snli_config, source)


@pytest.mark.parametrize("bad_count", [50.9, True, "50"])
def test_label_counts_require_exact_integers(
    snli_config: TaskConfig,
    bad_count: object,
) -> None:
    row = _row(1)
    row["label_counter"]["e"] = bad_count
    with pytest.raises(ValueError, match="must be integers"):
        to_dataset_record(row, snli_config)


def test_null_prompt_input_is_not_coerced(snli_config: TaskConfig) -> None:
    row = _row(1)
    row["example"]["premise"] = None
    with pytest.raises(ValueError, match="must be strings"):
        to_dataset_record(row, snli_config)
