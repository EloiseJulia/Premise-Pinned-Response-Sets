import math

from pprs.analysis.response_sets import (
    aggregate_pinned_choices,
    beta_pin,
    beta_self,
    h_seed,
)


def test_h_seed_requires_two_valid_samples() -> None:
    assert h_seed(["A", None], ("A", "B")) is None
    assert h_seed(["A", "B"], ("A", "B")) == 1.0


def test_pinned_aggregation_weights_premises_and_rounds_equally() -> None:
    result = aggregate_pinned_choices(
        [
            [
                ["A", "B"],
                ["A", "A", "A"],
            ],
            [
                ["B", "B"],
            ],
        ],
        ("A", "B"),
    )
    assert result is not None
    # Round 1: mean((.5,.5),(1,0)) = (.75,.25)
    # Round 2: (0,1); equal round mean = (.375,.625)
    assert result.distribution == {"A": 0.375, "B": 0.625}
    assert math.isclose(result.h_ctx_bits, 0.954434002924965)
    assert result.pprs == ("A", "B")
    assert result.valid_rounds == 2
    assert result.valid_premises == 3
    assert result.valid_pinned_values == 7


def test_premise_with_fewer_than_two_valid_values_is_excluded() -> None:
    result = aggregate_pinned_choices(
        [[[None, "A"], ["B", "B"]]],
        ("A", "B"),
    )
    assert result is not None
    assert result.distribution == {"A": 0.0, "B": 1.0}
    assert result.pprs == ("A", "B")
    assert result.valid_premises == 1


def test_single_valid_pin_yields_pprs_but_null_h_ctx() -> None:
    result = aggregate_pinned_choices(
        [[[None, "A"]]],
        ("A", "B"),
    )
    assert result is not None
    assert result.pprs == ("A",)
    assert result.distribution is None
    assert result.h_ctx_bits is None


def test_beta_self_uses_paired_negative_forced_samples() -> None:
    assert beta_self(
        ["B", "B", "A", None],
        [("A", "B"), ("B",), ("A",), ("A",)],
        positive_option="A",
        negative_option="B",
    ) == 0.5


def test_beta_denominator_zero_returns_null() -> None:
    assert beta_self(
        ["A"],
        [("A",)],
        positive_option="A",
        negative_option="B",
    ) is None
    assert beta_pin(
        [["A"]],
        [("A",)],
        positive_option="A",
        negative_option="B",
    ) is None


def test_beta_pin_reuses_item_pprs_for_negative_samples() -> None:
    assert beta_pin(
        [["B", "B", "A"]],
        [("A", "B")],
        positive_option="A",
        negative_option="B",
    ) == 1.0
    assert beta_pin(
        [["B", "B", "A"]],
        [("B",)],
        positive_option="A",
        negative_option="B",
    ) == 0.0


def test_beta_pin_pools_negative_samples_across_items() -> None:
    assert beta_pin(
        [["B"], ["B", "B", "B"]],
        [("A", "B"), ("B",)],
        positive_option="A",
        negative_option="B",
    ) == 0.25
