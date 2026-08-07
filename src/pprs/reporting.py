from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def render_all(
    analysis_path: Path,
    output_dir: Path,
) -> dict[str, Path]:
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    primary = analysis["primary_temperature_0_7"]
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "figure_beta": output_dir / "figure-1-beta-scatter.png",
        "figure_entropy": output_dir / "figure-2-seed-context-entropy.png",
        "figure_regret": output_dir / "figure-3-regret.png",
        "regret_surface": output_dir / "regret-surface.csv",
        "high_risk": output_dir / "high-risk-items.json",
    }
    render_beta_scatter(primary, outputs["figure_beta"])
    render_entropy_scatter(primary, outputs["figure_entropy"])
    render_regret(primary, outputs["figure_regret"])
    write_regret_surface(primary, outputs["regret_surface"])
    write_high_risk(primary, outputs["high_risk"])
    return outputs


def render_beta_scatter(primary: dict, path: Path) -> None:
    rows = [
        row
        for row in primary["beta_scatter_rows"]
        if row["beta_self"] is not None and row["beta_pin"] is not None
    ]
    fig, axis = plt.subplots(figsize=(6, 6))
    tasks = sorted({row["task"] for row in rows})
    colors = {task: plt.cm.tab10(index) for index, task in enumerate(tasks)}
    for task in tasks:
        task_rows = [row for row in rows if row["task"] == task]
        axis.scatter(
            [row["beta_self"] for row in task_rows],
            [row["beta_pin"] for row in task_rows],
            label=task,
            color=colors[task],
        )
    axis.plot([0, 1], [0, 1], linestyle="--", color="black", linewidth=1)
    axis.set(xlim=(0, 1), ylim=(0, 1), xlabel="beta_self", ylabel="beta_pin")
    h1 = primary["h1"]
    if "r" in h1:
        axis.set_title(f"Self-report vs premise-pinned sensitivity (r={h1['r']:.3f})")
    axis.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def render_entropy_scatter(primary: dict, path: Path) -> None:
    rows = [
        row
        for row in primary["diagnostic_rows"]
        if row["h_seed"] is not None and row["h_ctx"] is not None
    ]
    fig, axis = plt.subplots(figsize=(7, 5))
    max_y = max((row["h_ctx"] for row in rows), default=1.0)
    axis.axvspan(0, 0.5, ymin=0, ymax=1, color="red", alpha=0.08)
    tasks = sorted({row["task"] for row in rows})
    colors = {task: plt.cm.tab10(index) for index, task in enumerate(tasks)}
    for task in tasks:
        task_rows = [row for row in rows if row["task"] == task]
        axis.scatter(
            [row["h_seed"] for row in task_rows],
            [row["h_ctx"] for row in task_rows],
            s=12,
            alpha=0.55,
            label=task,
            color=colors[task],
        )
    axis.axvline(0.5, linestyle="--", color="red", linewidth=1)
    axis.axhline(0.0, linestyle="--", color="red", linewidth=1)
    axis.set(
        xlim=(0, None),
        ylim=(0, max_y * 1.05 if max_y else 1),
        xlabel="H_seed (bits)",
        ylabel="H_ctx (bits)",
        title="Seed versus context entropy (danger quadrant: upper-left)",
    )
    axis.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def render_regret(primary: dict, path: Path) -> None:
    rows = [
        row
        for row in primary["regret_surfaces"]
        if row["selected_model"] is not None
    ]
    metrics = sorted({row["metric"] for row in rows})
    consistency_by_task = defaultdict(list)
    bias_by_task = defaultdict(list)
    for row in rows:
        key = (row["metric"], row["task"])
        consistency_by_task[key].append(row["consistency_regret"])
        bias_by_task[key].append(row["bias_regret"])
    consistency = {
        metric: [
            sum(values) / len(values)
            for (candidate, _task), values in consistency_by_task.items()
            if candidate == metric
        ]
        for metric in metrics
    }
    bias = {
        metric: [
            sum(values) / len(values)
            for (candidate, _task), values in bias_by_task.items()
            if candidate == metric
        ]
        for metric in metrics
    }
    x = range(len(metrics))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].bar(
        x,
        [sum(consistency[m]) / len(consistency[m]) for m in metrics],
    )
    axes[1].bar(
        x,
        [sum(bias[m]) / len(bias[m]) for m in metrics],
    )
    for axis, title in zip(
        axes,
        ("Consistency regret", "Bias-MAE regret"),
        strict=True,
    ):
        axis.set_xticks(list(x), metrics, rotation=40, ha="right")
        axis.set_title(title)
        axis.set_ylabel("Regret (lower is better)")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def write_regret_surface(primary: dict, path: Path) -> None:
    rows = primary["regret_surfaces"]
    fields = (
        "task",
        "pi",
        "polarity",
        "tau",
        "metric",
        "selected_model",
        "valid_models",
        "consistency_regret",
        "bias_regret",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_high_risk(primary: dict, path: Path) -> None:
    rows = primary["high_risk_items"]
    if any(
        not (
            row["h_seed"] <= 0.5
            and row["h_ctx"] > 0
            and row["dangerous"] is True
        )
        for row in rows
    ):
        raise ValueError("high-risk export has the wrong measurement direction")
    path.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
