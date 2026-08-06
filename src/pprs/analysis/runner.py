from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict
import itertools
import json
import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from pprs.analysis.inference import (
    aggregate_full_grid_choices,
    bias_regret,
    consistency_regret,
    DangerCell,
    H3Observation,
    PlaceboPairContrast,
    h1_inference,
    h2_inference,
    h3_inference,
    h3_item_advantage,
    modal_label,
    jaccard_similarity,
    placebo_inference,
    select_model,
    squared_set_loss,
)
from pprs.analysis.metrics import (
    PI_GRID,
    danger_quadrant,
    human_response_set,
)
from pprs.analysis.response_sets import (
    aggregate_pinned_choices,
    beta_pin,
    beta_self,
    h_seed,
    label_distribution,
)
from pprs.data.schema import DatasetRecord, TaskId
from pprs.prompts import matched_placebo_components
from pprs.records.schema import ElicitationPath, RawResult


class TemperatureAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    h1: dict
    h2: dict
    h3: dict
    placebo: dict
    metric_surfaces: list[dict]
    regret_surfaces: list[dict]
    entropy_ablation: dict
    beta_scatter_rows: list[dict]
    diagnostic_rows: list[dict]
    high_risk_items: list[dict]
    coverage: dict[str, int]


class ConfirmatoryAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    primary_temperature_0_7: TemperatureAnalysisResult
    temperature_zero_ablation: TemperatureAnalysisResult
    full_grid: dict
    coordinate_validation: dict


def _run_temperature_analysis(
    raw_results: Sequence[RawResult],
    dataset_records: Sequence[DatasetRecord],
    config: dict,
    *,
    temperature: float,
    bootstrap_replicates: int = 10_000,
) -> TemperatureAnalysisResult:
    locked_models = tuple(
        model["model_snapshot"] for model in config["models"]
    )
    if set(locked_models) != {
        "gpt-5.4",
        "gpt-4o-mini-2024-07-18",
        "gemini-3.1-pro-preview",
        "gemini-3.5-flash",
    }:
        raise ValueError("confirmatory model roster changed")
    if tuple(config["thresholds"]["pi"]) != PI_GRID:
        raise ValueError("confirmatory pi grid changed")
    selected = [
        result
        for result in raw_results
        if result.temperature == temperature
        and result.model_snapshot in locked_models
    ]
    forced: dict[tuple, dict[int, str]] = defaultdict(dict)
    response_sets: dict[tuple, dict[int, tuple[str, ...]]] = defaultdict(dict)
    pins: dict[tuple, dict[int, dict[str, list[str | None]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    real_pin: dict[tuple, str] = {}
    placebo_pin: dict[tuple, str] = {}
    placebo_hierarchy: dict[
        tuple, dict[int, dict[str, list[str | None]]]
    ] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for result in selected:
        item_key = (
            result.task,
            result.item_id,
            result.model_snapshot,
        )
        if (
            result.path is ElicitationPath.FORCED_CHOICE
            and result.parsed_choice_hard is not None
        ):
            forced[item_key][result.sample_id] = result.parsed_choice_hard
        elif (
            result.path is ElicitationPath.MULTI_LABEL
            and result.parsed_choice_set is not None
        ):
            response_sets[item_key][result.sample_id] = (
                result.parsed_choice_set
            )
        elif (
            result.path is ElicitationPath.PREMISE_PINNED
            and result.parsed_choice_hard is not None
            and result.premise_id not in (None, "__full_grid__")
        ):
            pins[item_key][result.premise_round][
                result.premise_id
            ].append(result.parsed_choice_hard)
            pair_key = (
                *item_key,
                result.premise_round,
                result.premise_id,
                result.sample_id,
            )
            real_pin[pair_key] = result.parsed_choice_hard
        elif (
            result.path is ElicitationPath.PLACEBO
            and result.parsed_choice_hard is not None
            and result.premise_id is not None
        ):
            real_id = result.premise_id.removeprefix("placebo:")
            pair_key = (
                *item_key,
                result.premise_round,
                real_id,
                result.sample_id,
            )
            placebo_pin[pair_key] = result.parsed_choice_hard
            placebo_hierarchy[item_key][result.premise_round][
                real_id
            ].append(result.parsed_choice_hard)

    aggregations = {}
    danger_cells = []
    beta_pairs = []
    h3_observations = []
    placebo_items = []
    metric_item_rows = []
    downstream_item_rows = []
    entropy_rows = []
    diagnostic_rows = []
    beta_scatter_rows = []
    expected_items_by_task = {
        task.value: sum(record.task is task for record in dataset_records)
        for task in TaskId
    }
    expected_metric_cells = [
        (task.value, model, pi, polarity)
        for task in TaskId
        for model in locked_models
        for pi in PI_GRID
        for polarity in (
            ("upstream_behavior", "semantic_aligned")
            if task is TaskId.SUMMEVAL_RELEVANCE
            else ("not_applicable",)
        )
    ]
    valid_h_seed = 0
    valid_h_ctx = 0

    beta_mapping = config["analysis"]["beta_options"]
    for task in TaskId:
        option_order = (
            ("A", "B")
            if task is TaskId.SUMMEVAL_RELEVANCE
            else ("A", "B", "C")
        )
        task_records = [
            record for record in dataset_records if record.task is task
        ]
        for model in locked_models:
            cell_forced = []
            cell_sets = []
            cell_pprs = []
            for record in task_records:
                key = (task, record.item_id, model)
                forced_choices = tuple(
                    forced[key].get(index) for index in range(20)
                )
                sets = tuple(
                    response_sets[key].get(index) for index in range(20)
                )
                round_values = []
                for premise_round in sorted(pins[key]):
                    premise_values = [
                        pins[key][premise_round][premise_id]
                        for premise_id in sorted(pins[key][premise_round])
                    ]
                    round_values.append(premise_values)
                aggregation = aggregate_pinned_choices(
                    round_values,
                    option_order,
                )
                aggregations[key] = aggregation
                seed_entropy = h_seed(forced_choices, option_order)
                if seed_entropy is not None:
                    valid_h_seed += 1
                if aggregation is not None and aggregation.h_ctx_bits is not None:
                    valid_h_ctx += 1
                danger = (
                    danger_quadrant(
                        seed_entropy,
                        aggregation.h_ctx_bits,
                    )
                    if seed_entropy is not None
                    and aggregation is not None
                    and aggregation.h_ctx_bits is not None
                    else None
                )
                danger_cells.append(
                    DangerCell(
                        task=task.value,
                        item_id=record.item_id,
                        judge_id=model,
                        dangerous=danger,
                    )
                )
                diagnostic_rows.append(
                    {
                        "task": task.value,
                        "item_id": record.item_id,
                        "model_snapshot": model,
                        "temperature": temperature,
                        "h_seed": seed_entropy,
                        "h_ctx": (
                            aggregation.h_ctx_bits
                            if aggregation is not None
                            else None
                        ),
                        "dangerous": danger,
                        "valid_forced_samples": sum(
                            choice is not None for choice in forced_choices
                        ),
                        "valid_pinned_values": (
                            aggregation.valid_pinned_values
                            if aggregation is not None
                            else 0
                        ),
                    }
                )
                cell_forced.append(forced_choices)
                cell_sets.extend(sets)
                cell_pprs.append(
                    aggregation.pprs if aggregation is not None else None
                )

                valid_sets = [item for item in sets if item is not None]
                if aggregation is not None and valid_sets:
                    inclusion = {
                        option: sum(
                            option in response_set
                            for response_set in valid_sets
                        )
                        / len(valid_sets)
                        for option in option_order
                    }
                    for pi in PI_GRID:
                        if task is TaskId.SUMMEVAL_RELEVANCE:
                            source = record.human_label_counts
                            for polarity, counts in (
                                (
                                    "upstream_behavior",
                                    {
                                        "A": source["relevance_0"],
                                        "B": source["relevance_1"],
                                    },
                                ),
                                (
                                    "semantic_aligned",
                                    {
                                        "A": source["relevance_1"],
                                        "B": source["relevance_0"],
                                    },
                                ),
                            ):
                                human = human_response_set(counts, pi)
                                h3_observations.append(
                                    H3Observation(
                                        task=task.value,
                                        item_id=record.item_id,
                                        judge_id=model,
                                        pi=pi,
                                        polarity=polarity,
                                        advantage=h3_item_advantage(
                                            inclusion,
                                            aggregation.pprs,
                                            human,
                                            option_order,
                                        ),
                                    )
                                )
                                _append_metric_rows(
                                    metric_item_rows,
                                    downstream_item_rows,
                                    record=record,
                                    model=model,
                                    pi=pi,
                                    polarity=polarity,
                                    option_order=option_order,
                                    forced_choices=forced_choices,
                                    self_inclusion=inclusion,
                                    pprs=aggregation.pprs,
                                    pin_distribution=aggregation.distribution,
                                    human_counts=counts,
                                    tau_values=tuple(
                                        config["thresholds"]["tau"]
                                    ),
                                )
                        else:
                            human = human_response_set(
                                record.human_label_counts,
                                pi,
                            )
                            h3_observations.append(
                                H3Observation(
                                    task=task.value,
                                    item_id=record.item_id,
                                    judge_id=model,
                                    pi=pi,
                                    polarity="not_applicable",
                                    advantage=h3_item_advantage(
                                        inclusion,
                                        aggregation.pprs,
                                        human,
                                        option_order,
                                    ),
                                )
                            )
                            _append_metric_rows(
                                metric_item_rows,
                                downstream_item_rows,
                                record=record,
                                model=model,
                                pi=pi,
                                polarity="not_applicable",
                                option_order=option_order,
                                forced_choices=forced_choices,
                                self_inclusion=inclusion,
                                pprs=aggregation.pprs,
                                pin_distribution=aggregation.distribution,
                                human_counts=record.human_label_counts,
                                tau_values=tuple(
                                    config["thresholds"]["tau"]
                                ),
                            )

                matched_keys = [
                    pair_key
                    for pair_key in real_pin
                    if pair_key[:3] == key and pair_key in placebo_pin
                ]
                baseline = modal_label(forced_choices, option_order)
                for pair_key in matched_keys:
                    contrast = (
                        float(real_pin[pair_key] != baseline)
                        - float(placebo_pin[pair_key] != baseline)
                        if baseline is not None
                        else None
                    )
                    placebo_items.append(
                        PlaceboPairContrast(
                            task=task.value,
                            item_id=record.item_id,
                            judge_id=model,
                            contrast=contrast,
                        )
                    )
                placebo_rounds = [
                    [
                        placebo_hierarchy[key][round_index][premise_id]
                        for premise_id in sorted(
                            placebo_hierarchy[key][round_index]
                        )
                    ]
                    for round_index in sorted(placebo_hierarchy[key])
                ]
                placebo_aggregation = aggregate_pinned_choices(
                    placebo_rounds,
                    option_order,
                )
                entropy_rows.append(
                    {
                        "task": task.value,
                        "model_snapshot": model,
                        "item_id": record.item_id,
                        "real_h_ctx": (
                            aggregation.h_ctx_bits
                            if aggregation is not None
                            else None
                        ),
                        "placebo_h_ctx": (
                            placebo_aggregation.h_ctx_bits
                            if placebo_aggregation is not None
                            else None
                        ),
                    }
                )

            mapping = beta_mapping[task.value]
            flat_forced = [
                choice for choices in cell_forced for choice in choices
            ]
            self_beta = beta_self(
                flat_forced,
                cell_sets,
                positive_option=mapping["positive"],
                negative_option=mapping["negative"],
            )
            pin_beta = beta_pin(
                cell_forced,
                cell_pprs,
                positive_option=mapping["positive"],
                negative_option=mapping["negative"],
            )
            beta_pairs.append((self_beta, pin_beta))
            beta_scatter_rows.append(
                {
                    "task": task.value,
                    "model_snapshot": model,
                    "temperature": temperature,
                    "beta_self": self_beta,
                    "beta_pin": pin_beta,
                }
            )

    def infer_or_error(callable_, *args):
        try:
            return asdict(
                callable_(
                    *args,
                    bootstrap_replicates=bootstrap_replicates,
                )
            )
        except ValueError as exc:
            return {"error": str(exc)}

    metric_surfaces = _aggregate_metric_rows(
        metric_item_rows,
        expected_items_by_task,
        expected_metric_cells,
    )
    return TemperatureAnalysisResult(
        h1=infer_or_error(h1_inference, beta_pairs),
        h2=infer_or_error(h2_inference, danger_cells),
        h3=infer_or_error(h3_inference, h3_observations),
        placebo=infer_or_error(placebo_inference, placebo_items),
        metric_surfaces=metric_surfaces,
        regret_surfaces=_build_regret_surfaces(
            metric_surfaces,
            downstream_item_rows,
            tuple(config["thresholds"]["tau"]),
        ),
        entropy_ablation=_aggregate_entropy_rows(entropy_rows),
        beta_scatter_rows=beta_scatter_rows,
        diagnostic_rows=diagnostic_rows,
        high_risk_items=[
            row for row in diagnostic_rows if row["dangerous"] is True
        ],
        coverage={
            "raw_results": len(raw_results),
            "temperature_results": len(selected),
            "dataset_records": len(dataset_records),
            "valid_h_seed_cells": valid_h_seed,
            "valid_h_ctx_cells": valid_h_ctx,
            "h3_observations": len(h3_observations),
        },
    )


def _append_metric_rows(
    metric_rows: list[dict],
    downstream_rows: list[dict],
    *,
    record: DatasetRecord,
    model: str,
    pi: float,
    polarity: str,
    option_order: tuple[str, ...],
    forced_choices: Sequence[str | None],
    self_inclusion: dict[str, float],
    pprs: tuple[str, ...],
    pin_distribution: dict[str, float] | None,
    human_counts: dict[str, int],
    tau_values: tuple[float, ...],
) -> None:
    valid_forced = tuple(
        choice for choice in forced_choices if choice is not None
    )
    if not valid_forced:
        return
    judge_forced = label_distribution(valid_forced, option_order)
    total = sum(human_counts.values())
    human_forced = {
        option: human_counts[option] / total for option in option_order
    }
    human_set = human_response_set(human_counts, pi)
    judge_hard = modal_label(valid_forced, option_order)
    human_hard = modal_label(
        [
            option
            for option in option_order
            for _ in range(human_counts[option])
        ],
        option_order,
    )
    epsilon = 1e-10
    kl_hj = sum(
        human_forced[option]
        * math.log(
            max(human_forced[option], epsilon)
            / max(judge_forced[option], epsilon)
        )
        for option in option_order
    )
    kl_jh = sum(
        judge_forced[option]
        * math.log(
            max(judge_forced[option], epsilon)
            / max(human_forced[option], epsilon)
        )
        for option in option_order
    )
    metric_rows.append(
        {
            "task": record.task.value,
            "item_id": record.item_id,
            "model_snapshot": model,
            "pi": pi,
            "polarity": polarity,
            "Hit Rate": float(judge_hard == human_hard),
            "KL(h,j)": kl_hj,
            "KL(j,h)": kl_jh,
            "Coverage": float(judge_hard in human_set),
            "MSE_self": squared_set_loss(
                self_inclusion,
                human_set,
                option_order,
            ),
            "MSE_pin": squared_set_loss(
                {
                    option: float(option in pprs)
                    for option in option_order
                },
                human_set,
                option_order,
            ),
        }
    )
    positive = "A"
    if pin_distribution is None:
        return
    pin_positive = pin_distribution[positive]
    human_positive = human_forced[positive]
    for tau in tau_values:
        downstream_rows.append(
            {
                "task": record.task.value,
                "item_id": record.item_id,
                "model_snapshot": model,
                "pi": pi,
                "polarity": polarity,
                "tau": tau,
                "judge_positive": pin_positive > tau,
                "human_positive": human_positive > tau,
            }
        )


def _aggregate_metric_rows(
    rows: list[dict],
    expected_items_by_task: dict[str, int] | None = None,
    expected_cells: Sequence[tuple[str, str, float, str]] | None = None,
) -> list[dict]:
    grouped = defaultdict(list)
    metric_names = (
        "Hit Rate",
        "KL(h,j)",
        "KL(j,h)",
        "Coverage",
        "MSE_self",
        "MSE_pin",
    )
    for row in rows:
        key = (
            row["task"],
            row["model_snapshot"],
            row["pi"],
            row["polarity"],
        )
        grouped[key].append(row)
    keys = (
        set(expected_cells)
        if expected_cells is not None
        else set(grouped)
    )
    output = []
    for key in sorted(keys):
        values = grouped.get(key, [])
        task, model, pi, polarity = key
        expected_items = (
            expected_items_by_task[task]
            if expected_items_by_task is not None
            else len(values)
        )
        output.append(
            {
                "task": task,
                "model_snapshot": model,
                "pi": pi,
                "polarity": polarity,
                "valid_items": len(values),
                "expected_items": expected_items,
                "failure_rate": (
                    1 - len(values) / expected_items
                    if expected_items
                    else 0.0
                ),
                **{
                    metric: (
                        sum(row[metric] for row in values) / len(values)
                        if values
                        else None
                    )
                    for metric in metric_names
                },
            }
        )
    return output


def _build_regret_surfaces(
    metrics: list[dict],
    downstream_rows: list[dict],
    tau_values: tuple[float, ...] | None = None,
) -> list[dict]:
    downstream_grouped = defaultdict(list)
    for row in downstream_rows:
        key = (
            row["task"],
            row["model_snapshot"],
            row["pi"],
            row["polarity"],
            row["tau"],
        )
        downstream_grouped[key].append(row)
    downstream = {}
    for key, rows in downstream_grouped.items():
        judge_rate = sum(row["judge_positive"] for row in rows) / len(rows)
        human_rate = sum(row["human_positive"] for row in rows) / len(rows)
        downstream[key] = {
            "consistency": sum(
                row["judge_positive"] == row["human_positive"] for row in rows
            )
            / len(rows),
            "bias_mae": abs(judge_rate - human_rate),
        }
    metrics_by_surface = defaultdict(dict)
    for row in metrics:
        surface = (row["task"], row["pi"], row["polarity"])
        metrics_by_surface[surface][row["model_snapshot"]] = row
    output = []
    directions = {
        "Hit Rate": False,
        "KL(h,j)": True,
        "KL(j,h)": True,
        "Coverage": False,
        "MSE_self": True,
        "MSE_pin": True,
    }
    for surface, by_model in sorted(metrics_by_surface.items()):
        task, pi, polarity = surface
        surface_taus = (
            tuple(sorted(tau_values))
            if tau_values is not None
            else tuple(
                sorted(
                    {
                        key[4]
                        for key in downstream
                        if key[:1] == (task,)
                        and key[2] == pi
                        and key[3] == polarity
                    }
                )
            )
        )
        for tau in surface_taus:
            consistency = {
                model: downstream[(task, model, pi, polarity, tau)][
                    "consistency"
                ]
                for model in by_model
                if (task, model, pi, polarity, tau) in downstream
            }
            bias = {
                model: downstream[(task, model, pi, polarity, tau)][
                    "bias_mae"
                ]
                for model in by_model
                if (task, model, pi, polarity, tau) in downstream
            }
            for metric, lower_is_better in directions.items():
                eligible = {
                    model: values[metric]
                    for model, values in by_model.items()
                    if values[metric] is not None
                    and (task, model, pi, polarity, tau) in downstream
                }
                if not eligible:
                    output.append(
                        {
                            "task": task,
                            "pi": pi,
                            "polarity": polarity,
                            "tau": tau,
                            "metric": metric,
                            "selected_model": None,
                            "eligible_models": [],
                            "valid_models": 0,
                            "consistency_regret": None,
                            "bias_regret": None,
                        }
                    )
                    continue
                selected = select_model(
                    eligible,
                    lower_is_better=lower_is_better,
                )
                eligible_models = sorted(eligible)
                output.append(
                    {
                        "task": task,
                        "pi": pi,
                        "polarity": polarity,
                        "tau": tau,
                        "metric": metric,
                        "selected_model": selected,
                        "eligible_models": eligible_models,
                        "valid_models": len(eligible_models),
                        "consistency_regret": consistency_regret(
                            {
                                model: consistency[model]
                                for model in eligible_models
                            },
                            selected,
                        ),
                        "bias_regret": bias_regret(
                            {
                                model: bias[model]
                                for model in eligible_models
                            },
                            selected,
                        ),
                    }
                )
    return output


def _aggregate_entropy_rows(rows: list[dict]) -> dict:
    valid = [
        row
        for row in rows
        if row["real_h_ctx"] is not None
        and row["placebo_h_ctx"] is not None
    ]
    if not valid:
        return {"n": 0, "mean_real_h_ctx": None, "mean_placebo_h_ctx": None}
    return {
        "n": len(valid),
        "mean_real_h_ctx": sum(row["real_h_ctx"] for row in valid)
        / len(valid),
        "mean_placebo_h_ctx": sum(row["placebo_h_ctx"] for row in valid)
        / len(valid),
    }


def run_confirmatory_analysis(
    raw_results: Sequence[RawResult],
    dataset_records: Sequence[DatasetRecord],
    config: dict,
) -> ConfirmatoryAnalysisResult:
    validation = _validate_coordinate_grid(
        raw_results,
        dataset_records,
        config,
    )
    replicates = config["analysis"]["bootstrap_replicates"]
    primary = _run_temperature_analysis(
        raw_results,
        dataset_records,
        config,
        temperature=0.7,
        bootstrap_replicates=replicates,
    )
    zero = _run_temperature_analysis(
        raw_results,
        dataset_records,
        config,
        temperature=0.0,
        bootstrap_replicates=replicates,
    )
    return ConfirmatoryAnalysisResult(
        primary_temperature_0_7=primary,
        temperature_zero_ablation=zero,
        full_grid=_analyze_full_grid(raw_results),
        coordinate_validation=validation,
    )


def _validate_coordinate_grid(
    raw_results: Sequence[RawResult],
    dataset_records: Sequence[DatasetRecord],
    config: dict,
) -> dict:
    models = tuple(model["model_snapshot"] for model in config["models"])
    temperatures = tuple(config["temperatures"])
    item_ids = {(record.task, record.item_id) for record in dataset_records}
    seen_cache = set()
    seen_coordinates = set()
    fixed_actual = set()
    disclosure_actual = set()
    real_pin_actual = set()
    placebo_actual = set()
    full_grid_actual = set()
    successful_disclosures = []
    for result in raw_results:
        if result.cache_key in seen_cache:
            raise ValueError("duplicate cache key in raw results")
        seen_cache.add(result.cache_key)
        if result.model_snapshot not in models:
            raise ValueError("raw result contains an unlocked model")
        if result.temperature not in temperatures or result.top_p != 1.0:
            raise ValueError("raw result contains unlocked sampling parameters")
        if result.prereg_tag != config["prereg_tag"]:
            raise ValueError("raw result lacks the frozen preregistration tag")
        if (result.task, result.item_id) not in item_ids:
            raise ValueError("raw result item is outside frozen samples")
        coordinate = (
            result.task,
            result.item_id,
            result.model_snapshot,
            result.temperature,
            result.path,
            result.sample_id,
            result.premise_round,
            result.premise_id,
            result.premise_value,
        )
        if coordinate in seen_coordinates:
            raise ValueError("duplicate experiment coordinate")
        seen_coordinates.add(coordinate)
        if result.path in {
            ElicitationPath.FORCED_CHOICE,
            ElicitationPath.MULTI_LABEL,
        }:
            fixed_actual.add(
                (
                    result.task,
                    result.item_id,
                    result.model_snapshot,
                    result.temperature,
                    result.path,
                    result.sample_id,
                )
            )
        if (
            result.path is ElicitationPath.PREMISE_PINNED
            and result.premise_id is None
        ):
            disclosure_actual.add(
                (
                    result.task,
                    result.item_id,
                    result.model_snapshot,
                    result.temperature,
                    result.premise_round,
                )
            )
            if result.parsed_premises is not None:
                successful_disclosures.append(result)
        elif (
            result.path is ElicitationPath.PREMISE_PINNED
            and result.premise_id == "__full_grid__"
        ):
            full_grid_actual.add(
                (
                    result.task,
                    result.item_id,
                    result.model_snapshot,
                    result.temperature,
                    result.premise_round,
                    result.sample_id,
                    result.premise_value,
                )
            )
        elif (
            result.path is ElicitationPath.PREMISE_PINNED
            and result.premise_id is not None
        ):
            real_pin_actual.add(
                (
                    result.task,
                    result.item_id,
                    result.model_snapshot,
                    result.temperature,
                    result.premise_round,
                    result.premise_id,
                    result.sample_id,
                    result.premise_value,
                )
            )
        elif result.path is ElicitationPath.PLACEBO:
            placebo_actual.add(
                (
                    result.task,
                    result.item_id,
                    result.model_snapshot,
                    result.temperature,
                    result.premise_round,
                    result.premise_id,
                    result.sample_id,
                    result.premise_value,
                )
            )
    expected_fixed = set()
    expected_disclosure = set()
    for task, item_id in item_ids:
        for model in models:
            for temperature in temperatures:
                for path, repetitions in (
                    (ElicitationPath.FORCED_CHOICE, 20),
                    (ElicitationPath.MULTI_LABEL, 20),
                ):
                    expected_fixed.update(
                        (
                            task,
                            item_id,
                            model,
                            temperature,
                            path,
                            sample_id,
                        )
                        for sample_id in range(repetitions)
                    )
                expected_disclosure.update(
                    (
                        task,
                        item_id,
                        model,
                        temperature,
                        premise_round,
                    )
                    for premise_round in range(3)
                )
    if fixed_actual != expected_fixed:
        raise ValueError("fixed F/S coordinate grid is incomplete or excessive")
    if disclosure_actual != expected_disclosure:
        raise ValueError("premise-disclosure grid is incomplete or excessive")
    full_grid_subset = json.loads(
        Path("configs/samples/full-grid-ablation-v1.json").read_text()
    )["items"]
    full_grid_ids = {
        (TaskId(task), item_id)
        for task, ids in full_grid_subset.items()
        for item_id in ids
    }
    expected_real = set()
    expected_placebo = set()
    expected_grid = set()
    for disclosure in successful_disclosures:
        premises = disclosure.parsed_premises
        for premise in premises:
            for value_index, value in enumerate(premise.candidate_values):
                base = (
                    disclosure.task,
                    disclosure.item_id,
                    disclosure.model_snapshot,
                    disclosure.temperature,
                    disclosure.premise_round,
                )
                expected_real.add(
                    (
                        *base,
                        premise.premise_id,
                        value_index,
                        value,
                    )
                )
                _statement, placebo_value = matched_placebo_components(
                    premise.statement,
                    value,
                )
                expected_placebo.add(
                    (
                        *base,
                        f"placebo:{premise.premise_id}",
                        value_index,
                        placebo_value,
                    )
                )
        if (disclosure.task, disclosure.item_id) in full_grid_ids:
            for combo_index, values in enumerate(
                itertools.product(
                    *(
                        premise.candidate_values
                        for premise in premises
                    )
                )
            ):
                canonical = json.dumps(
                    [
                        {
                            "premise_id": premise.premise_id,
                            "premise_type": premise.premise_type.value,
                            "premise_value": value,
                        }
                        for premise, value in zip(
                            premises,
                            values,
                            strict=True,
                        )
                    ],
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                expected_grid.add(
                    (
                        disclosure.task,
                        disclosure.item_id,
                        disclosure.model_snapshot,
                        disclosure.temperature,
                        disclosure.premise_round,
                        combo_index,
                        canonical,
                    )
                )
    if real_pin_actual != expected_real:
        raise ValueError("real-pin coordinate grid is incomplete or excessive")
    if placebo_actual != expected_placebo:
        raise ValueError("placebo coordinate grid is incomplete or excessive")
    if full_grid_actual != expected_grid:
        raise ValueError("full-grid coordinate grid is incomplete or excessive")
    git_shas = {result.git_sha for result in raw_results}
    if len(git_shas) != 1:
        raise ValueError("raw results contain multiple Git SHAs")
    return {
        "raw_records": len(raw_results),
        "unique_coordinates": len(seen_coordinates),
        "fixed_coordinates": len(fixed_actual),
        "disclosure_coordinates": len(disclosure_actual),
        "real_pin_coordinates": len(real_pin_actual),
        "placebo_coordinates": len(placebo_actual),
        "full_grid_coordinates": len(full_grid_actual),
        "git_sha": next(iter(git_shas)),
    }


def _analyze_full_grid(raw_results: Sequence[RawResult]) -> dict:
    one_dimensional = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    grid = defaultdict(lambda: defaultdict(list))
    for result in raw_results:
        if (
            result.path is ElicitationPath.PREMISE_PINNED
            and result.parsed_choice_hard is not None
        ):
            key = (
                result.task,
                result.item_id,
                result.model_snapshot,
                result.temperature,
            )
            if result.premise_id == "__full_grid__":
                grid[key][result.premise_round].append(
                    result.parsed_choice_hard
                )
            elif result.premise_id is not None:
                one_dimensional[key][result.premise_round][
                    result.premise_id
                ].append(result.parsed_choice_hard)
    items = []
    for key, grid_rounds in grid.items():
        task, item_id, model, temperature = key
        option_order = (
            ("A", "B")
            if task is TaskId.SUMMEVAL_RELEVANCE
            else ("A", "B", "C")
        )
        grid_aggregation = aggregate_full_grid_choices(
            [grid_rounds[index] for index in sorted(grid_rounds)],
            option_order,
        )
        pin_rounds = [
            [
                one_dimensional[key][round_index][premise_id]
                for premise_id in sorted(one_dimensional[key][round_index])
            ]
            for round_index in sorted(one_dimensional[key])
        ]
        pin_aggregation = aggregate_pinned_choices(
            pin_rounds,
            option_order,
        )
        if grid_aggregation is None or pin_aggregation is None:
            continue
        items.append(
            {
                "task": task.value,
                "item_id": item_id,
                "model_snapshot": model,
                "temperature": temperature,
                "h_grid": grid_aggregation.h_ctx_bits,
                "h_ctx": pin_aggregation.h_ctx_bits,
                "delta_h": (
                    grid_aggregation.h_ctx_bits - pin_aggregation.h_ctx_bits
                    if grid_aggregation.h_ctx_bits is not None
                    and pin_aggregation.h_ctx_bits is not None
                    else None
                ),
                "grid_union": grid_aggregation.pprs,
                "pprs": pin_aggregation.pprs,
                "jaccard": jaccard_similarity(
                    grid_aggregation.pprs,
                    pin_aggregation.pprs,
                ),
            }
        )
    return {"item_estimands": items, "n_items": len(items)}
