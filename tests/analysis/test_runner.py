import json
from pathlib import Path

import pytest

from pprs.analysis.runner import (
    _aggregate_metric_rows,
    _build_regret_surfaces,
    run_confirmatory_analysis,
)


def test_confirmatory_runner_rejects_incomplete_records() -> None:
    config = json.loads(
        Path("configs/runs/confirmatory-v1.json").read_text()
    )
    with pytest.raises(ValueError):
        run_confirmatory_analysis(
            [],
            [],
            config,
        )


def test_metric_and_regret_surfaces_are_executable() -> None:
    metric_rows = []
    downstream_rows = []
    for model, hit, bias in (("a", 1.0, False), ("b", 0.0, True)):
        metric_rows.append(
            {
                "task": "snli",
                "item_id": "i",
                "model_snapshot": model,
                "pi": 0.05,
                "polarity": "not_applicable",
                "Hit Rate": hit,
                "KL(h,j)": 1 - hit,
                "KL(j,h)": 1 - hit,
                "Coverage": hit,
                "MSE_self": 1 - hit,
                "MSE_pin": 1 - hit,
            }
        )
        downstream_rows.append(
            {
                "task": "snli",
                "item_id": "i",
                "model_snapshot": model,
                "pi": 0.05,
                "polarity": "not_applicable",
                "tau": 0.5,
                "judge_positive": bias,
                "human_positive": False,
            }
        )
    assert len(_aggregate_metric_rows(metric_rows)) == 2
    regrets = _build_regret_surfaces(
        metric_rows,
        downstream_rows,
        (0.5,),
    )
    assert {row["metric"] for row in regrets} == {
        "Hit Rate",
        "KL(h,j)",
        "KL(j,h)",
        "Coverage",
        "MSE_self",
        "MSE_pin",
    }


def test_zero_coverage_regret_cells_are_explicit() -> None:
    metrics = [
        {
            "task": "snli",
            "model_snapshot": "a",
            "pi": 0.05,
            "polarity": "not_applicable",
            "Hit Rate": None,
            "KL(h,j)": None,
            "KL(j,h)": None,
            "Coverage": None,
            "MSE_self": None,
            "MSE_pin": None,
        }
    ]
    regrets = _build_regret_surfaces(metrics, [], (0.0, 0.5, 1.0))
    assert len(regrets) == 18
    assert all(row["selected_model"] is None for row in regrets)
