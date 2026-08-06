import pytest

from pprs.analysis.inference import (
    DangerCell,
    H3Observation,
    PlaceboPairContrast,
    aggregate_full_grid_choices,
    bias_regret,
    consistency_regret,
    h3_item_advantage,
    h1_inference,
    h2_inference,
    h3_inference,
    jaccard_similarity,
    modal_label,
    placebo_flip_contrast,
    placebo_inference,
    select_model,
)


def test_modal_label_uses_option_order_for_ties() -> None:
    assert modal_label(["B", "A"], ("A", "B")) == "A"


def test_h3_advantage_positive_favors_pprs() -> None:
    advantage = h3_item_advantage(
        {"A": 0.4, "B": 0.6},
        ("A",),
        ("A",),
        ("A", "B"),
    )
    assert advantage > 0


def test_placebo_contrast_is_matched_real_minus_placebo() -> None:
    assert placebo_flip_contrast(
        ["A", "A", "A"],
        ["B", "A"],
        ["A", "A"],
        ("A", "B"),
    ) == 0.5


def test_placebo_inference_bootstraps_items() -> None:
    result = placebo_inference(
        [
            PlaceboPairContrast("snli", "i1", "a", 0.5),
            PlaceboPairContrast("snli", "i1", "b", 0.0),
            PlaceboPairContrast("mnli", "i3", "a", None),
        ],
        bootstrap_replicates=100,
    )
    assert result.mean_contrast == 0.25
    assert result.valid_pairs == 2
    assert result.excluded_pairs == 1


def test_full_grid_uses_equal_round_weights() -> None:
    result = aggregate_full_grid_choices(
        [["A", "B"], ["B", "B"]],
        ("A", "B"),
    )
    assert result is not None
    assert result.distribution == {"A": 0.25, "B": 0.75}


def test_jaccard_and_regrets() -> None:
    assert jaccard_similarity(("A",), ("A", "B")) == 0.5
    consistency = {"a": 0.8, "b": 0.9}
    bias = {"a": 0.1, "b": 0.3}
    assert consistency_regret(consistency, "a") == pytest.approx(0.1)
    assert bias_regret(bias, "b") == pytest.approx(0.2)


def test_model_selection_ties_use_lexical_id() -> None:
    assert select_model(
        {"z": 1.0, "a": 1.0},
        lower_is_better=True,
    ) == "a"


def test_h1_inference_freezes_prediction_rules() -> None:
    result = h1_inference(
        [(0.0, 0.0), (0.5, 0.1), (1.0, 0.2), (0.2, 0.8)],
        bootstrap_replicates=100,
    )
    assert result.n_cells == 4
    assert isinstance(result.prediction_met, bool)


def test_h2_inference_clusters_items_with_judges() -> None:
    cells = [
        DangerCell("snli", "i1", "a", True),
        DangerCell("snli", "i1", "b", True),
        DangerCell("snli", "i2", "a", False),
        DangerCell("snli", "i2", "b", None),
    ]
    result = h2_inference(cells, bootstrap_replicates=100)
    assert result.proportion == pytest.approx(2 / 3)
    assert result.valid_cells == 3
    assert result.excluded_cells == 1


def test_h3_inference_applies_monotonic_rule() -> None:
    observations = []
    for task, value in (
        ("chaosnli_snli", 0.1),
        ("chaosnli_mnli", 0.2),
    ):
        for pi in (0.05, 0.1):
            observations.append(
                H3Observation(
                    task=task,
                    item_id="i",
                    judge_id="j",
                    pi=pi,
                    polarity="not_applicable",
                    advantage=value,
                )
            )
    for polarity in ("upstream_behavior", "semantic_aligned"):
        for pi in (0.05, 0.1):
            observations.append(
                H3Observation(
                    task="summeval_relevance",
                    item_id="i",
                    judge_id="j",
                    pi=pi,
                    polarity=polarity,
                    advantage=0.3,
                )
            )
    result = h3_inference(observations, bootstrap_replicates=100)
    assert result.prediction_met
    assert 0.05 in result.surface_ci["chaosnli_snli"]["not_applicable"]
