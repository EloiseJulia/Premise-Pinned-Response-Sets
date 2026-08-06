from pathlib import Path

import pytest

from pprs.data.schema import TaskConfig
from pprs.data.summeval import sample_rows, to_dataset_record


@pytest.fixture
def config() -> TaskConfig:
    return TaskConfig.model_validate_json(
        Path("configs/tasks/summeval-relevance.json").read_text()
    )


def _row(index: int) -> dict[str, str]:
    return {
        "id": f"article-{index}",
        "article": f"article text {index}",
        "summary": f"summary text {index}",
        "relevance_0": "3.0",
        "relevance_1": "5.0",
    }


def test_summeval_sampling_is_deterministic(config: TaskConfig) -> None:
    rows = [_row(index) for index in range(200)]
    first = sample_rows(rows, config)
    second = sample_rows(rows, config)
    assert first == second
    assert len(first) == 150


def test_summeval_record_retains_polarity_neutral_counts(
    config: TaskConfig,
) -> None:
    record = to_dataset_record(_row(1), config, row_index=1)
    assert record.item_id == "article-1::row-1"
    assert record.human_label_counts == {
        "relevance_0": 3,
        "relevance_1": 5,
    }


@pytest.mark.parametrize("bad_value", ["3.5", "-1", "not-a-number"])
def test_summeval_counts_require_nonnegative_integers(
    config: TaskConfig,
    bad_value: str,
) -> None:
    row = _row(1)
    row["relevance_0"] = bad_value
    with pytest.raises(ValueError):
        to_dataset_record(row, config, row_index=1)
