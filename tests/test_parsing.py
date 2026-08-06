import pytest

from pprs.parsing import parse_response
from pprs.providers.base import ResponseFormat
from pprs.records.schema import ParseStatus


def test_forced_choice_parses() -> None:
    result = parse_response(
        '{"choice":"A"}',
        ResponseFormat.FORCED_CHOICE_JSON,
        ("A", "B", "C"),
    )
    assert result.status is ParseStatus.OK
    assert result.parsed_choice_hard == "A"


def test_response_set_canonicalizes_unique_tokens() -> None:
    duplicate = parse_response(
        '{"choices":["A","A"]}',
        ResponseFormat.RESPONSE_SET_JSON,
        ("A", "B", "C"),
    )
    reordered = parse_response(
        '{"choices":["B","A"]}',
        ResponseFormat.RESPONSE_SET_JSON,
        ("A", "B", "C"),
    )
    unknown = parse_response(
        '{"choices":["Z"]}',
        ResponseFormat.RESPONSE_SET_JSON,
        ("A", "B", "C"),
    )
    assert duplicate.status is ParseStatus.MALFORMED_JSON
    assert reordered.status is ParseStatus.OK
    assert reordered.parsed_choice_set == ("A", "B")
    assert unknown.status is ParseStatus.MALFORMED_JSON


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("not-json", ParseStatus.MALFORMED_JSON),
        ("{}", ParseStatus.MISSING_FIELD),
        ('{"choice":"A","extra":1}', ParseStatus.MALFORMED_JSON),
    ],
)
def test_parser_failures_are_explicit(
    raw_text: str,
    expected: ParseStatus,
) -> None:
    result = parse_response(
        raw_text,
        ResponseFormat.FORCED_CHOICE_JSON,
        ("A", "B", "C"),
    )
    assert result.status is expected
    assert result.parsed_choice_hard is None
    assert result.parsed_choice_set is None
    assert result.parsed_premises is None


def test_premise_disclosure_parses() -> None:
    result = parse_response(
        """
        {
          "premises": [{
            "premise_id": "coverage",
            "premise_type": "vagueness",
            "statement": "How much coverage is required?",
            "candidate_values": ["strict", "lenient"]
          }]
        }
        """,
        ResponseFormat.PREMISE_DISCLOSURE_JSON,
        ("A", "B", "C"),
    )
    assert result.status is ParseStatus.OK
    assert result.parsed_premises is not None
    assert result.parsed_premises[0].premise_id == "coverage"


def test_unknown_response_format_fails() -> None:
    with pytest.raises(ValueError, match="unknown response format"):
        parse_response(
            '{"premises":[]}',
            "unknown_format",
            ("A", "B"),
        )
