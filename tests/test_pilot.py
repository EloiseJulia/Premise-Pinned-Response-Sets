from pathlib import Path

import pytest

from pprs.data.schema import DatasetRecord, TaskId
from pprs.pilot import (
    PILOT_MODELS,
    build_pilot_cells,
    load_and_validate_sample,
    select_pilot_records,
)
from pprs.prompts import disclosure_template_ids


def _record(task: TaskId, index: int) -> DatasetRecord:
    if task is TaskId.SUMMEVAL_RELEVANCE:
        return DatasetRecord(
            task=task,
            item_id=f"sum-{index}",
            source_dataset="SummEval",
            source_revision="37b8d7863430ec3433d6a73da08408b064643b8b",
            source_object_id="5f3c386bf230cfa0d53fec293cfb56bf7ac76637",
            source_split="all",
            source_original_id=f"sum-{index}",
            sampling_seed=42,
            inputs={"article": "article", "summary": "summary"},
            human_label_counts={"relevance_0": 3, "relevance_1": 5},
            human_label_distribution={
                "relevance_0": 3 / 8,
                "relevance_1": 5 / 8,
            },
            ratings_per_item=8,
            license_identifier="MIT",
            license_source="https://github.com/Yale-LILY/SummEval/blob/81b59ad53d63cb6009764240853c91235a44e238/LICENSE",
            data_card_source="https://github.com/Yale-LILY/SummEval/blob/81b59ad53d63cb6009764240853c91235a44e238/README.md",
            data_card_revision="81b59ad53d63cb6009764240853c91235a44e238",
            data_card_blob="4b54cd7db70990ba8e22a947cf4bd5c9132acd0c",
        )
    split = "snli" if task is TaskId.CHAOSNLI_SNLI else "mnli_matched"
    object_id = (
        "aea16e8f1e868493da3913e3d84c0ba0373bab33"
        if task is TaskId.CHAOSNLI_SNLI
        else "acf6a5a539ee6d1802c3a45e7c2399ab3320e62c"
    )
    return DatasetRecord(
        task=task,
        item_id=f"nli-{index}",
        source_dataset="ChaosNLI",
        source_revision="37b8d7863430ec3433d6a73da08408b064643b8b",
        source_object_id=object_id,
        source_split=split,
        source_original_id=f"nli-{index}",
        sampling_seed=42,
        inputs={"context": "context", "statement": "statement"},
        human_label_counts={"A": 50, "B": 30, "C": 20},
        human_label_distribution={"A": 0.5, "B": 0.3, "C": 0.2},
        ratings_per_item=100,
        license_identifier="CC-BY-NC-4.0",
        license_source="https://github.com/easonnie/ChaosNLI/blob/f358e234ea2797d9298f7b0213bf1308b6d7756b/LICENSE",
        data_card_source="https://github.com/easonnie/ChaosNLI/blob/f358e234ea2797d9298f7b0213bf1308b6d7756b/README.md",
        data_card_revision="f358e234ea2797d9298f7b0213bf1308b6d7756b",
        data_card_blob="967b5a2becf268a18a7d1615ea11bfb5e8423352",
    )


def test_pilot_grid_is_20_by_2_by_5() -> None:
    records_by_task = {
        task: [_record(task, index) for index in range(10)]
        for task in TaskId
    }
    selected = select_pilot_records(records_by_task)
    cells = build_pilot_cells(selected)
    assert len(selected) == 20
    assert len(cells) == 20 * len(PILOT_MODELS) * len(
        disclosure_template_ids()
    )
    assert len({cell.seed for cell in cells}) == len(cells)


def test_sample_manifest_validation_rejects_wrong_order() -> None:
    if not Path("data/processed/chaosnli-snli.parquet").exists():
        pytest.skip("requires locally materialized ignored sample Parquet")
    # The full round-trip is exercised by the committed real sample artifacts.
    # A copied manifest paired with the wrong task Parquet must fail.
    with pytest.raises(ValueError):
        load_and_validate_sample(
            Path("data/processed/chaosnli-snli.parquet"),
            Path("configs/samples/chaosnli-mnli-seed42.json"),
        )
