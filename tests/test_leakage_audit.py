import json

from pprs.data.schema import DatasetRecord, TaskId
from pprs.leakage_audit import (
    audit_key,
    build_auditor_prompt,
    parse_audit_payload,
)
from pprs.prompts import TaskFraming


def test_auditor_prompt_separates_static_and_source() -> None:
    framing = TaskFraming(
        criterion="Assess the relationship under the rubric.",
        item_fields=("context", "statement"),
        forbidden_labels=("entailment", "neutral", "contradiction"),
        forbidden_option_markers=("A.", "B.", "C."),
    )
    record = DatasetRecord(
        task=TaskId.CHAOSNLI_SNLI,
        item_id="fixture",
        source_dataset="ChaosNLI",
        source_revision="37b8d7863430ec3433d6a73da08408b064643b8b",
        source_object_id="aea16e8f1e868493da3913e3d84c0ba0373bab33",
        source_split="snli",
        source_original_id="fixture",
        sampling_seed=42,
        inputs={
            "context": "The word entailment is source content.",
            "statement": "A statement.",
        },
        human_label_counts={"A": 50, "B": 30, "C": 20},
        human_label_distribution={"A": 0.5, "B": 0.3, "C": 0.2},
        ratings_per_item=100,
        license_identifier="CC-BY-NC-4.0",
        license_source="https://github.com/easonnie/ChaosNLI/blob/f358e234ea2797d9298f7b0213bf1308b6d7756b/LICENSE",
        data_card_source="https://github.com/easonnie/ChaosNLI/blob/f358e234ea2797d9298f7b0213bf1308b6d7756b/README.md",
        data_card_revision="f358e234ea2797d9298f7b0213bf1308b6d7756b",
        data_card_blob="967b5a2becf268a18a7d1615ea11bfb5e8423352",
    )
    prompt = build_auditor_prompt(
        framing,
        record,
        "premise-disclosure-inventory-v2",
    )
    assert "STATIC PROMPT" in prompt
    assert "SOURCE ITEM" in prompt
    assert "do not blame the static prompt" in " ".join(
        prompt.lower().split()
    )


def test_audit_payload_is_strict_json() -> None:
    parsed = parse_audit_payload(
        json.dumps(
            {
                "leakage": False,
                "categories": [],
                "rationale": "No option terms in static framing.",
            }
        )
    )
    assert not parsed.leakage


def test_audit_key_changes_with_seed() -> None:
    assert audit_key("prompt", "model", 1) != audit_key(
        "prompt", "model", 2
    )


def test_audit_key_changes_with_endpoint() -> None:
    assert audit_key(
        "prompt",
        "model",
        1,
        "http://127.0.0.1:8313/v1",
    ) != audit_key(
        "prompt",
        "model",
        1,
        "http://127.0.0.1:8787/v1",
    )
