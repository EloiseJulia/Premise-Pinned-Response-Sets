from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field


class PinnedAggregation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    distribution: dict[str, float] | None
    h_ctx_bits: float | None
    pprs: tuple[str, ...]
    valid_rounds: int = Field(ge=0)
    valid_premises: int = Field(ge=0)
    valid_pinned_values: int = Field(ge=0)


def label_distribution(
    labels: Sequence[str],
    option_order: tuple[str, ...],
) -> dict[str, float]:
    if not labels:
        raise ValueError("label distribution requires labels")
    _validate_option_order(option_order)
    if any(label not in option_order for label in labels):
        raise ValueError("label is outside the task option space")
    counts = Counter(labels)
    total = len(labels)
    return {
        option: counts.get(option, 0) / total for option in option_order
    }


def entropy_bits_from_distribution(
    distribution: dict[str, float],
) -> float:
    if not distribution:
        raise ValueError("distribution cannot be empty")
    values = tuple(distribution.values())
    if any(
        not math.isfinite(value) or value < 0 or value > 1
        for value in values
    ):
        raise ValueError("probabilities must be finite and within [0,1]")
    if not math.isclose(sum(values), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("probabilities must sum to one")
    return -sum(value * math.log2(value) for value in values if value > 0)


def h_seed(
    forced_choices: Sequence[str | None],
    option_order: tuple[str, ...],
) -> float | None:
    valid = tuple(choice for choice in forced_choices if choice is not None)
    if len(valid) < 2:
        return None
    return entropy_bits_from_distribution(
        label_distribution(valid, option_order)
    )


def aggregate_pinned_choices(
    rounds: Sequence[Sequence[Sequence[str | None]]],
    option_order: tuple[str, ...],
) -> PinnedAggregation | None:
    _validate_option_order(option_order)
    round_distributions = []
    pprs_values: set[str] = set()
    valid_premises = 0
    valid_values = 0

    for round_premises in rounds:
        premise_distributions = []
        for premise_values in round_premises:
            valid = tuple(
                label for label in premise_values if label is not None
            )
            if valid:
                if any(label not in option_order for label in valid):
                    raise ValueError("label is outside the task option space")
                pprs_values.update(valid)
                valid_values += len(valid)
            if len(valid) < 2:
                continue
            distribution = label_distribution(valid, option_order)
            premise_distributions.append(distribution)
            valid_premises += 1
        if premise_distributions:
            round_distributions.append(
                _mean_distributions(
                    premise_distributions,
                    option_order,
                )
            )

    if not pprs_values:
        return None
    distribution = (
        _mean_distributions(round_distributions, option_order)
        if round_distributions
        else None
    )
    return PinnedAggregation(
        distribution=distribution,
        h_ctx_bits=(
            entropy_bits_from_distribution(distribution)
            if distribution is not None
            else None
        ),
        pprs=tuple(
            option for option in option_order if option in pprs_values
        ),
        valid_rounds=len(round_distributions),
        valid_premises=valid_premises,
        valid_pinned_values=valid_values,
    )


def beta_self(
    forced_choices: Sequence[str | None],
    response_sets: Sequence[Sequence[str] | None],
    *,
    positive_option: str,
    negative_option: str,
) -> float | None:
    if len(forced_choices) != len(response_sets):
        raise ValueError("forced choices and response sets must align")
    numerator = 0
    denominator = 0
    for forced, response_set in zip(
        forced_choices,
        response_sets,
        strict=True,
    ):
        if forced is None or response_set is None:
            continue
        if forced == negative_option:
            denominator += 1
            numerator += positive_option in response_set
    return numerator / denominator if denominator else None


def beta_pin(
    forced_choices_by_item: Sequence[Sequence[str | None]],
    pprs_by_item: Sequence[Sequence[str] | None],
    *,
    positive_option: str,
    negative_option: str,
) -> float | None:
    if len(forced_choices_by_item) != len(pprs_by_item):
        raise ValueError("forced-choice items and PPRS items must align")
    numerator = 0
    denominator = 0
    for forced_choices, pprs in zip(
        forced_choices_by_item,
        pprs_by_item,
        strict=True,
    ):
        if pprs is None:
            continue
        item_negative = sum(
            choice == negative_option
            for choice in forced_choices
            if choice is not None
        )
        denominator += item_negative
        if positive_option in pprs:
            numerator += item_negative
    return numerator / denominator if denominator else None


def _mean_distributions(
    distributions: Sequence[dict[str, float]],
    option_order: tuple[str, ...],
) -> dict[str, float]:
    if not distributions:
        raise ValueError("cannot average empty distributions")
    return {
        option: sum(
            distribution[option] for distribution in distributions
        )
        / len(distributions)
        for option in option_order
    }


def _validate_option_order(option_order: tuple[str, ...]) -> None:
    if not option_order or len(set(option_order)) != len(option_order):
        raise ValueError("option order must be nonempty and unique")
