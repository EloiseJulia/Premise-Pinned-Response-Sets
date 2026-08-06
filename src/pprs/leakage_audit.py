from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field
from filelock import FileLock

from pprs.data.schema import DatasetRecord, TaskId
from pprs.prompts import TaskFraming, render_disclosure_prompt

AUDITOR_MODEL = "mai-code-1-flash-picker"
AUDIT_SAMPLE_SIZE = 30
AUDITOR_MAX_COMPLETION_TOKENS = 2048


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LeakageAuditPayload(StrictModel):
    leakage: bool
    categories: tuple[str, ...]
    rationale: str = Field(min_length=1)


class LeakageAuditRecord(StrictModel):
    audit_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    task: TaskId
    item_id: str
    disclosure_template_id: str
    auditor_model: str
    seed: int
    raw_text: str
    status: str
    parsed: LeakageAuditPayload | None
    error: str | None


def select_audit_records(
    records_by_task: dict[TaskId, list[DatasetRecord]],
) -> tuple[DatasetRecord, ...]:
    selected = []
    for task in TaskId:
        records = records_by_task.get(task)
        if records is None or len(records) < AUDIT_SAMPLE_SIZE:
            raise ValueError(f"not enough leakage-audit records for {task}")
        selected.extend(records[:AUDIT_SAMPLE_SIZE])
    return tuple(selected)


def build_auditor_prompt(
    framing: TaskFraming,
    record: DatasetRecord,
    disclosure_template_id: str,
) -> str:
    rendered = render_disclosure_prompt(
        framing,
        record.inputs,
        disclosure_template_id,
    )
    static_prompt, source_item = rendered.text.split("\n\nItem:\n", maxsplit=1)
    forbidden = ", ".join(
        (*framing.forbidden_labels, *framing.forbidden_option_markers)
    )
    return f"""
You are auditing a scoring-premise disclosure prompt for answer leakage.

STATIC PROMPT:
--- begin static prompt ---
{static_prompt}
--- end static prompt ---

SOURCE ITEM (may naturally contain label-like words; do not blame the static
prompt for words that occur only here):
--- begin source item ---
{source_item}
--- end source item ---

Task option labels/markers to watch for: {forbidden}

Set leakage=true only if the STATIC PROMPT itself introduces an option label,
option marker, gold answer, directional answer hint, or a task-specific answer
axis beyond the source item. Generic rubric language is not leakage.

Return only JSON:
{{"leakage":false,"categories":[],"rationale":"short explanation"}}
""".strip()


def audit_key(
    prompt: str,
    model: str,
    seed: int,
    api_base: str = "http://127.0.0.1:8313/v1",
) -> str:
    canonical = json.dumps(
        {
            "api_base": api_base.rstrip("/"),
            "prompt": prompt,
            "model": model,
            "seed": seed,
            "top_p": 1.0,
            "max_completion_tokens": AUDITOR_MAX_COMPLETION_TOKENS,
            "response_format": "json_object",
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_audit_payload(raw_text: str) -> LeakageAuditPayload:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("auditor returned malformed JSON") from exc
    return LeakageAuditPayload.model_validate(payload)


def _call_auditor(
    api_base: str,
    prompt: str,
    *,
    model: str,
    seed: int,
) -> str:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "seed": seed,
            "top_p": 1.0,
            "max_completion_tokens": AUDITOR_MAX_COMPLETION_TOKENS,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    request = Request(
        f"{api_base.rstrip('/')}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"leakage auditor request failed: {exc}") from exc
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("leakage auditor response has no choices")
    content = choices[0].get("message", {}).get("content")
    if not isinstance(content, str):
        raise RuntimeError("leakage auditor response has no text content")
    return content


async def audit_record(
    *,
    api_base: str,
    framing: TaskFraming,
    record: DatasetRecord,
    disclosure_template_id: str,
    seed: int,
    cache_dir: Path,
    model: str = AUDITOR_MODEL,
) -> LeakageAuditRecord:
    prompt = build_auditor_prompt(
        framing,
        record,
        disclosure_template_id,
    )
    key = audit_key(prompt, model, seed, api_base)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{key}.json"
    lock = FileLock(
        str(cache_dir / f".{key}.lock"),
        timeout=60,
        thread_local=False,
    )
    await asyncio.to_thread(lock.acquire)
    try:
        if cache_path.exists():
            return LeakageAuditRecord.model_validate_json(
                cache_path.read_text(encoding="utf-8")
            )
        raw_text = ""
        try:
            raw_text = await asyncio.to_thread(
                _call_auditor,
                api_base,
                prompt,
                model=model,
                seed=seed,
            )
            parsed = parse_audit_payload(raw_text)
            result = LeakageAuditRecord(
                audit_key=key,
                task=record.task,
                item_id=record.item_id,
                disclosure_template_id=disclosure_template_id,
                auditor_model=model,
                seed=seed,
                raw_text=raw_text,
                status="ok",
                parsed=parsed,
                error=None,
            )
        except Exception as exc:
            result = LeakageAuditRecord(
                audit_key=key,
                task=record.task,
                item_id=record.item_id,
                disclosure_template_id=disclosure_template_id,
                auditor_model=model,
                seed=seed,
                raw_text=raw_text,
                status="error",
                parsed=None,
                error=str(exc),
            )
        temporary = cache_dir / f".{key}.{uuid4().hex}.tmp"
        temporary.write_text(
            result.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(cache_path)
        return result
    finally:
        await asyncio.to_thread(lock.release)
