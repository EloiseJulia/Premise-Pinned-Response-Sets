from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_post_analysis_supplement(
    artifact_root: Path,
    subset_path: Path,
) -> dict:
    analysis_path = artifact_root / "analysis.json"
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    valid_rows = analysis["full_grid"]["item_estimands"]
    valid_keys = {
        (
            row["task"],
            row["item_id"],
            row["model_snapshot"],
            row["temperature"],
        )
        for row in valid_rows
    }
    subset = json.loads(subset_path.read_text(encoding="utf-8"))
    models = (
        "gpt-5.4",
        "gpt-4o-mini-2024-07-18",
        "gemini-3.1-pro-preview",
        "gemini-3.5-flash",
    )
    temperatures = (0.0, 0.7)
    expected_keys = {
        (task, item_id, model, temperature)
        for task, item_ids in subset["items"].items()
        for item_id in item_ids
        for model in models
        for temperature in temperatures
    }

    seed_rows: dict[int, list[dict]] = defaultdict(list)
    grid_valid_by_round: dict[tuple, dict[int, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    one_dim_valid_by_premise: dict[
        tuple, dict[tuple[int, str], int]
    ] = defaultdict(lambda: defaultdict(int))
    inventory = artifact_root / "raw-records.jsonl"
    with inventory.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            coordinate = {
                "task": row["task"],
                "item_id": row["item_id"],
                "model_snapshot": row["model_snapshot"],
                "temperature": row["temperature"],
                "path": row["path"],
                "sample_id": row["sample_id"],
                "premise_round": row["premise_round"],
                "premise_id": row["premise_id"],
            }
            seed_rows[row["seed"]].append(coordinate)
            key = (
                row["task"],
                row["item_id"],
                row["model_snapshot"],
                row["temperature"],
            )
            if (
                row["path"] == "premise_pinned"
                and row["parse_status"] == "ok"
                and row["parsed_choice_hard"] is not None
            ):
                if row["premise_id"] == "__full_grid__":
                    grid_valid_by_round[key][row["premise_round"]] += 1
                elif row["premise_id"] is not None:
                    one_dim_valid_by_premise[key][
                        (row["premise_round"], row["premise_id"])
                    ] += 1

    missing = []
    for key in sorted(expected_keys - valid_keys):
        grid_counts = grid_valid_by_round.get(key, {})
        premise_counts = one_dim_valid_by_premise.get(key, {})
        if not grid_counts:
            reason = "no_valid_full_grid_choices"
        elif all(count < 2 for count in grid_counts.values()):
            reason = "fewer_than_two_valid_grid_combinations_per_round"
        elif not any(count >= 2 for count in premise_counts.values()):
            reason = "no_valid_one_dimensional_hctx"
        else:
            reason = "aggregation_null_other"
        missing.append(
            {
                "task": key[0],
                "item_id": key[1],
                "model_snapshot": key[2],
                "temperature": key[3],
                "reason": reason,
                "valid_grid_choices_by_round": dict(grid_counts),
                "valid_one_dimensional_values": {
                    f"{round_id}|{premise_id}": count
                    for (round_id, premise_id), count in premise_counts.items()
                },
            }
        )

    seed_collisions = [
        {"seed": seed, "coordinates": rows}
        for seed, rows in sorted(seed_rows.items())
        if len(rows) > 1
    ]
    by_task = {}
    for task in subset["items"]:
        expected = sum(key[0] == task for key in expected_keys)
        valid = sum(key[0] == task for key in valid_keys)
        by_task[task] = {
            "expected": expected,
            "valid": valid,
            "excluded": expected - valid,
            "failure_rate": (expected - valid) / expected,
        }
    return {
        "full_grid_coverage": {
            "expected": len(expected_keys),
            "valid": len(valid_keys),
            "excluded": len(expected_keys - valid_keys),
            "failure_rate": (
                len(expected_keys - valid_keys) / len(expected_keys)
            ),
            "by_task": by_task,
            "exclusions": missing,
        },
        "seed_collision_audit": {
            "unique_seeds": len(seed_rows),
            "collision_groups": len(seed_collisions),
            "collisions": seed_collisions,
            "impact": (
                "The duplicate seeds occur on distinct prompts/cache keys; raw "
                "coordinates and outputs remain distinct."
            ),
        },
        "authoritative_artifact_hashes": {
            "analysis_json": sha256_file(analysis_path),
            "raw_run_manifest": sha256_file(
                artifact_root / "run-manifest.json"
            ),
            "specification_curve_manifest": sha256_file(
                artifact_root / "specification-curve-manifest.json"
            ),
            "analysis_upstream": sha256_file(
                artifact_root / "analysis-upstream_behavior.json"
            ),
            "analysis_semantic": sha256_file(
                artifact_root / "analysis-semantic_aligned.json"
            ),
        },
    }


def write_post_analysis_manifest(
    supplement: dict,
    supplement_path: Path,
    manifest_path: Path,
) -> None:
    supplement_path.write_text(
        json.dumps(supplement, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    payload = {
        "manifest_type": "post_analysis_audit",
        "supplement_sha256": sha256_file(supplement_path),
        **supplement["authoritative_artifact_hashes"],
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    payload["manifest_id"] = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
