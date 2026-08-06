from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SummEvalPolarity(StrEnum):
    UPSTREAM_BEHAVIOR = "upstream_behavior"
    SEMANTIC_ALIGNED = "semantic_aligned"


class RunManifest(StrictModel):
    manifest_role: Literal["raw_collection", "analysis"]
    run_tag: str = Field(min_length=1)
    git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    prereg_tag: str | None

    dataset_revisions: dict[str, str] = Field(min_length=1)
    sampled_item_list_hashes: dict[str, str] = Field(min_length=1)
    task_config_hashes: dict[str, str] = Field(min_length=1)
    prompt_template_hashes: dict[str, str] = Field(min_length=1)
    rendered_prompt_ledger_hashes: dict[str, str] = Field(min_length=1)

    model_provider_map: dict[str, str] = Field(min_length=1)
    temperatures: tuple[float, ...] = Field(min_length=1)
    top_ps: tuple[float, ...] = Field(min_length=1)
    seeds: tuple[int, ...] = Field(min_length=1)
    response_formats: tuple[str, ...] = Field(min_length=1)
    option_permutation_policy: str = Field(min_length=1)
    option_permutation_seeds: tuple[int, ...] = Field(min_length=1)
    path_repetitions: dict[str, int] = Field(min_length=1)

    summ_eval_polarity: SummEvalPolarity | None
    output_locations: dict[str, str] = Field(min_length=1)
    output_hashes: dict[str, str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_identity_dimensions(self) -> RunManifest:
        if not self.run_tag.strip():
            raise ValueError("run tag cannot be blank")
        if not self.option_permutation_policy.strip():
            raise ValueError("option permutation policy cannot be blank")
        task_key_sets = (
            set(self.dataset_revisions),
            set(self.sampled_item_list_hashes),
            set(self.task_config_hashes),
            set(self.rendered_prompt_ledger_hashes),
        )
        if len({frozenset(keys) for keys in task_key_sets}) != 1:
            raise ValueError("task identity mappings must use matching keys")
        if set(self.output_locations) != set(self.output_hashes):
            raise ValueError("output locations and hashes must use matching keys")
        all_mappings = (
            self.dataset_revisions,
            self.sampled_item_list_hashes,
            self.task_config_hashes,
            self.prompt_template_hashes,
            self.rendered_prompt_ledger_hashes,
            self.model_provider_map,
            self.path_repetitions,
            self.output_locations,
            self.output_hashes,
        )
        if any(
            not key.strip()
            or (isinstance(value, str) and not value.strip())
            for mapping in all_mappings
            for key, value in mapping.items()
        ):
            raise ValueError("manifest identity text values cannot be blank")
        if any(not value for value in self.response_formats):
            raise ValueError("response formats cannot be blank")
        includes_summeval = any(
            task_key == "summeval_relevance"
            for task_key in self.dataset_revisions
        )
        if (
            self.manifest_role == "analysis"
            and includes_summeval
            and self.summ_eval_polarity is None
        ):
            raise ValueError("SummEval manifests require a polarity identity")
        if (
            self.manifest_role == "raw_collection"
            and self.summ_eval_polarity is not None
        ):
            raise ValueError(
                "raw collection manifests cannot select a polarity"
            )
        if not includes_summeval and self.summ_eval_polarity is not None:
            raise ValueError(
                "non-SummEval manifests cannot carry a polarity identity"
            )
        hash_mappings = (
            self.sampled_item_list_hashes,
            self.task_config_hashes,
            self.prompt_template_hashes,
            self.rendered_prompt_ledger_hashes,
            self.output_hashes,
        )
        if any(
            len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for mapping in hash_mappings
            for value in mapping.values()
        ):
            raise ValueError("manifest content hashes must be SHA-256 hex")
        if any(repetitions <= 0 for repetitions in self.path_repetitions.values()):
            raise ValueError("path repetitions must be positive")
        return self

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

    def manifest_id(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class SpecificationCurveManifest(StrictModel):
    source_run_manifest_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    analysis_manifest_ids: dict[SummEvalPolarity, str]
    output_locations: dict[SummEvalPolarity, str]
    output_hashes: dict[SummEvalPolarity, str]

    @model_validator(mode="after")
    def validate_polarity_arms(self) -> SpecificationCurveManifest:
        required = {
            SummEvalPolarity.UPSTREAM_BEHAVIOR,
            SummEvalPolarity.SEMANTIC_ALIGNED,
        }
        for field_name in (
            "analysis_manifest_ids",
            "output_locations",
            "output_hashes",
        ):
            values = getattr(self, field_name)
            if set(values) != required:
                raise ValueError(
                    f"{field_name} must contain both SummEval polarity arms"
                )
        if len(set(self.analysis_manifest_ids.values())) != 2:
            raise ValueError("SummEval polarity arms need distinct manifest IDs")
        if len(set(self.output_locations.values())) != 2:
            raise ValueError(
                "SummEval polarity arms need distinct output locations"
            )
        if any(not location for location in self.output_locations.values()):
            raise ValueError("specification-curve locations cannot be blank")
        hash_mappings = (
            self.analysis_manifest_ids,
            self.output_hashes,
        )
        if any(
            len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for mapping in hash_mappings
            for value in mapping.values()
        ):
            raise ValueError(
                "specification-curve identities must be SHA-256 hex"
            )
        return self
