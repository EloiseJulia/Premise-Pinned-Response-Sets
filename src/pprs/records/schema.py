from __future__ import annotations

from datetime import datetime
from enum import StrEnum

import pyarrow as pa
from pydantic import BaseModel, ConfigDict, Field, model_validator

from pprs.data.schema import TaskId


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ElicitationPath(StrEnum):
    FORCED_CHOICE = "forced_choice"
    MULTI_LABEL = "multi_label"
    PREMISE_PINNED = "premise_pinned"
    PLACEBO = "placebo"


class PremiseType(StrEnum):
    AMBIGUITY = "ambiguity"
    VAGUENESS = "vagueness"
    DISAGREEMENT = "disagreement"


class ParseStatus(StrEnum):
    OK = "ok"
    MALFORMED_JSON = "malformed_json"
    MISSING_FIELD = "missing_field"
    REFUSED = "refused"
    TIMEOUT = "timeout"
    PROVIDER_ERROR = "provider_error"


class ParsedPremise(StrictModel):
    premise_id: str = Field(min_length=1)
    premise_type: PremiseType
    statement: str = Field(min_length=1)
    candidate_values: tuple[str, ...] = Field(min_length=2, max_length=3)

    @model_validator(mode="after")
    def validate_candidate_values(self) -> ParsedPremise:
        if not self.premise_id.strip() or not self.statement.strip():
            raise ValueError("premise identifiers and statements cannot be blank")
        if any(not value.strip() for value in self.candidate_values):
            raise ValueError("premise candidate values cannot be blank")
        if len(set(self.candidate_values)) != len(self.candidate_values):
            raise ValueError("premise candidate values must be distinct")
        return self


class RawResult(StrictModel):
    cache_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    run_tag: str = Field(min_length=1)
    git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    prereg_tag: str | None

    task: TaskId
    item_id: str = Field(min_length=1)
    judge_id: str = Field(min_length=1)
    path: ElicitationPath
    sample_id: int = Field(ge=0)

    premise_id: str | None
    premise_type: PremiseType | None
    premise_value: str | None
    premise_round: int | None = Field(default=None, ge=0)

    model_snapshot: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    temperature: float = Field(ge=0)
    top_p: float = Field(gt=0, le=1)
    seed: int
    prompt_template_id: str = Field(min_length=1)
    prompt_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    option_permutation_seed: int

    raw_text: str
    parsed_choice_hard: str | None
    parsed_choice_set: tuple[str, ...] | None
    parsed_premises: tuple[ParsedPremise, ...] | None

    parse_status: ParseStatus
    provider_error: str | None
    http_status: int | None
    retry_count: int = Field(ge=0)

    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    wall_clock_ms: int = Field(ge=0)
    ts_utc: datetime

    @model_validator(mode="after")
    def validate_failure_nullability(self) -> RawResult:
        if self.path is not ElicitationPath.PREMISE_PINNED and any(
            value is not None
            for value in (
                self.premise_id,
                self.premise_type,
                self.premise_value,
                self.premise_round,
            )
        ):
            raise ValueError(
                "non-premise paths cannot carry premise coordinates"
            )

        if self.parse_status is not ParseStatus.OK:
            parsed_values = (
                self.parsed_choice_hard,
                self.parsed_choice_set,
                self.parsed_premises,
            )
            if any(value is not None for value in parsed_values):
                raise ValueError(
                    "non-ok records must keep every parsed field null"
                )
            return self

        if self.path in {
            ElicitationPath.FORCED_CHOICE,
            ElicitationPath.PLACEBO,
        }:
            if self.parsed_choice_hard is None:
                raise ValueError("ok forced-choice records need a hard choice")
            if (
                self.parsed_choice_set is not None
                or self.parsed_premises is not None
            ):
                raise ValueError(
                    "ok forced-choice records cannot carry other parsed payloads"
                )
        elif self.path is ElicitationPath.MULTI_LABEL:
            if not self.parsed_choice_set:
                raise ValueError("ok multi-label records need a nonempty set")
            if (
                self.parsed_choice_hard is not None
                or self.parsed_premises is not None
            ):
                raise ValueError(
                    "ok multi-label records cannot carry other parsed payloads"
                )
        elif self.path is ElicitationPath.PREMISE_PINNED:
            payloads = (
                self.parsed_choice_hard is not None,
                bool(self.parsed_premises),
            )
            if sum(payloads) != 1 or self.parsed_choice_set is not None:
                raise ValueError(
                    "ok premise-pinned records need exactly one stage payload"
                )
            if self.parsed_choice_hard is not None:
                required_coordinates = (
                    self.premise_id,
                    self.premise_type,
                    self.premise_value,
                    self.premise_round,
                )
                if any(value is None for value in required_coordinates):
                    raise ValueError(
                        "premise-pinned scoring needs complete coordinates"
                    )
                if (
                    not self.premise_id.strip()
                    or not self.premise_value.strip()
                ):
                    raise ValueError(
                        "premise-pinned coordinates cannot be blank"
                    )
            else:
                if self.premise_round is None:
                    raise ValueError(
                        "premise disclosure needs a premise round"
                    )
                if any(
                    value is not None
                    for value in (
                        self.premise_id,
                        self.premise_type,
                        self.premise_value,
                    )
                ):
                    raise ValueError(
                        "premise disclosure cannot carry scoring coordinates"
                    )
        valid_tokens = {
            TaskId.CHAOSNLI_SNLI: ("A", "B", "C"),
            TaskId.CHAOSNLI_MNLI: ("A", "B", "C"),
            TaskId.SUMMEVAL_RELEVANCE: ("A", "B"),
        }[self.task]
        if (
            self.parsed_choice_hard is not None
            and self.parsed_choice_hard not in valid_tokens
        ):
            raise ValueError("parsed hard choice is not valid for the task")
        if self.parsed_choice_set is not None:
            if any(token not in valid_tokens for token in self.parsed_choice_set):
                raise ValueError("parsed choice set contains an invalid token")
            if len(set(self.parsed_choice_set)) != len(self.parsed_choice_set):
                raise ValueError("parsed choice set cannot contain duplicates")
            canonical = tuple(
                token
                for token in valid_tokens
                if token in self.parsed_choice_set
            )
            if self.parsed_choice_set != canonical:
                raise ValueError("parsed choice set must use canonical order")
        return self


def raw_result_arrow_schema() -> pa.Schema:
    premise_struct = pa.struct(
        [
            pa.field("premise_id", pa.string(), nullable=False),
            pa.field("premise_type", pa.string(), nullable=False),
            pa.field("statement", pa.string(), nullable=False),
            pa.field(
                "candidate_values",
                pa.list_(pa.string()),
                nullable=False,
            ),
        ]
    )
    return pa.schema(
        [
            pa.field("cache_key", pa.string(), nullable=False),
            pa.field("run_tag", pa.string(), nullable=False),
            pa.field("git_sha", pa.string(), nullable=False),
            pa.field("prereg_tag", pa.string()),
            pa.field("task", pa.string(), nullable=False),
            pa.field("item_id", pa.string(), nullable=False),
            pa.field("judge_id", pa.string(), nullable=False),
            pa.field("path", pa.string(), nullable=False),
            pa.field("sample_id", pa.int64(), nullable=False),
            pa.field("premise_id", pa.string()),
            pa.field("premise_type", pa.string()),
            pa.field("premise_value", pa.string()),
            pa.field("premise_round", pa.int64()),
            pa.field("model_snapshot", pa.string(), nullable=False),
            pa.field("provider", pa.string(), nullable=False),
            pa.field("temperature", pa.float64(), nullable=False),
            pa.field("top_p", pa.float64(), nullable=False),
            pa.field("seed", pa.int64(), nullable=False),
            pa.field("prompt_template_id", pa.string(), nullable=False),
            pa.field("prompt_hash", pa.string(), nullable=False),
            pa.field("option_permutation_seed", pa.int64(), nullable=False),
            pa.field("raw_text", pa.string(), nullable=False),
            pa.field("parsed_choice_hard", pa.string()),
            pa.field("parsed_choice_set", pa.list_(pa.string())),
            pa.field("parsed_premises", pa.list_(premise_struct)),
            pa.field("parse_status", pa.string(), nullable=False),
            pa.field("provider_error", pa.string()),
            pa.field("http_status", pa.int64()),
            pa.field("retry_count", pa.int64(), nullable=False),
            pa.field("prompt_tokens", pa.int64()),
            pa.field("completion_tokens", pa.int64()),
            pa.field("wall_clock_ms", pa.int64(), nullable=False),
            pa.field(
                "ts_utc",
                pa.timestamp("us", tz="UTC"),
                nullable=False,
            ),
        ]
    )
