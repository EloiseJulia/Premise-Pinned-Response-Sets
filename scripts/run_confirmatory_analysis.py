from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from pprs.analysis.runner import run_confirmatory_analysis
from pprs.data.schema import DatasetRecord, TaskId
from pprs.pilot import load_and_validate_sample
from pprs.records.schema import RawResult
from pprs.freeze import validate_freeze
from pprs.manifests.schema import (
    RunManifest,
    SpecificationCurveManifest,
    SummEvalPolarity,
)
from pprs.run_manifest import (
    sha256_file,
    validate_raw_run_manifest,
    write_run_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("artifacts/wp7-full-v3/cache"),
    )
    parser.add_argument("--trusted-raw-manifest-sha256", required=True)
    parser.add_argument("--trusted-raw-manifest-id", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/wp7-full-v3/analysis.json"),
    )
    args = parser.parse_args()
    freeze_sha = validate_freeze(
        freeze_path=Path("configs/runs/confirmatory-v3.freeze.json"),
        expected_tag="pprs-prereg-v3",
    )
    raw_manifest_path = args.cache_dir.parent / "run-manifest.json"
    raw_manifest = validate_raw_run_manifest(
        raw_manifest_path,
        expected_git_sha=freeze_sha,
        trusted_manifest_sha256=args.trusted_raw_manifest_sha256,
        trusted_manifest_id=args.trusted_raw_manifest_id,
        expected_prereg_tag="pprs-prereg-v3",
    )
    inventory_path = Path(
        raw_manifest.output_locations["raw_inventory"]
    )
    raw_results = [
        RawResult.model_validate_json(line)
        for line in inventory_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    sample_paths = {
        TaskId.CHAOSNLI_SNLI: (
            Path("data/processed/chaosnli-snli.parquet"),
            Path("configs/samples/chaosnli-snli-seed42.json"),
        ),
        TaskId.CHAOSNLI_MNLI: (
            Path("data/processed/chaosnli-mnli.parquet"),
            Path("configs/samples/chaosnli-mnli-seed42.json"),
        ),
        TaskId.SUMMEVAL_RELEVANCE: (
            Path("data/processed/summeval-relevance.parquet"),
            Path("configs/samples/summeval-relevance-seed42.json"),
        ),
    }
    records: list[DatasetRecord] = [
        record
        for task in TaskId
        for record in load_and_validate_sample(*sample_paths[task])[0]
    ]
    config = json.loads(
        Path("configs/runs/confirmatory-v1.json").read_text()
    )
    result = run_confirmatory_analysis(
        raw_results,
        records,
        config,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        result.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    raw_manifest_payload = json.loads(raw_manifest_path.read_text())
    source_run_manifest_id = raw_manifest_payload.pop("manifest_id")
    analysis_ids = {}
    locations = {}
    hashes = {}
    result_payload = result.model_dump(mode="json")
    for polarity in (
        SummEvalPolarity.UPSTREAM_BEHAVIOR,
        SummEvalPolarity.SEMANTIC_ALIGNED,
    ):
        arm_payload = _filter_polarity(result_payload, polarity.value)
        arm_path = args.output.parent / f"analysis-{polarity.value}.json"
        arm_path.write_text(
            json.dumps(arm_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest_data = {
            **raw_manifest_payload,
            "manifest_role": "analysis",
            "run_tag": f"wp7-analysis-{polarity.value}",
            "summ_eval_polarity": polarity.value,
            "output_locations": {"analysis": str(arm_path)},
            "output_hashes": {"analysis": sha256_file(arm_path)},
        }
        manifest = RunManifest.model_validate(manifest_data)
        manifest_path = (
            args.output.parent / f"manifest-{polarity.value}.json"
        )
        write_run_manifest(manifest, manifest_path)
        analysis_ids[polarity] = manifest.manifest_id()
        locations[polarity] = str(arm_path)
        hashes[polarity] = sha256_file(arm_path)
    curve = SpecificationCurveManifest(
        source_run_manifest_id=source_run_manifest_id,
        analysis_manifest_ids=analysis_ids,
        output_locations=locations,
        output_hashes=hashes,
    )
    (args.output.parent / "specification-curve-manifest.json").write_text(
        curve.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)


def _filter_polarity(payload: dict, polarity: str) -> dict:
    filtered = copy.deepcopy(payload)
    for temperature_key in (
        "primary_temperature_0_7",
        "temperature_zero_ablation",
    ):
        section = filtered[temperature_key]
        h3 = section["h3"]
        if "error" not in h3:
            h3["task_median_advantage"]["summeval_relevance"] = {
                polarity: h3["task_median_advantage"][
                    "summeval_relevance"
                ][polarity]
            }
            h3["surface"]["summeval_relevance"] = {
                polarity: h3["surface"]["summeval_relevance"][polarity]
            }
            h3["surface_ci"]["summeval_relevance"] = {
                polarity: h3["surface_ci"]["summeval_relevance"][polarity]
            }
        section["metric_surfaces"] = [
            row
            for row in section["metric_surfaces"]
            if row["task"] != "summeval_relevance"
            or row["polarity"] == polarity
        ]
        section["regret_surfaces"] = [
            row
            for row in section["regret_surfaces"]
            if row["task"] != "summeval_relevance"
            or row["polarity"] == polarity
        ]
    return filtered


if __name__ == "__main__":
    main()
