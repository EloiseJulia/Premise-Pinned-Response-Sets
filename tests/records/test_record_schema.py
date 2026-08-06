import pytest
from pydantic import ValidationError

from pprs.records.schema import ParseStatus, RawResult, raw_result_arrow_schema
from pprs.records.schema import ParsedPremise, PremiseType


def test_failure_records_require_null_parsed_fields(raw_result: RawResult) -> None:
    payload = raw_result.model_dump()
    payload["parse_status"] = ParseStatus.TIMEOUT

    with pytest.raises(ValidationError, match="parsed field null"):
        RawResult.model_validate(payload)


def test_arrow_schema_contains_every_raw_result_field() -> None:
    assert set(raw_result_arrow_schema().names) == set(RawResult.model_fields)


def test_ok_forced_choice_requires_parsed_choice(
    raw_result: RawResult,
) -> None:
    payload = raw_result.model_dump()
    payload["parsed_choice_hard"] = None

    with pytest.raises(ValidationError, match="need a hard choice"):
        RawResult.model_validate(payload)


def test_invalid_hard_choice_cannot_be_ok(raw_result: RawResult) -> None:
    payload = raw_result.model_dump()
    payload["parsed_choice_hard"] = "Z"

    with pytest.raises(ValidationError, match="not valid"):
        RawResult.model_validate(payload)


def test_choice_set_cannot_contain_duplicates(
    raw_result: RawResult,
) -> None:
    payload = raw_result.model_dump()
    payload["path"] = "multi_label"
    payload["parsed_choice_hard"] = None
    payload["parsed_choice_set"] = ("A", "A")

    with pytest.raises(ValidationError, match="duplicates"):
        RawResult.model_validate(payload)


def test_premise_scoring_requires_complete_coordinates(
    raw_result: RawResult,
) -> None:
    payload = raw_result.model_dump()
    payload["path"] = "premise_pinned"

    with pytest.raises(ValidationError, match="complete coordinates"):
        RawResult.model_validate(payload)


def test_premise_disclosure_requires_round(
    raw_result: RawResult,
) -> None:
    payload = raw_result.model_dump()
    payload["path"] = "premise_pinned"
    payload["parsed_choice_hard"] = None
    payload["parsed_premises"] = (
        ParsedPremise(
            premise_id="coverage",
            premise_type=PremiseType.VAGUENESS,
            statement="How much source coverage is required?",
            candidate_values=("strict", "lenient"),
        ),
    )

    with pytest.raises(ValidationError, match="premise round"):
        RawResult.model_validate(payload)


def test_premise_candidate_values_must_be_distinct() -> None:
    with pytest.raises(ValidationError, match="distinct"):
        ParsedPremise(
            premise_id="coverage",
            premise_type=PremiseType.VAGUENESS,
            statement="How much source coverage is required?",
            candidate_values=("strict", "strict"),
        )


@pytest.mark.parametrize("parse_status", ["ok", "timeout"])
def test_non_premise_paths_reject_premise_coordinates(
    raw_result: RawResult,
    parse_status: str,
) -> None:
    payload = raw_result.model_dump()
    payload["premise_id"] = "coverage"
    payload["premise_type"] = "vagueness"
    payload["premise_value"] = "strict"
    payload["premise_round"] = 0
    payload["parse_status"] = parse_status
    if parse_status != "ok":
        payload["parsed_choice_hard"] = None

    with pytest.raises(ValidationError, match="non-premise paths"):
        RawResult.model_validate(payload)


def test_premise_disclosure_cannot_be_empty(
    raw_result: RawResult,
) -> None:
    payload = raw_result.model_dump()
    payload["path"] = "premise_pinned"
    payload["parsed_choice_hard"] = None
    payload["parsed_premises"] = ()
    payload["premise_round"] = 0

    with pytest.raises(ValidationError, match="exactly one stage payload"):
        RawResult.model_validate(payload)
