from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from pprs.data.schema import TaskId
from pprs.providers.base import ResponseFormat


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TaskFraming(StrictModel):
    criterion: str = Field(min_length=1)
    item_fields: tuple[str, ...] = Field(min_length=1)
    forbidden_labels: tuple[str, ...]
    forbidden_option_markers: tuple[str, ...]


class PromptOption(StrictModel):
    token: str = Field(pattern=r"^[A-Z]$")
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)


class LeakageReport(StrictModel):
    introduced_terms: tuple[str, ...]
    source_content_terms: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.introduced_terms


class RenderedPrompt(StrictModel):
    template_id: str = Field(min_length=1)
    response_format: ResponseFormat
    text: str = Field(min_length=1)
    prompt_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_length: int = Field(gt=0)
    matched_prompt_length: int | None = Field(default=None, gt=0)
    length_delta: int | None = None
    option_permutation_seed: int | None
    leakage_report: LeakageReport | None = None


@dataclass(frozen=True)
class DisclosureCandidate:
    template_id: str
    opening: str


_DISCLOSURE_CANDIDATES = (
    DisclosureCandidate(
        "premise-disclosure-inventory-v1",
        "Identify the unstated scoring premises that must be fixed before this "
        "item can be rated under the rubric.",
    ),
    DisclosureCandidate(
        "premise-disclosure-counterfactual-v1",
        "List unstated scoring premises whose alternative resolutions could "
        "change the rating assigned under the rubric.",
    ),
    DisclosureCandidate(
        "premise-disclosure-rubric-v1",
        "Surface the unresolved interpretations of the rubric that materially "
        "affect how this item should be rated.",
    ),
    DisclosureCandidate(
        "premise-disclosure-boundary-v1",
        "Describe the unstated scoring decisions that determine where this item "
        "falls under the rubric.",
    ),
    DisclosureCandidate(
        "premise-disclosure-minimal-v1",
        "State the smallest set of unresolved scoring premises needed to rate "
        "this item consistently.",
    ),
)

_DISCLOSURE_BY_ID = {
    candidate.template_id: candidate
    for candidate in _DISCLOSURE_CANDIDATES
}
_DISCLOSURE_BY_ID["premise-disclosure-inventory-v2"] = DisclosureCandidate(
    "premise-disclosure-inventory-v2",
    "Identify the unstated scoring premises that must be fixed before this "
    "item can be rated under the rubric. The first response character must be "
    "{ and the last must be }. Do not use Markdown or code fences.",
)

_DISCLOSURE_SHARED = """
Return only material scoring premises. Do not rate the item. Do not
predict a label. Exclude presentation format, output encoding, programming
language, tooling, typography, and interface metadata.

For each premise:
- use a short stable premise_id;
- classify premise_type as ambiguity, vagueness, or disagreement;
- state the unresolved scoring question;
- provide 2 or 3 concrete candidate_values.

Return only JSON in this shape:
{"premises":[{"premise_id":"...","premise_type":"vagueness","statement":"...","candidate_values":["...","..."]}]}
""".strip()

_PIN_CLAUSE = """
For this rating only, use this resolution of one otherwise unspecified scoring
premise:
Premise: {premise_statement}
Resolution: {premise_value}
""".strip()

_PLACEBO_PREMISE = "interface accent color"
_PLACEBO_VALUE = "blue"
_LINE_SEPARATORS = frozenset(
    "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"
)


def disclosure_template_ids() -> tuple[str, ...]:
    return tuple(candidate.template_id for candidate in _DISCLOSURE_CANDIDATES)


def repaired_disclosure_template_id() -> str:
    return "premise-disclosure-inventory-v2"


def load_task_framings(path: Path) -> dict[TaskId, TaskFraming]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        TaskId(task_id): TaskFraming.model_validate(framing)
        for task_id, framing in payload.items()
    }


def permute_options(
    options: tuple[PromptOption, ...],
    seed: int,
) -> tuple[PromptOption, ...]:
    if len({option.token for option in options}) != len(options):
        raise ValueError("option tokens must be unique")
    shuffled = list(options)
    random.Random(seed).shuffle(shuffled)
    return tuple(shuffled)


def _item_text(framing: TaskFraming, item: dict[str, str]) -> str:
    if set(item) != set(framing.item_fields):
        raise ValueError("item fields must exactly match the task framing")
    if any(not item[field].strip() for field in framing.item_fields):
        raise ValueError("item fields cannot be blank")
    return "\n".join(
        f"{field.replace('_', ' ').title()}: {item[field]}"
        for field in framing.item_fields
    )


def _hash_prompt(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _option_text(options: tuple[PromptOption, ...]) -> str:
    return "\n".join(
        f"{option.token}. {option.label} - {option.description}"
        for option in options
    )


def _find_terms(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    found = []
    lowered = text.lower()
    for term in terms:
        if re.search(rf"\b{re.escape(term.lower())}\b", lowered):
            found.append(term)
    return tuple(found)


def audit_disclosure_leakage(
    framing: TaskFraming,
    static_text: str,
    item_text: str,
) -> LeakageReport:
    introduced = list(_find_terms(static_text, framing.forbidden_labels))
    introduced.extend(_find_option_markers(static_text, framing))
    source_terms = list(_find_terms(item_text, framing.forbidden_labels))
    source_terms.extend(_find_option_markers(item_text, framing))
    return LeakageReport(
        introduced_terms=tuple(dict.fromkeys(introduced)),
        source_content_terms=tuple(dict.fromkeys(source_terms)),
    )


def _find_option_markers(
    text: str,
    framing: TaskFraming,
) -> tuple[str, ...]:
    found = []
    for configured in framing.forbidden_option_markers:
        token = configured[0]
        patterns = (
            rf"\boption\s+{re.escape(token)}\b",
            rf"(?<!\w){re.escape(token)}\s*[\.\):]",
            rf"""["'\[]{re.escape(token)}["'\]]""",
        )
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            found.append(configured)
    return tuple(found)


def render_disclosure_prompt(
    framing: TaskFraming,
    item: dict[str, str],
    template_id: str,
    *,
    max_premises: int = 4,
) -> RenderedPrompt:
    if max_premises <= 0:
        raise ValueError("max_premises must be positive")
    try:
        candidate = _DISCLOSURE_BY_ID[template_id]
    except KeyError as exc:
        raise ValueError(f"unknown disclosure template: {template_id}") from exc

    item_block = _item_text(framing, item)
    static_text = (
        "Evaluation criterion:\n"
        f"{framing.criterion}\n\n"
        f"{candidate.opening}\n"
        f"List at most {max_premises} premises, most consequential first.\n\n"
        f"{_DISCLOSURE_SHARED}"
    )
    leakage = audit_disclosure_leakage(
        framing,
        static_text,
        item_block,
    )
    if not leakage.passed:
        raise ValueError(
            f"disclosure framing leaks option terms: {leakage.introduced_terms}"
        )
    text = f"{static_text}\n\nItem:\n{item_block}"
    return RenderedPrompt(
        template_id=template_id,
        response_format=ResponseFormat.PREMISE_DISCLOSURE_JSON,
        text=text,
        prompt_hash=_hash_prompt(text),
        prompt_length=len(text),
        option_permutation_seed=None,
        leakage_report=leakage,
    )


def _render_rating_prompt(
    framing: TaskFraming,
    item: dict[str, str],
    options: tuple[PromptOption, ...],
    seed: int,
    *,
    template_id: str,
    instruction: str,
    response_example: str,
    prefix: str | None = None,
) -> RenderedPrompt:
    permuted = permute_options(options, seed)
    blocks = []
    if prefix is not None:
        blocks.append(prefix)
    blocks.extend(
        [
            f"Evaluation criterion:\n{framing.criterion}",
            f"Item:\n{_item_text(framing, item)}",
            f"{instruction}\n{_option_text(permuted)}",
            (
                f"Return only JSON: {response_example}\n"
                "The first response character must be { and the last must be }."
                " Do not use Markdown or code fences."
            ),
        ]
    )
    text = "\n\n".join(blocks)
    response_format = (
        ResponseFormat.RESPONSE_SET_JSON
        if "choices" in response_example
        else ResponseFormat.FORCED_CHOICE_JSON
    )
    return RenderedPrompt(
        template_id=template_id,
        response_format=response_format,
        text=text,
        prompt_hash=_hash_prompt(text),
        prompt_length=len(text),
        option_permutation_seed=seed,
    )


def render_forced_choice_prompt(
    framing: TaskFraming,
    item: dict[str, str],
    options: tuple[PromptOption, ...],
    seed: int,
) -> RenderedPrompt:
    return _render_rating_prompt(
        framing,
        item,
        options,
        seed,
        template_id="forced-choice-v2",
        instruction="Select exactly one option that best applies:",
        response_example='{"choice":"<token>"}',
    )


def render_response_set_prompt(
    framing: TaskFraming,
    item: dict[str, str],
    options: tuple[PromptOption, ...],
    seed: int,
) -> RenderedPrompt:
    return _render_rating_prompt(
        framing,
        item,
        options,
        seed,
        template_id="response-set-v2",
        instruction=(
            "Select every option that could reasonably apply under plausible "
            "interpretations of the criterion:"
        ),
        response_example='{"choices":["<token>"]}',
    )


def render_pinned_prompt(
    framing: TaskFraming,
    item: dict[str, str],
    options: tuple[PromptOption, ...],
    seed: int,
    *,
    premise_statement: str,
    premise_value: str,
) -> RenderedPrompt:
    _validate_pin_component(premise_statement, "premise statement")
    _validate_pin_component(premise_value, "premise value")
    prefix = _PIN_CLAUSE.format(
        premise_statement=premise_statement,
        premise_value=premise_value,
    )
    return _render_rating_prompt(
        framing,
        item,
        options,
        seed,
        template_id="premise-pinned-v2",
        instruction="Select exactly one option that best applies:",
        response_example='{"choice":"<token>"}',
        prefix=prefix,
    )


def render_full_grid_prompt(
    framing: TaskFraming,
    item: dict[str, str],
    options: tuple[PromptOption, ...],
    seed: int,
    *,
    assignments: tuple[tuple[str, str], ...],
) -> RenderedPrompt:
    if len(assignments) < 1:
        raise ValueError("full-grid prompt requires at least one assignment")
    lines = []
    for index, (statement, value) in enumerate(assignments, start=1):
        _validate_pin_component(statement, "premise statement")
        _validate_pin_component(value, "premise value")
        lines.append(
            f"{index}. Premise: {statement}\n   Resolution: {value}"
        )
    prefix = (
        "For this rating only, use all of these resolutions of otherwise "
        "unspecified scoring premises:\n" + "\n".join(lines)
    )
    return _render_rating_prompt(
        framing,
        item,
        options,
        seed,
        template_id="premise-full-grid-v2",
        instruction="Select exactly one option that best applies:",
        response_example='{"choice":"<token>"}',
        prefix=prefix,
    )
def render_placebo_prompt(
    framing: TaskFraming,
    item: dict[str, str],
    options: tuple[PromptOption, ...],
    seed: int,
    *,
    matched_premise_statement: str,
    matched_premise_value: str,
) -> RenderedPrompt:
    _validate_pin_component(
        matched_premise_statement,
        "matched premise statement",
    )
    _validate_pin_component(
        matched_premise_value,
        "matched premise value",
    )
    matched = render_pinned_prompt(
        framing,
        item,
        options,
        seed,
        premise_statement=matched_premise_statement,
        premise_value=matched_premise_value,
    )
    placebo_statement, placebo_value = matched_placebo_components(
        matched_premise_statement,
        matched_premise_value,
    )
    prefix = _PIN_CLAUSE.format(
        premise_statement=placebo_statement,
        premise_value=placebo_value,
    )
    rendered = _render_rating_prompt(
        framing,
        item,
        options,
        seed,
        template_id="placebo-pinned-v2",
        instruction="Select exactly one option that best applies:",
        response_example='{"choice":"<token>"}',
        prefix=prefix,
    )
    return rendered.model_copy(
        update={
            "matched_prompt_length": matched.prompt_length,
            "length_delta": rendered.prompt_length - matched.prompt_length,
        }
    )


def _validate_pin_component(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be blank")
    if any(character in _LINE_SEPARATORS for character in value):
        raise ValueError(f"{field_name} must be a single line")
    if re.search(r"\b(?:premise|resolution)\s*:", value, re.IGNORECASE):
        raise ValueError(f"{field_name} contains a structural delimiter")


def _match_length(base: str, target_length: int, pad: str) -> str:
    if target_length <= 0:
        raise ValueError("target length must be positive")
    if target_length <= len(base):
        return base[:target_length]
    return base + (pad * (target_length - len(base)))


def matched_placebo_components(
    matched_premise_statement: str,
    matched_premise_value: str,
) -> tuple[str, str]:
    _validate_pin_component(
        matched_premise_statement,
        "matched premise statement",
    )
    _validate_pin_component(
        matched_premise_value,
        "matched premise value",
    )
    return (
        _match_length(
            _PLACEBO_PREMISE,
            len(matched_premise_statement),
            "x",
        ),
        _match_length(
            _PLACEBO_VALUE,
            len(matched_premise_value),
            "y",
        ),
    )
