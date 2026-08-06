from __future__ import annotations

import json
from pathlib import Path

from pprs.cache import ParquetRecordCache


async def build_review(
    summary_path: Path,
    cache_dir: Path,
) -> dict:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    keys = summary["first_run"]["cache_keys"]
    if len(keys) < 20:
        raise ValueError("smoke has fewer than 20 records")
    indices = [
        round(index * (len(keys) - 1) / 19) for index in range(20)
    ]
    cache = ParquetRecordCache(cache_dir)
    records = []
    for index in indices:
        record = await cache.get(keys[index])
        if record is None:
            raise ValueError(f"missing smoke record {keys[index]}")
        records.append(
            {
                "cache_key": record.cache_key,
                "task": record.task.value,
                "item_id": record.item_id,
                "judge_id": record.judge_id,
                "path": record.path.value,
                "parse_status": record.parse_status.value,
                "raw_text": record.raw_text,
                "parsed_choice_hard": record.parsed_choice_hard,
                "parsed_choice_set": record.parsed_choice_set,
                "parsed_premises": (
                    [
                        premise.model_dump(mode="json")
                        for premise in record.parsed_premises
                    ]
                    if record.parsed_premises
                    else None
                ),
                "premise_id": record.premise_id,
                "premise_type": (
                    record.premise_type.value
                    if record.premise_type
                    else None
                ),
                "premise_value": record.premise_value,
                "premise_round": record.premise_round,
                "provider_error": record.provider_error,
                "http_status": record.http_status,
                "retry_count": record.retry_count,
                "review_checks": {
                    "non_ok_parsed_fields_null": (
                        record.parse_status.value == "ok"
                        or (
                            record.parsed_choice_hard is None
                            and record.parsed_choice_set is None
                            and record.parsed_premises is None
                        )
                    ),
                    "raw_text_preserved": record.raw_text is not None,
                    "cache_key_matches_summary": record.cache_key == keys[index],
                },
            }
        )
    return {
        "review_type": "deterministic_20_record_smoke_packet",
        "human_owner_review_status": "pending",
        "run_tag": summary["first_run"]["run_tag"],
        "git_sha": summary["first_run"]["git_sha"],
        "subset_id": summary["first_run"]["subset_id"],
        "indices": indices,
        "records": records,
    }
