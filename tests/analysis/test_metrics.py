import math

import pytest

from pprs.analysis.metrics import (
    PI_GRID,
    SummEvalPolarity,
    danger_quadrant,
    human_response_set,
    human_response_set_surface,
    shannon_entropy_bits,
    summeval_distribution,
    threshold_surface,
    validate_probability_distribution,
)


def test_shannon_entropy_in_bits() -> None:
    assert shannon_entropy_bits(["A", "A"]) == 0.0
    assert shannon_entropy_bits(["A", "B"]) == 1.0
    assert math.isclose(
        shannon_entropy_bits(["A", "A", "B"]),
        0.9182958340544896,
    )


def test_empty_entropy_fails() -> None:
    with pytest.raises(ValueError, match="at least one"):
        shannon_entropy_bits([])


@pytest.mark.parametrize(
    ("h_seed", "h_ctx", "expected"),
    [
        (0.0, 1.0, True),
        (0.5, 0.1, True),
        (0.5000001, 1.0, False),
        (0.0, 0.0, False),
        (1.0, 1.0, False),
    ],
)
def test_danger_quadrant_direction(
    h_seed: float,
    h_ctx: float,
    expected: bool,
) -> None:
    assert danger_quadrant(h_seed, h_ctx) is expected


def test_human_response_set_uses_inclusive_pi() -> None:
    counts = {"A": 5, "B": 20, "C": 75}
    assert human_response_set(counts, 0.05) == ("A", "B", "C")
    assert human_response_set(counts, 0.10) == ("B", "C")
    assert human_response_set(counts, 0.25) == ("C",)


def test_pi_surface_is_locked() -> None:
    surface = human_response_set_surface(
        {"A": 5, "B": 20, "C": 75}
    )
    assert tuple(surface) == PI_GRID
    with pytest.raises(ValueError, match="cannot be changed"):
        human_response_set_surface(
            {"A": 5, "B": 20, "C": 75},
            (0.10, 0.20),
        )


def test_tau_surface_requires_explicit_valid_grid() -> None:
    result = threshold_surface(
        [0.1, 0.6, 0.9],
        (0.0, 0.5, 1.0),
        lambda values, tau: sum(value >= tau for value in values) / len(values),
    )
    assert result == {0.0: 1.0, 0.5: 2 / 3, 1.0: 0.0}
    with pytest.raises(ValueError, match="unique"):
        threshold_surface([1], (0.5, 0.5), lambda values, tau: 0)


def test_summeval_polarity_specification_curve() -> None:
    upstream = summeval_distribution(
        3,
        5,
        SummEvalPolarity.UPSTREAM_BEHAVIOR,
    )
    semantic = summeval_distribution(
        3,
        5,
        SummEvalPolarity.SEMANTIC_ALIGNED,
    )
    assert upstream == {"Relevant": 3 / 8, "Not Relevant": 5 / 8}
    assert semantic == {"Relevant": 5 / 8, "Not Relevant": 3 / 8}
    assert upstream != semantic


@pytest.mark.parametrize(
    "probabilities",
    [
        {},
        {"A": math.nan, "B": math.nan},
        {"A": -0.1, "B": 1.1},
        {"A": 0.4, "B": 0.5},
        {"A": True},
    ],
)
def test_probability_validation_rejects_invalid_inputs(
    probabilities,
) -> None:
    with pytest.raises(ValueError):
        validate_probability_distribution(probabilities)


def test_probability_validation_accepts_normalized_input() -> None:
    validate_probability_distribution({"A": 0.4, "B": 0.6})


def test_tau_grid_rejects_booleans() -> None:
    with pytest.raises(ValueError, match="not boolean"):
        threshold_surface([1], (False, True), lambda values, tau: 0)
