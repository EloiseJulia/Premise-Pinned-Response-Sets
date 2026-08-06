from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from pprs.cache import ParquetRecordCache
from pprs.pilot import PilotSummary
from pprs.records.schema import ParseStatus, RawResult

_FORMAT_TERMS = frozenset(
    """
    formatting format typography font color colour interface ui layout
    encoding json xml markdown language programming library tooling
    whitespace indentation capitalization punctuation
    """.split()
)
_GENERIC_TERMS = frozenset(
    """
    quality accuracy correctness evaluate evaluation assessment criteria
    rubric overall generally methodology method approach
    """.split()
)


class ReviewCell(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cache_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    task: str
    item_id: str
    model_snapshot: str
    template_id: str
    parse_status: str
    premise_count: int = Field(ge=0)
    premise_types: tuple[str, ...]
    preliminary_category: str
    flags: tuple[str, ...]
    raw_text: str


class ReviewSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pilot_run_tag: str
    total_cells: int
    category_counts: dict[str, int]
    by_template: dict[str, dict[str, int]]
    by_model: dict[str, dict[str, int]]
    review_cells: tuple[ReviewCell, ...]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def preliminarily_classify(record: RawResult) -> tuple[str, tuple[str, ...]]:
    if record.parse_status is not ParseStatus.OK:
        return record.parse_status.value, ()
    premises = record.parsed_premises or ()
    if not premises:
        return "empty", ("no_premises",)

    flags = []
    substantive = 0
    generic = 0
    for premise in premises:
        text = " ".join(
            (
                premise.statement,
                *premise.candidate_values,
            )
        )
        tokens = _tokens(text)
        if tokens & _FORMAT_TERMS:
            flags.append(f"format_or_tooling:{premise.premise_id}")
            continue
        if len(tokens & _GENERIC_TERMS) >= 2:
            generic += 1
            flags.append(f"generic:{premise.premise_id}")
            continue
        substantive += 1

    if substantive:
        return "pinable_candidate", tuple(flags)
    if generic:
        return "generic_methodology", tuple(flags)
    return "format_or_tooling", tuple(flags)


async def load_review(
    summary_path: Path,
    cache_dir: Path,
) -> ReviewSummary:
    pilot = PilotSummary.model_validate_json(
        summary_path.read_text(encoding="utf-8")
    )
    cache = ParquetRecordCache(cache_dir)
    cells = []
    category_counts = Counter()
    by_template: dict[str, Counter] = defaultdict(Counter)
    by_model: dict[str, Counter] = defaultdict(Counter)

    for cache_key in pilot.result_cache_keys:
        record = await cache.get(cache_key)
        if record is None:
            raise ValueError(f"missing pilot cache record: {cache_key}")
        category, flags = preliminarily_classify(record)
        premises = record.parsed_premises or ()
        cell = ReviewCell(
            cache_key=cache_key,
            task=record.task.value,
            item_id=record.item_id,
            model_snapshot=record.model_snapshot,
            template_id=record.prompt_template_id,
            parse_status=record.parse_status.value,
            premise_count=len(premises),
            premise_types=tuple(
                premise.premise_type.value for premise in premises
            ),
            preliminary_category=category,
            flags=flags,
            raw_text=record.raw_text,
        )
        cells.append(cell)
        category_counts[category] += 1
        by_template[record.prompt_template_id][category] += 1
        by_model[record.model_snapshot][category] += 1

    if len(cells) != pilot.total_cells:
        raise ValueError("review cell count does not match pilot summary")
    return ReviewSummary(
        pilot_run_tag=pilot.run_tag,
        total_cells=len(cells),
        category_counts=dict(sorted(category_counts.items())),
        by_template={
            key: dict(sorted(counts.items()))
            for key, counts in sorted(by_template.items())
        },
        by_model={
            key: dict(sorted(counts.items()))
            for key, counts in sorted(by_model.items())
        },
        review_cells=tuple(cells),
    )


def write_review(review: ReviewSummary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            review.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
