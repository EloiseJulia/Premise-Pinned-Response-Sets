from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pprs.data.schema import DatasetRecord, TaskId
from pprs.manifests.schema import RunManifest, SummEvalPolarity
from pprs.records.schema import ElicitationPath, ParseStatus, RawResult


@pytest.fixture
def dataset_record() -> DatasetRecord:
    return DatasetRecord(
        task=TaskId.CHAOSNLI_SNLI,
        item_id="46359n",
        source_dataset="ChaosNLI",
        source_revision="37b8d7863430ec3433d6a73da08408b064643b8b",
        source_object_id="aea16e8f1e868493da3913e3d84c0ba0373bab33",
        source_split="snli",
        source_original_id="46359n",
        sampling_seed=42,
        inputs={"context": "Premise", "statement": "Hypothesis"},
        human_label_counts={"A": 76, "B": 20, "C": 4},
        human_label_distribution={"A": 0.76, "B": 0.20, "C": 0.04},
        ratings_per_item=100,
        license_identifier="CC-BY-NC-4.0",
        license_source="https://github.com/easonnie/ChaosNLI/blob/f358e234ea2797d9298f7b0213bf1308b6d7756b/LICENSE",
        data_card_source="https://github.com/easonnie/ChaosNLI/blob/f358e234ea2797d9298f7b0213bf1308b6d7756b/README.md",
        data_card_revision="f358e234ea2797d9298f7b0213bf1308b6d7756b",
        data_card_blob="967b5a2becf268a18a7d1615ea11bfb5e8423352",
    )


@pytest.fixture
def raw_result() -> RawResult:
    return RawResult(
        cache_key="a" * 64,
        run_tag="fixture",
        git_sha="b" * 40,
        prereg_tag=None,
        task=TaskId.CHAOSNLI_SNLI,
        item_id="46359n",
        judge_id="mock-judge",
        path=ElicitationPath.FORCED_CHOICE,
        sample_id=0,
        premise_id=None,
        premise_type=None,
        premise_value=None,
        premise_round=None,
        pinning_assignments=None,
        model_snapshot="mock-snapshot",
        provider="mock",
        temperature=0.0,
        top_p=1.0,
        seed=7,
        prompt_template_id="nli-forced-choice-v1",
        prompt_hash="c" * 64,
        option_permutation_seed=11,
        raw_text="A",
        parsed_choice_hard="A",
        parsed_choice_set=None,
        parsed_premises=None,
        parse_status=ParseStatus.OK,
        provider_error=None,
        http_status=200,
        system_fingerprint="fixture-fingerprint",
        retry_count=0,
        prompt_tokens=10,
        completion_tokens=1,
        wall_clock_ms=5,
        ts_utc=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )


@pytest.fixture
def run_manifest() -> RunManifest:
    return RunManifest(
        manifest_role="raw_collection",
        run_tag="fixture",
        git_sha="d" * 40,
        prereg_tag=None,
        dataset_revisions={
            "chaosnli_snli": "37b8d7863430ec3433d6a73da08408b064643b8b"
        },
        sampled_item_list_hashes={"chaosnli_snli": "e" * 64},
        task_config_hashes={"chaosnli_snli": "f" * 64},
        prompt_template_hashes={"nli-forced-choice-v1": "1" * 64},
        rendered_prompt_ledger_hashes={"chaosnli_snli": "2" * 64},
        model_provider_map={"mock-snapshot": "mock"},
        temperatures=(0.0, 0.7),
        top_ps=(1.0,),
        seeds=(7,),
        response_formats=("json",),
        option_permutation_policy="per-item seeded shuffle",
        option_permutation_seeds=(11,),
        path_repetitions={"forced_choice": 20, "multi_label": 20},
        summ_eval_polarity=None,
        output_locations={"raw": "artifacts/raw"},
        output_hashes={"raw": "3" * 64},
    )
