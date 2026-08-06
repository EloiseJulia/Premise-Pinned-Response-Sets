from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from enum import StrEnum
from numbers import Integral, Real
from typing import TypeVar

PI_GRID = (0.05, 0.10, 0.15, 0.20, 0.25)


class SummEvalPolarity(StrEnum):
    UPSTREAM_BEHAVIOR = "upstream_behavior"
    SEMANTIC_ALIGNED = "semantic_aligned"


Label = TypeVar("Label", bound=str)
T = TypeVar("T")


def shannon_entropy_bits(labels: Sequence[Label]) -> float:
    if not labels:
        raise ValueError("entropy requires at least one label")
    counts = Counter(labels)
    total = len(labels)
    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )


def danger_quadrant(h_seed: float, h_ctx: float) -> bool:
    _finite_nonnegative(h_seed, "h_seed")
    _finite_nonnegative(h_ctx, "h_ctx")
    return h_seed <= 0.5 and h_ctx > 0.0


def _validated_counts(counts: Mapping[Label, int]) -> tuple[int, tuple[Label, ...]]:
    if not counts:
        raise ValueError("counts cannot be empty")
    if any(type(count) is not int or count < 0 for count in counts.values()):
        raise ValueError("counts must be nonnegative integers")
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("count total must be positive")
    return total, tuple(counts)


def human_response_set(
    counts: Mapping[Label, int],
    pi: float,
) -> tuple[Label, ...]:
    total, labels = _validated_counts(counts)
    _unit_interval(pi, "pi")
    return tuple(label for label in labels if counts[label] / total >= pi)


def human_response_set_surface(
    counts: Mapping[Label, int],
    pi_values: Sequence[float] = PI_GRID,
) -> dict[float, tuple[Label, ...]]:
    values = _validate_grid(pi_values, "pi")
    if tuple(values) != PI_GRID:
        raise ValueError("the proposal-locked pi grid cannot be changed")
    return {pi: human_response_set(counts, pi) for pi in values}


def threshold_surface(
    values: Sequence[T],
    tau_values: Sequence[float],
    evaluate: Callable[[Sequence[T], float], Real],
) -> dict[float, float]:
    if not values:
        raise ValueError("threshold surface requires observations")
    taus = _validate_grid(tau_values, "tau")
    surface = {}
    for tau in taus:
        result = float(evaluate(values, tau))
        if not math.isfinite(result):
            raise ValueError("threshold evaluation must be finite")
        surface[tau] = result
    return surface


def summeval_distribution(
    relevance_0: int,
    relevance_1: int,
    polarity: SummEvalPolarity,
) -> dict[str, float]:
    if (
        type(relevance_0) is not int
        or type(relevance_1) is not int
        or relevance_0 < 0
        or relevance_1 < 0
    ):
        raise ValueError("SummEval counts must be nonnegative integers")
    total = relevance_0 + relevance_1
    if total != 8:
        raise ValueError("SummEval records must contain exactly 8 ratings")
    if polarity is SummEvalPolarity.UPSTREAM_BEHAVIOR:
        relevant, not_relevant = relevance_0, relevance_1
    elif polarity is SummEvalPolarity.SEMANTIC_ALIGNED:
        relevant, not_relevant = relevance_1, relevance_0
    else:
        raise ValueError(f"unknown SummEval polarity: {polarity}")
    return {
        "Relevant": relevant / total,
        "Not Relevant": not_relevant / total,
    }


def validate_probability_distribution(
    probabilities: Mapping[str, float],
) -> None:
    if not probabilities:
        raise ValueError("probability distribution cannot be empty")
    original_values = tuple(probabilities.values())
    if any(
        isinstance(value, bool) or not isinstance(value, Real)
        for value in original_values
    ):
        raise ValueError("probabilities must be numeric and not boolean")
    values = tuple(float(value) for value in original_values)
    if any(
        not math.isfinite(value) or value < 0 or value > 1
        for value in values
    ):
        raise ValueError("probabilities must be finite and within [0,1]")
    if not math.isclose(sum(values), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("probabilities must sum to one")


def _validate_grid(values: Sequence[float], name: str) -> tuple[float, ...]:
    if not values:
        raise ValueError(f"{name} grid cannot be empty")
    if any(
        isinstance(value, bool) or not isinstance(value, Real)
        for value in values
    ):
        raise ValueError(f"{name} values must be numeric and not boolean")
    floats = tuple(float(value) for value in values)
    if len(set(floats)) != len(floats):
        raise ValueError(f"{name} grid values must be unique")
    for value in floats:
        _unit_interval(value, name)
    return floats


def _unit_interval(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be numeric")
    if not math.isfinite(float(value)) or not 0 <= float(value) <= 1:
        raise ValueError(f"{name} must be finite and within [0,1]")


def _finite_nonnegative(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be numeric")
    if not math.isfinite(float(value)) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
