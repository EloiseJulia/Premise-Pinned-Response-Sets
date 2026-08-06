from __future__ import annotations

from enum import StrEnum
import hashlib
import json
from math import isclose

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TaskId(StrEnum):
    CHAOSNLI_SNLI = "chaosnli_snli"
    CHAOSNLI_MNLI = "chaosnli_mnli"
    SUMMEVAL_RELEVANCE = "summeval_relevance"


class OptionToken(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class OptionDefinition(StrictModel):
    token: OptionToken
    label: str = Field(min_length=1)
    source_label: str = Field(min_length=1)


class LicenseEvidence(StrictModel):
    identifier: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_blob: str = Field(pattern=r"^[0-9a-f]{40}$")
    caveat: str | None = None


class DataCardEvidence(StrictModel):
    source_url: str = Field(min_length=1)
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_blob: str = Field(pattern=r"^[0-9a-f]{40}$")


class UpstreamReference(StrictModel):
    repository: str = Field(min_length=1)
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    path: str = Field(min_length=1)
    blob: str = Field(pattern=r"^[0-9a-f]{40}$")


class TaskConfig(StrictModel):
    task_id: TaskId
    source_dataset: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    source_download_uri: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    source_object_id: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_split: str = Field(min_length=1)
    sample_size: int = Field(gt=0)
    sampling_seed: int | None = Field(default=None, ge=0)
    input_fields: tuple[str, ...] = Field(min_length=1)
    options: tuple[OptionDefinition, ...] = Field(min_length=2)
    valid_response_sets: tuple[str, ...] = Field(min_length=3)
    analysis_conventions: dict[str, dict[str, str]] = Field(min_length=1)
    ratings_per_item: int = Field(gt=0)
    license: LicenseEvidence
    data_card: DataCardEvidence
    upstream_reference: UpstreamReference

    @model_validator(mode="after")
    def validate_task_contract(self) -> TaskConfig:
        tokens = tuple(option.token.value for option in self.options)
        if len(tokens) != len(set(tokens)):
            raise ValueError("option tokens must be unique")
        for convention, mapping in self.analysis_conventions.items():
            if not convention or set(mapping) != set(tokens):
                raise ValueError(
                    "analysis conventions must map every option token"
                )
            if any(not source_field for source_field in mapping.values()):
                raise ValueError(
                    "analysis convention source fields cannot be blank"
                )

        nli_tasks = {TaskId.CHAOSNLI_SNLI, TaskId.CHAOSNLI_MNLI}
        if self.task_id in nli_tasks:
            locked_sources = {
                TaskId.CHAOSNLI_SNLI: {
                    "source_uri": "https://huggingface.co/datasets/lguerdan/indeterminacy-datasets/blob/37b8d7863430ec3433d6a73da08408b064643b8b/chaosNLI_v1.0/chaosNLI_snli.jsonl",
                    "source_download_uri": "https://huggingface.co/datasets/lguerdan/indeterminacy-datasets/resolve/37b8d7863430ec3433d6a73da08408b064643b8b/chaosNLI_v1.0/chaosNLI_snli.jsonl",
                    "source_object_id": "aea16e8f1e868493da3913e3d84c0ba0373bab33",
                    "source_split": "snli",
                },
                TaskId.CHAOSNLI_MNLI: {
                    "source_uri": "https://huggingface.co/datasets/lguerdan/indeterminacy-datasets/blob/37b8d7863430ec3433d6a73da08408b064643b8b/chaosNLI_v1.0/chaosNLI_mnli_m.jsonl",
                    "source_download_uri": "https://huggingface.co/datasets/lguerdan/indeterminacy-datasets/resolve/37b8d7863430ec3433d6a73da08408b064643b8b/chaosNLI_v1.0/chaosNLI_mnli_m.jsonl",
                    "source_object_id": "acf6a5a539ee6d1802c3a45e7c2399ab3320e62c",
                    "source_split": "mnli_matched",
                },
            }
            expected_source = locked_sources[self.task_id]
            if self.source_dataset != "ChaosNLI":
                raise ValueError("NLI source dataset must be ChaosNLI")
            if (
                self.source_revision
                != "37b8d7863430ec3433d6a73da08408b064643b8b"
            ):
                raise ValueError("ChaosNLI source revision is locked")
            for field, expected in expected_source.items():
                if getattr(self, field) != expected:
                    raise ValueError(f"locked ChaosNLI {field} does not match")
            if self.license.identifier != "CC-BY-NC-4.0":
                raise ValueError("ChaosNLI license identifier is locked")
            if (
                self.license.source_url
                != "https://github.com/easonnie/ChaosNLI/blob/f358e234ea2797d9298f7b0213bf1308b6d7756b/LICENSE"
            ):
                raise ValueError("ChaosNLI license source is locked")
            if (
                self.license.source_revision
                != "f358e234ea2797d9298f7b0213bf1308b6d7756b"
                or self.license.source_blob
                != "50f2e656c8e006d68fce3c9ddd02d9069072214a"
            ):
                raise ValueError("ChaosNLI license artifact is locked")
            if (
                self.data_card.source_url
                != "https://github.com/easonnie/ChaosNLI/blob/f358e234ea2797d9298f7b0213bf1308b6d7756b/README.md"
                or self.data_card.source_revision
                != "f358e234ea2797d9298f7b0213bf1308b6d7756b"
                or self.data_card.source_blob
                != "967b5a2becf268a18a7d1615ea11bfb5e8423352"
            ):
                raise ValueError("ChaosNLI data-card artifact is locked")
            if (
                self.upstream_reference.repository
                != "https://github.com/lguerdan/indeterminacy"
                or self.upstream_reference.commit
                != "efdb3a2792369e2f98b86dd1d25c2f9c477c115a"
                or self.upstream_reference.path != "config/tasks.py"
                or self.upstream_reference.blob
                != "818b0aedb2281323f8440d8e0ddd8cbe0af50163"
            ):
                raise ValueError("pinned indeterminacy reference does not match")
            expected_options = (
                ("A", "Entailment", "e"),
                ("B", "Neutral", "n"),
                ("C", "Contradiction", "c"),
            )
            actual_options = tuple(
                (option.token.value, option.label, option.source_label)
                for option in self.options
            )
            if actual_options != expected_options:
                raise ValueError(
                    "ChaosNLI option order must be A=Entailment, "
                    "B=Neutral, C=Contradiction"
                )
            if self.sample_size != 150:
                raise ValueError("ChaosNLI task sample size must be 150")
            if self.sampling_seed != 42:
                raise ValueError("ChaosNLI sampling seed must be 42")
            if self.input_fields != ("context", "statement"):
                raise ValueError(
                    "ChaosNLI input fields must be context and statement"
                )
            if self.ratings_per_item != 100:
                raise ValueError("ChaosNLI records must contain 100 ratings")
            if self.valid_response_sets != (
                "A",
                "B",
                "C",
                "AB",
                "AC",
                "BC",
                "ABC",
            ):
                raise ValueError("ChaosNLI response-set token order is locked")
            if self.analysis_conventions != {
                "canonical": {"A": "e", "B": "n", "C": "c"}
            }:
                raise ValueError("ChaosNLI human label mapping is locked")

        if self.task_id is TaskId.SUMMEVAL_RELEVANCE:
            if (
                self.source_dataset != "SummEval"
                or self.source_uri
                != "https://huggingface.co/datasets/lguerdan/indeterminacy-datasets/blob/37b8d7863430ec3433d6a73da08408b064643b8b/SummEval/summ_eval_processed.csv"
                or self.source_download_uri
                != "https://huggingface.co/datasets/lguerdan/indeterminacy-datasets/resolve/37b8d7863430ec3433d6a73da08408b064643b8b/SummEval/summ_eval_processed.csv"
                or self.source_revision
                != "37b8d7863430ec3433d6a73da08408b064643b8b"
                or self.source_object_id
                != "5f3c386bf230cfa0d53fec293cfb56bf7ac76637"
                or self.source_split != "all"
            ):
                raise ValueError("SummEval source artifact is locked")
            expected_options = (
                ("A", "Relevant", "relevant"),
                ("B", "Not Relevant", "not_relevant"),
            )
            actual_options = tuple(
                (option.token.value, option.label, option.source_label)
                for option in self.options
            )
            if actual_options != expected_options:
                raise ValueError(
                    "SummEval options must be A=Relevant, B=Not Relevant"
                )
            if self.input_fields != ("article", "summary"):
                raise ValueError(
                    "SummEval input fields must be article and summary"
                )
            if self.sample_size != 150 or self.ratings_per_item != 8:
                raise ValueError("SummEval sample size and rating count are locked")
            if self.sampling_seed != 42:
                raise ValueError("SummEval sampling seed must be 42")
            if self.valid_response_sets != ("A", "B", "AB"):
                raise ValueError("SummEval response-set token order is locked")
            if self.analysis_conventions != {
                "upstream_behavior": {
                    "A": "relevance_0",
                    "B": "relevance_1",
                },
                "semantic_aligned": {
                    "A": "relevance_1",
                    "B": "relevance_0",
                },
            }:
                raise ValueError(
                    "both SummEval polarity conventions are required"
                )
            if (
                self.license.identifier != "MIT"
                or self.license.source_url
                != "https://github.com/Yale-LILY/SummEval/blob/81b59ad53d63cb6009764240853c91235a44e238/LICENSE"
                or self.license.source_revision
                != "81b59ad53d63cb6009764240853c91235a44e238"
                or self.license.source_blob
                != "fbe02d55ba3e128a8b75d1e2c90bd067e2fa9086"
            ):
                raise ValueError("SummEval license artifact is locked")
            if (
                self.data_card.source_url
                != "https://github.com/Yale-LILY/SummEval/blob/81b59ad53d63cb6009764240853c91235a44e238/README.md"
                or self.data_card.source_revision
                != "81b59ad53d63cb6009764240853c91235a44e238"
                or self.data_card.source_blob
                != "4b54cd7db70990ba8e22a947cf4bd5c9132acd0c"
            ):
                raise ValueError("SummEval data-card artifact is locked")
            if (
                self.upstream_reference.repository
                != "https://github.com/lguerdan/indeterminacy"
                or self.upstream_reference.commit
                != "efdb3a2792369e2f98b86dd1d25c2f9c477c115a"
                or self.upstream_reference.path != "config/tasks.py"
                or self.upstream_reference.blob
                != "818b0aedb2281323f8440d8e0ddd8cbe0af50163"
            ):
                raise ValueError("pinned indeterminacy reference does not match")

        return self


class SampleManifest(StrictModel):
    task: TaskId
    source_revision: str = Field(min_length=1)
    source_object_id: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sampling_seed: int = Field(ge=0)
    sampling_algorithm: str = Field(min_length=1)
    sample_size: int = Field(gt=0)
    ordered_item_ids: tuple[str, ...] = Field(min_length=1)
    record_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parquet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_sample(self) -> SampleManifest:
        if len(self.ordered_item_ids) != self.sample_size:
            raise ValueError("sample manifest ID count must match sample size")
        if len(set(self.ordered_item_ids)) != self.sample_size:
            raise ValueError("sample manifest IDs must be unique")
        return self

    def manifest_id(self) -> str:
        payload = self.model_dump(mode="json")
        return hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()


class DatasetRecord(StrictModel):
    task: TaskId
    item_id: str = Field(min_length=1)
    source_dataset: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    source_object_id: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_split: str = Field(min_length=1)
    source_original_id: str = Field(min_length=1)
    sampling_seed: int = Field(ge=0)
    inputs: dict[str, str]
    human_label_counts: dict[str, int]
    human_label_distribution: dict[str, float]
    ratings_per_item: int = Field(gt=0)
    license_identifier: str = Field(min_length=1)
    license_source: str = Field(min_length=1)
    data_card_source: str = Field(min_length=1)
    data_card_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    data_card_blob: str = Field(pattern=r"^[0-9a-f]{40}$")

    @model_validator(mode="after")
    def validate_human_labels(self) -> DatasetRecord:
        if self.task in {TaskId.CHAOSNLI_SNLI, TaskId.CHAOSNLI_MNLI}:
            expected_split = {
                TaskId.CHAOSNLI_SNLI: "snli",
                TaskId.CHAOSNLI_MNLI: "mnli_matched",
            }[self.task]
            expected_object_id = {
                TaskId.CHAOSNLI_SNLI: (
                    "aea16e8f1e868493da3913e3d84c0ba0373bab33"
                ),
                TaskId.CHAOSNLI_MNLI: (
                    "acf6a5a539ee6d1802c3a45e7c2399ab3320e62c"
                ),
            }[self.task]
            if self.source_dataset != "ChaosNLI":
                raise ValueError("NLI source dataset must be ChaosNLI")
            if (
                self.source_revision
                != "37b8d7863430ec3433d6a73da08408b064643b8b"
            ):
                raise ValueError("ChaosNLI source revision is locked")
            if self.source_split != expected_split:
                raise ValueError("ChaosNLI source split is locked")
            if self.source_object_id != expected_object_id:
                raise ValueError("ChaosNLI source object is locked")
            if self.item_id != self.source_original_id:
                raise ValueError("ChaosNLI item ID must preserve the source UID")
            if set(self.inputs) != {"context", "statement"} or any(
                not value.strip() for value in self.inputs.values()
            ):
                raise ValueError(
                    "ChaosNLI records require nonempty context and statement"
                )
            if self.license_identifier != "CC-BY-NC-4.0":
                raise ValueError("ChaosNLI license identifier is locked")
            if (
                self.license_source
                != "https://github.com/easonnie/ChaosNLI/blob/f358e234ea2797d9298f7b0213bf1308b6d7756b/LICENSE"
            ):
                raise ValueError("ChaosNLI license source is locked")
            if (
                self.data_card_source
                != "https://github.com/easonnie/ChaosNLI/blob/f358e234ea2797d9298f7b0213bf1308b6d7756b/README.md"
                or self.data_card_revision
                != "f358e234ea2797d9298f7b0213bf1308b6d7756b"
                or self.data_card_blob
                != "967b5a2becf268a18a7d1615ea11bfb5e8423352"
            ):
                raise ValueError("ChaosNLI data-card artifact is locked")
            expected_keys = {"A", "B", "C"}
            if set(self.human_label_counts) != expected_keys:
                raise ValueError("ChaosNLI label counts must use A, B, and C")
            if set(self.human_label_distribution) != expected_keys:
                raise ValueError(
                    "ChaosNLI label distribution must use A, B, and C"
                )
            if self.ratings_per_item != 100:
                raise ValueError("ChaosNLI records must contain 100 ratings")
            if any(count < 0 for count in self.human_label_counts.values()):
                raise ValueError("human label counts cannot be negative")
            if any(
                probability < 0 or probability > 1
                for probability in self.human_label_distribution.values()
            ):
                raise ValueError(
                    "human label probabilities must be between zero and one"
                )
            if sum(self.human_label_counts.values()) != self.ratings_per_item:
                raise ValueError("human label counts must sum to 100")
            for token, count in self.human_label_counts.items():
                expected = count / self.ratings_per_item
                if not isclose(
                    self.human_label_distribution[token],
                    expected,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ):
                    raise ValueError(
                        "human label distribution must be derived from counts"
                    )
            if self.sampling_seed != 42:
                raise ValueError("ChaosNLI sampling seed must be 42")

        if self.task is TaskId.SUMMEVAL_RELEVANCE:
            if (
                self.source_dataset != "SummEval"
                or self.source_revision
                != "37b8d7863430ec3433d6a73da08408b064643b8b"
                or self.source_object_id
                != "5f3c386bf230cfa0d53fec293cfb56bf7ac76637"
                or self.source_split != "all"
            ):
                raise ValueError("SummEval record provenance is locked")
            if self.sampling_seed != 42:
                raise ValueError("SummEval sampling seed must be 42")
            if set(self.inputs) != {"article", "summary"} or any(
                not value.strip() for value in self.inputs.values()
            ):
                raise ValueError(
                    "SummEval records require nonempty article and summary"
                )
            expected_keys = {"relevance_0", "relevance_1"}
            if set(self.human_label_counts) != expected_keys:
                raise ValueError(
                    "SummEval records retain relevance_0 and relevance_1"
                )
            if set(self.human_label_distribution) != expected_keys:
                raise ValueError(
                    "SummEval distributions retain source column names"
                )
            if self.ratings_per_item != 8:
                raise ValueError("SummEval records must contain 8 ratings")
            if any(count < 0 for count in self.human_label_counts.values()):
                raise ValueError("human label counts cannot be negative")
            if sum(self.human_label_counts.values()) != 8:
                raise ValueError("SummEval label counts must sum to 8")
            for key, count in self.human_label_counts.items():
                if not isclose(
                    self.human_label_distribution[key],
                    count / 8,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ):
                    raise ValueError(
                        "SummEval distribution must be derived from counts"
                    )

        return self
