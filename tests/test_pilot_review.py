from pprs.pilot_review import preliminarily_classify
from pprs.records.schema import ParseStatus, ParsedPremise, PremiseType


def test_review_classifies_substantive_premise(raw_result) -> None:
    record = raw_result.model_copy(
        update={
            "path": "premise_pinned",
            "premise_round": 0,
            "parsed_choice_hard": None,
            "parsed_premises": (
                ParsedPremise(
                    premise_id="coverage_standard",
                    premise_type=PremiseType.VAGUENESS,
                    statement="How much source coverage is required?",
                    candidate_values=("strict", "lenient"),
                ),
            ),
        }
    )
    category, _flags = preliminarily_classify(record)
    assert category == "pinable_candidate"


def test_review_preserves_failure_category(raw_result) -> None:
    record = raw_result.model_copy(
        update={
            "parse_status": ParseStatus.TIMEOUT,
            "parsed_choice_hard": None,
        }
    )
    category, flags = preliminarily_classify(record)
    assert category == "timeout"
    assert flags == ()
