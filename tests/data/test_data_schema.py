import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pprs.data.schema import DatasetRecord, TaskConfig


@pytest.mark.parametrize(
    "config_path",
    [
        Path("configs/tasks/chaosnli-snli.json"),
        Path("configs/tasks/chaosnli-mnli.json"),
    ],
)
def test_locked_nli_configs_validate(config_path: Path) -> None:
    config = TaskConfig.model_validate(json.loads(config_path.read_text()))
    assert config.sample_size == 150
    assert config.sampling_seed == 42
    assert config.ratings_per_item == 100


def test_summeval_config_has_both_polarities_and_seed_42() -> None:
    config = TaskConfig.model_validate(
        json.loads(
            Path("configs/tasks/summeval-relevance.json").read_text()
        )
    )
    assert set(config.analysis_conventions) == {
        "upstream_behavior",
        "semantic_aligned",
    }
    assert config.sampling_seed == 42


def test_label_counts_must_total_100(dataset_record: DatasetRecord) -> None:
    payload = dataset_record.model_dump()
    payload["human_label_counts"] = {"A": 75, "B": 20, "C": 4}

    with pytest.raises(ValidationError, match="sum to 100"):
        DatasetRecord.model_validate(payload)


def test_option_order_drift_fails() -> None:
    payload = json.loads(
        Path("configs/tasks/chaosnli-snli.json").read_text()
    )
    payload["options"][0], payload["options"][1] = (
        payload["options"][1],
        payload["options"][0],
    )

    with pytest.raises(ValidationError, match="option order"):
        TaskConfig.model_validate(payload)


def test_chaosnli_provenance_is_locked() -> None:
    payload = json.loads(
        Path("configs/tasks/chaosnli-snli.json").read_text()
    )
    payload["source_dataset"] = "SNLI"
    payload["source_revision"] = "fake"
    payload["source_split"] = "train"

    with pytest.raises(ValidationError, match="must be ChaosNLI"):
        TaskConfig.model_validate(payload)


def test_nli_prompt_fields_are_locked() -> None:
    payload = json.loads(
        Path("configs/tasks/chaosnli-snli.json").read_text()
    )
    payload["input_fields"] = ["wrong"]

    with pytest.raises(ValidationError, match="input fields"):
        TaskConfig.model_validate(payload)


def test_negative_label_counts_fail(dataset_record: DatasetRecord) -> None:
    payload = dataset_record.model_dump()
    payload["human_label_counts"] = {"A": 101, "B": -1, "C": 0}
    payload["human_label_distribution"] = {
        "A": 1.01,
        "B": -0.01,
        "C": 0.0,
    }

    with pytest.raises(ValidationError, match="cannot be negative"):
        DatasetRecord.model_validate(payload)


def test_prompt_inputs_cannot_be_dropped(
    dataset_record: DatasetRecord,
) -> None:
    payload = dataset_record.model_dump()
    payload["inputs"] = {}

    with pytest.raises(ValidationError, match="context and statement"):
        DatasetRecord.model_validate(payload)
