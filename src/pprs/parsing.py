from __future__ import annotations

import json
from json import JSONDecodeError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from pprs.providers.base import ResponseFormat
from pprs.records.schema import ParseStatus, ParsedPremise


class StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ForcedChoicePayload(StrictPayload):
    choice: str = Field(min_length=1)


class ResponseSetPayload(StrictPayload):
    choices: tuple[str, ...] = Field(min_length=1)


class PremiseDisclosurePayload(StrictPayload):
    premises: tuple[ParsedPremise, ...] = Field(
        min_length=1,
        max_length=4,
    )

    @model_validator(mode="after")
    def validate_unique_premise_ids(self) -> "PremiseDisclosurePayload":
        premise_ids = tuple(
            premise.premise_id for premise in self.premises
        )
        if len(set(premise_ids)) != len(premise_ids):
            raise ValueError("premise IDs must be unique within a disclosure")
        return self


class ParseResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ParseStatus
    parsed_choice_hard: str | None = None
    parsed_choice_set: tuple[str, ...] | None = None
    parsed_premises: tuple[ParsedPremise, ...] | None = None


def _validation_status(exc: ValidationError) -> ParseStatus:
    if any(error["type"] == "missing" for error in exc.errors()):
        return ParseStatus.MISSING_FIELD
    return ParseStatus.MALFORMED_JSON


def parse_response(
    raw_text: str,
    response_format: ResponseFormat,
    valid_tokens: tuple[str, ...],
) -> ParseResult:
    if not isinstance(response_format, ResponseFormat):
        raise ValueError(f"unknown response format: {response_format}")
    try:
        payload = json.loads(raw_text)
    except JSONDecodeError:
        return ParseResult(status=ParseStatus.MALFORMED_JSON)

    try:
        if response_format is ResponseFormat.FORCED_CHOICE_JSON:
            parsed = ForcedChoicePayload.model_validate(payload)
            if parsed.choice not in valid_tokens:
                return ParseResult(status=ParseStatus.MALFORMED_JSON)
            return ParseResult(
                status=ParseStatus.OK,
                parsed_choice_hard=parsed.choice,
            )

        if response_format is ResponseFormat.RESPONSE_SET_JSON:
            parsed = ResponseSetPayload.model_validate(payload)
            if any(choice not in valid_tokens for choice in parsed.choices):
                return ParseResult(status=ParseStatus.MALFORMED_JSON)
            if len(set(parsed.choices)) != len(parsed.choices):
                return ParseResult(status=ParseStatus.MALFORMED_JSON)
            canonical = tuple(
                token for token in valid_tokens if token in parsed.choices
            )
            return ParseResult(
                status=ParseStatus.OK,
                parsed_choice_set=canonical,
            )

        if response_format is ResponseFormat.PREMISE_DISCLOSURE_JSON:
            parsed = PremiseDisclosurePayload.model_validate(payload)
            return ParseResult(
                status=ParseStatus.OK,
                parsed_premises=parsed.premises,
            )
        raise ValueError(f"unknown response format: {response_format}")
    except ValidationError as exc:
        return ParseResult(status=_validation_status(exc))
