import asyncio
from pathlib import Path

import pytest

from pprs.cache import CacheIdentityCollisionError, ParquetRecordCache
from pprs.records.schema import RawResult


def test_cache_round_trip_and_identical_put(
    tmp_path: Path,
    raw_result: RawResult,
) -> None:
    async def scenario() -> None:
        cache = ParquetRecordCache(tmp_path)
        await cache.put(raw_result)
        await cache.put(raw_result)
        loaded = await cache.get(raw_result.cache_key)
        assert loaded == raw_result
        assert len(list(tmp_path.glob("*.parquet"))) == 1

    asyncio.run(scenario())


def test_cache_rejects_identity_collision(
    tmp_path: Path,
    raw_result: RawResult,
) -> None:
    async def scenario() -> None:
        cache = ParquetRecordCache(tmp_path)
        await cache.put(raw_result)
        changed = raw_result.model_copy(update={"raw_text": "B"})
        with pytest.raises(CacheIdentityCollisionError):
            await cache.put(changed)
        assert await cache.get(raw_result.cache_key) == raw_result

    asyncio.run(scenario())


def test_partial_temp_file_is_not_a_cache_hit(
    tmp_path: Path,
    raw_result: RawResult,
) -> None:
    async def scenario() -> None:
        cache = ParquetRecordCache(tmp_path)
        partial = tmp_path / f".{raw_result.cache_key}.partial.tmp.parquet"
        partial.write_text("partial")
        assert await cache.get(raw_result.cache_key) is None

    asyncio.run(scenario())
