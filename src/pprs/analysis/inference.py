from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import random

import numpy as np

from pprs.analysis.response_sets import (
    PinnedAggregation,
    aggregate_pinned_choices,
)


def modal_label(
    labels: Sequence[str | None],
    option_order: tuple[str, ...],
) -> str | None:
    valid = [label for label in labels if label is not None]
    if not valid:
        return None
    counts = {option: valid.count(option) for option in option_order}
    maximum = max(counts.values())
    return next(
        option for option in option_order if counts[option] == maximum
    )


def squared_set_loss(
    predicted: Mapping[str, float],
    human_set: Sequence[str],
    option_order: tuple[str, ...],
) -> float:
    if set(predicted) != set(option_order):
        raise ValueError("predicted vector must cover the task option order")
    if any(value < 0 or value > 1 for value in predicted.values()):
        raise ValueError("predicted values must be within [0,1]")
    human = set(human_set)
    if not human <= set(option_order):
        raise ValueError("human set contains an unknown option")
    return sum(
        (predicted[option] - (1.0 if option in human else 0.0)) ** 2
        for option in option_order
    )


def h3_item_advantage(
    self_inclusion_frequency: Mapping[str, float],
    pprs: Sequence[str],
    human_set: Sequence[str],
    option_order: tuple[str, ...],
) -> float:
    self_loss = squared_set_loss(
        self_inclusion_frequency,
        human_set,
        option_order,
    )
    pin_vector = {
        option: 1.0 if option in pprs else 0.0 for option in option_order
    }
    pin_loss = squared_set_loss(pin_vector, human_set, option_order)
    return self_loss - pin_loss


def placebo_flip_contrast(
    baseline_labels: Sequence[str | None],
    real_pin_choices: Sequence[str | None],
    placebo_choices: Sequence[str | None],
    option_order: tuple[str, ...],
) -> float | None:
    if len(real_pin_choices) != len(placebo_choices):
        raise ValueError("real and placebo choices must align")
    baseline = modal_label(baseline_labels, option_order)
    if baseline is None:
        return None
    differences = []
    for real, placebo in zip(
        real_pin_choices,
        placebo_choices,
        strict=True,
    ):
        if real is None or placebo is None:
            continue
        differences.append(
            float(real != baseline) - float(placebo != baseline)
        )
    return sum(differences) / len(differences) if differences else None


def aggregate_full_grid_choices(
    rounds: Sequence[Sequence[str | None]],
    option_order: tuple[str, ...],
) -> PinnedAggregation | None:
    # Reuse the hierarchical aggregator with one equal-weight "premise" per
    # round whose values are the Cartesian-product combination outputs.
    return aggregate_pinned_choices(
        [[round_choices] for round_choices in rounds],
        option_order,
    )


def jaccard_similarity(
    first: Sequence[str],
    second: Sequence[str],
) -> float:
    first_set = set(first)
    second_set = set(second)
    union = first_set | second_set
    if not union:
        return 1.0
    return len(first_set & second_set) / len(union)


def consistency_regret(
    consistency_by_model: Mapping[str, float],
    selected_model: str,
) -> float:
    return max(consistency_by_model.values()) - consistency_by_model[
        selected_model
    ]


def bias_regret(
    bias_mae_by_model: Mapping[str, float],
    selected_model: str,
) -> float:
    return bias_mae_by_model[selected_model] - min(
        bias_mae_by_model.values()
    )


def select_model(
    metric_by_model: Mapping[str, float],
    *,
    lower_is_better: bool,
) -> str:
    if not metric_by_model:
        raise ValueError("model metric mapping cannot be empty")
    optimum = (
        min(metric_by_model.values())
        if lower_is_better
        else max(metric_by_model.values())
    )
    return min(
        model
        for model, value in metric_by_model.items()
        if value == optimum
    )


@dataclass(frozen=True)
class H1Inference:
    r: float
    ci_low: float
    ci_high: float
    n_cells: int
    prediction_met: bool
    bootstrap_robust: bool


def h1_inference(
    beta_pairs: Sequence[tuple[float | None, float | None]],
    *,
    bootstrap_replicates: int = 10_000,
    seed: int = 42,
) -> H1Inference:
    valid = [(a, b) for a, b in beta_pairs if a is not None and b is not None]
    if len(valid) < 3:
        raise ValueError("H1 requires at least three valid task-judge cells")
    r = _pearson(valid)
    rng = random.Random(seed)
    boot = []
    for _ in range(bootstrap_replicates):
        sample = [valid[rng.randrange(len(valid))] for _ in valid]
        try:
            boot.append(_pearson(sample))
        except ValueError:
            continue
    if not boot:
        raise ValueError("H1 bootstrap produced no valid correlations")
    low, high = np.quantile(boot, [0.025, 0.975])
    return H1Inference(
        r=r,
        ci_low=float(low),
        ci_high=float(high),
        n_cells=len(valid),
        prediction_met=r < 0.4,
        bootstrap_robust=float(high) < 0.4,
    )


@dataclass(frozen=True)
class DangerCell:
    task: str
    item_id: str
    judge_id: str
    dangerous: bool | None


@dataclass(frozen=True)
class H2Inference:
    proportion: float
    ci_low: float
    ci_high: float
    valid_cells: int
    excluded_cells: int
    prediction_met: bool
    bootstrap_robust: bool


def h2_inference(
    cells: Sequence[DangerCell],
    *,
    bootstrap_replicates: int = 10_000,
    seed: int = 42,
) -> H2Inference:
    valid = [cell for cell in cells if cell.dangerous is not None]
    if not valid:
        raise ValueError("H2 requires valid danger cells")
    point = sum(bool(cell.dangerous) for cell in valid) / len(valid)
    by_task_item: dict[str, dict[str, list[DangerCell]]] = {}
    for cell in valid:
        by_task_item.setdefault(cell.task, {}).setdefault(
            cell.item_id, []
        ).append(cell)
    rng = random.Random(seed)
    boot = []
    for _ in range(bootstrap_replicates):
        sampled_cells = []
        for items in by_task_item.values():
            item_ids = tuple(items)
            for _index in item_ids:
                chosen = item_ids[rng.randrange(len(item_ids))]
                sampled_cells.extend(items[chosen])
        boot.append(
            sum(bool(cell.dangerous) for cell in sampled_cells)
            / len(sampled_cells)
        )
    low, high = np.quantile(boot, [0.025, 0.975])
    return H2Inference(
        proportion=point,
        ci_low=float(low),
        ci_high=float(high),
        valid_cells=len(valid),
        excluded_cells=len(cells) - len(valid),
        prediction_met=point > 0.15,
        bootstrap_robust=float(low) > 0.15,
    )


@dataclass(frozen=True)
class H3Observation:
    task: str
    item_id: str
    judge_id: str
    pi: float
    polarity: str
    advantage: float


@dataclass(frozen=True)
class H3Inference:
    task_median_advantage: dict[str, dict[str, float]]
    surface: dict[str, dict[str, dict[float, float]]]
    surface_ci: dict[str, dict[str, dict[float, tuple[float, float]]]]
    prediction_met: bool


@dataclass(frozen=True)
class PlaceboPairContrast:
    task: str
    item_id: str
    judge_id: str
    contrast: float | None


@dataclass(frozen=True)
class PlaceboInference:
    mean_contrast: float
    ci_low: float
    ci_high: float
    valid_pairs: int
    excluded_pairs: int


def placebo_inference(
    pairs: Sequence[PlaceboPairContrast],
    *,
    bootstrap_replicates: int = 10_000,
    seed: int = 42,
) -> PlaceboInference:
    valid = [pair for pair in pairs if pair.contrast is not None]
    if not valid:
        raise ValueError("placebo inference requires valid item contrasts")
    point = sum(float(pair.contrast) for pair in valid) / len(valid)
    by_task_item: dict[str, dict[str, list[PlaceboPairContrast]]] = {}
    for pair in valid:
        by_task_item.setdefault(pair.task, {}).setdefault(
            pair.item_id, []
        ).append(pair)
    rng = random.Random(seed)
    boot = []
    for _ in range(bootstrap_replicates):
        sampled = []
        for items in by_task_item.values():
            item_ids = tuple(items)
            for _index in item_ids:
                chosen = item_ids[rng.randrange(len(item_ids))]
                sampled.extend(items[chosen])
        boot.append(
            sum(float(pair.contrast) for pair in sampled) / len(sampled)
        )
    low, high = np.quantile(boot, [0.025, 0.975])
    return PlaceboInference(
        mean_contrast=point,
        ci_low=float(low),
        ci_high=float(high),
        valid_pairs=len(valid),
        excluded_pairs=len(pairs) - len(valid),
    )


def h3_inference(
    observations: Sequence[H3Observation],
    *,
    bootstrap_replicates: int = 10_000,
    seed: int = 42,
) -> H3Inference:
    if not observations:
        raise ValueError("H3 requires observations")
    grouped: dict[
        tuple[str, str, float, str], list[float]
    ] = {}
    for observation in observations:
        grouped.setdefault(
            (
                observation.task,
                observation.judge_id,
                observation.pi,
                observation.polarity,
            ),
            [],
        ).append(observation.advantage)
    judge_means = {
        key: sum(values) / len(values) for key, values in grouped.items()
    }
    surface_values: dict[
        tuple[str, str, float], list[float]
    ] = {}
    for (task, _judge, pi, polarity), value in judge_means.items():
        surface_values.setdefault((task, polarity, pi), []).append(value)
    surface: dict[str, dict[str, dict[float, float]]] = {}
    for (task, polarity, pi), values in surface_values.items():
        surface.setdefault(task, {}).setdefault(polarity, {})[pi] = (
            sum(values) / len(values)
        )
    medians: dict[str, dict[str, float]] = {}
    for task, by_polarity in surface.items():
        medians[task] = {}
        for polarity, by_pi in by_polarity.items():
            medians[task][polarity] = float(
                np.median(tuple(by_pi.values()))
            )

    rng = random.Random(seed)
    surface_ci: dict[
        str, dict[str, dict[float, tuple[float, float]]]
    ] = {}
    for (task, polarity, pi), _point_values in surface_values.items():
        relevant = [
            observation
            for observation in observations
            if observation.task == task
            and observation.polarity == polarity
            and observation.pi == pi
        ]
        by_item: dict[str, list[H3Observation]] = {}
        for observation in relevant:
            by_item.setdefault(observation.item_id, []).append(observation)
        item_ids = tuple(by_item)
        boot = []
        for _ in range(bootstrap_replicates):
            sampled = [
                by_item[item_ids[rng.randrange(len(item_ids))]]
                for _index in item_ids
            ]
            by_judge: dict[str, list[float]] = {}
            for item_rows in sampled:
                for observation in item_rows:
                    by_judge.setdefault(
                        observation.judge_id, []
                    ).append(observation.advantage)
            judge_values = [
                sum(values) / len(values)
                for values in by_judge.values()
            ]
            boot.append(sum(judge_values) / len(judge_values))
        low, high = np.quantile(boot, [0.025, 0.975])
        surface_ci.setdefault(task, {}).setdefault(
            polarity, {}
        )[pi] = (float(low), float(high))

    snli = medians["chaosnli_snli"]["not_applicable"]
    mnli = medians["chaosnli_mnli"]["not_applicable"]
    prediction = snli > 0 and mnli > 0 and snli <= mnli
    summeval = medians["summeval_relevance"]
    for polarity in ("upstream_behavior", "semantic_aligned"):
        value = summeval[polarity]
        prediction = prediction and value > 0 and mnli <= value
    return H3Inference(
        task_median_advantage=medians,
        surface=surface,
        surface_ci=surface_ci,
        prediction_met=prediction,
    )


def _pearson(pairs: Sequence[tuple[float, float]]) -> float:
    first = np.array([pair[0] for pair in pairs], dtype=float)
    second = np.array([pair[1] for pair in pairs], dtype=float)
    if np.std(first) == 0 or np.std(second) == 0:
        raise ValueError("Pearson correlation requires nonzero variance")
    return float(np.corrcoef(first, second)[0, 1])
