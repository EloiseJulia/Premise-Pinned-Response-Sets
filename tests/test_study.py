from pathlib import Path

from pprs.data.schema import TaskId
from pprs.study import (
    load_subset_records,
    models_roster_sha256_from_payload,
    task_options,
)
from pprs.records.schema import PinAssignment, PremiseType


def test_smoke_subset_loads_locked_ten_items() -> None:
    subset_id, records = load_subset_records(
        Path("configs/samples/smoke-v1.json")
    )
    assert subset_id == "smoke-v1"
    assert len(records) == 10


def test_task_options_match_locked_order() -> None:
    assert tuple(
        option.token for option in task_options(TaskId.CHAOSNLI_SNLI)
    ) == ("A", "B", "C")
    assert tuple(
        option.token
        for option in task_options(TaskId.SUMMEVAL_RELEVANCE)
    ) == ("A", "B")


def test_models_roster_hash_is_order_independent() -> None:
    first = models_roster_sha256_from_payload(
        {
            "data": [
                {"id": "b", "owned_by": "x", "created": 0},
                {"id": "a", "owned_by": "y", "created": 0},
            ]
        }
    )
    second = models_roster_sha256_from_payload(
        {
            "data": [
                {"id": "a", "owned_by": "y", "created": 0},
                {"id": "b", "owned_by": "x", "created": 0},
            ]
        }
    )
    assert first == second


def test_pin_assignment_is_explicit_for_full_grid() -> None:
    assignment = PinAssignment(
        premise_id="coverage",
        premise_type=PremiseType.VAGUENESS,
        premise_value="strict",
    )
    assert assignment.premise_id == "coverage"
