import pytest

from pydantic import ValidationError

from pprs.manifests.schema import (
    RunManifest,
    SpecificationCurveManifest,
    SummEvalPolarity,
)


def test_specification_curve_hashes_must_be_sha256(
    run_manifest: RunManifest,
) -> None:
    with pytest.raises(ValidationError, match="SHA-256"):
        SpecificationCurveManifest(
            source_run_manifest_id="a" * 64,
            analysis_manifest_ids={
                SummEvalPolarity.UPSTREAM_BEHAVIOR: "x",
                SummEvalPolarity.SEMANTIC_ALIGNED: "y",
            },
            output_locations={
                SummEvalPolarity.UPSTREAM_BEHAVIOR: "artifacts/upstream",
                SummEvalPolarity.SEMANTIC_ALIGNED: "artifacts/semantic",
            },
            output_hashes={
                SummEvalPolarity.UPSTREAM_BEHAVIOR: "",
                SummEvalPolarity.SEMANTIC_ALIGNED: "",
            },
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dataset_revisions", {"chaosnli_snli": "changed"}),
        ("sampled_item_list_hashes", {"chaosnli_snli": "0" * 64}),
        ("task_config_hashes", {"chaosnli_snli": "2" * 64}),
        ("prompt_template_hashes", {"nli-forced-choice-v1": "3" * 64}),
        ("rendered_prompt_ledger_hashes", {"chaosnli_snli": "4" * 64}),
        ("model_provider_map", {"other-snapshot": "other-provider"}),
        ("temperatures", (0.0,)),
        ("top_ps", (0.9,)),
        ("seeds", (8,)),
        ("response_formats", ("text",)),
        ("option_permutation_seeds", (12,)),
        ("path_repetitions", {"forced_choice": 19, "multi_label": 20}),
        ("summ_eval_polarity", SummEvalPolarity.SEMANTIC_ALIGNED),
    ],
)
def test_identity_changes_for_output_affecting_fields(
    run_manifest: RunManifest,
    field: str,
    value: object,
) -> None:
    changed = run_manifest.model_copy(update={field: value})
    assert changed.manifest_id() != run_manifest.manifest_id()


def test_summeval_polarity_arms_have_distinct_outputs(
    run_manifest: RunManifest,
) -> None:
    summeval_updates = {
        "dataset_revisions": {"summeval_relevance": "revision"},
        "sampled_item_list_hashes": {"summeval_relevance": "a" * 64},
        "task_config_hashes": {"summeval_relevance": "b" * 64},
        "rendered_prompt_ledger_hashes": {
            "summeval_relevance": "c" * 64
        },
    }
    upstream = RunManifest.model_validate(
        {
            **run_manifest.model_dump(),
            **summeval_updates,
            "summ_eval_polarity": SummEvalPolarity.UPSTREAM_BEHAVIOR,
        }
    )
    semantic = RunManifest.model_validate(
        {
            **run_manifest.model_dump(),
            **summeval_updates,
            "summ_eval_polarity": SummEvalPolarity.SEMANTIC_ALIGNED,
        }
    )
    curve = SpecificationCurveManifest(
        source_run_manifest_id="a" * 64,
        analysis_manifest_ids={
            SummEvalPolarity.UPSTREAM_BEHAVIOR: upstream.manifest_id(),
            SummEvalPolarity.SEMANTIC_ALIGNED: semantic.manifest_id(),
        },
        output_locations={
            SummEvalPolarity.UPSTREAM_BEHAVIOR: "artifacts/upstream",
            SummEvalPolarity.SEMANTIC_ALIGNED: "artifacts/semantic",
        },
        output_hashes={
            SummEvalPolarity.UPSTREAM_BEHAVIOR: "b" * 64,
            SummEvalPolarity.SEMANTIC_ALIGNED: "c" * 64,
        },
    )
    assert len(set(curve.analysis_manifest_ids.values())) == 2


def test_summeval_polarity_output_collision_fails(
    run_manifest: RunManifest,
) -> None:
    with pytest.raises(ValidationError, match="distinct output locations"):
        SpecificationCurveManifest(
            source_run_manifest_id="a" * 64,
            analysis_manifest_ids={
                SummEvalPolarity.UPSTREAM_BEHAVIOR: run_manifest.manifest_id(),
                SummEvalPolarity.SEMANTIC_ALIGNED: "b" * 64,
            },
            output_locations={
                SummEvalPolarity.UPSTREAM_BEHAVIOR: "artifacts/shared",
                SummEvalPolarity.SEMANTIC_ALIGNED: "artifacts/shared",
            },
            output_hashes={
                SummEvalPolarity.UPSTREAM_BEHAVIOR: "c" * 64,
                SummEvalPolarity.SEMANTIC_ALIGNED: "d" * 64,
            },
        )


def test_empty_identity_mappings_fail(run_manifest: RunManifest) -> None:
    payload = run_manifest.model_dump()
    payload["dataset_revisions"] = {}

    with pytest.raises(ValidationError):
        RunManifest.model_validate(payload)


def test_task_identity_mapping_keys_must_match(
    run_manifest: RunManifest,
) -> None:
    payload = run_manifest.model_dump()
    payload["task_config_hashes"] = {"other_task": "f" * 64}

    with pytest.raises(ValidationError, match="matching keys"):
        RunManifest.model_validate(payload)


def test_manifest_identity_values_cannot_be_blank(
    run_manifest: RunManifest,
) -> None:
    payload = run_manifest.model_dump()
    payload["model_provider_map"] = {"mock-snapshot": ""}

    with pytest.raises(ValidationError, match="cannot be blank"):
        RunManifest.model_validate(payload)


def test_path_repetitions_cannot_be_empty(
    run_manifest: RunManifest,
) -> None:
    payload = run_manifest.model_dump()
    payload["path_repetitions"] = {}

    with pytest.raises(ValidationError):
        RunManifest.model_validate(payload)


def test_summeval_manifest_requires_polarity(
    run_manifest: RunManifest,
) -> None:
    payload = run_manifest.model_dump()
    payload["dataset_revisions"] = {"summeval_relevance": "revision"}
    payload["sampled_item_list_hashes"] = {"summeval_relevance": "a" * 64}
    payload["task_config_hashes"] = {"summeval_relevance": "b" * 64}
    payload["rendered_prompt_ledger_hashes"] = {
        "summeval_relevance": "c" * 64
    }
    payload["summ_eval_polarity"] = None

    with pytest.raises(ValidationError, match="require a polarity"):
        RunManifest.model_validate(payload)


def test_whitespace_identity_values_fail(run_manifest: RunManifest) -> None:
    payload = run_manifest.model_dump()
    payload["run_tag"] = " "
    payload["option_permutation_policy"] = " "
    payload["model_provider_map"] = {" ": " "}

    with pytest.raises(ValidationError, match="cannot be blank"):
        RunManifest.model_validate(payload)
