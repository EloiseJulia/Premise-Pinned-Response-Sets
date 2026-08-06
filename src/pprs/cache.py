from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from collections.abc import AsyncIterator
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq
from filelock import FileLock

from pprs.records.schema import RawResult, raw_result_arrow_schema


class CacheIdentityCollisionError(RuntimeError):
    """Raised when one cache key is associated with different raw records."""


class ParquetRecordCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, cache_key: str) -> Path:
        if len(cache_key) != 64 or any(
            character not in "0123456789abcdef" for character in cache_key
        ):
            raise ValueError("cache key must be lowercase SHA-256 hex")
        return self.root / f"{cache_key}.parquet"

    @asynccontextmanager
    async def _file_guard(
        self,
        cache_key: str,
        purpose: str,
    ) -> AsyncIterator[None]:
        self._path(cache_key)
        lock = FileLock(
            str(self.root / f".{cache_key}.{purpose}.lock"),
            timeout=60,
            thread_local=False,
        )
        await asyncio.to_thread(lock.acquire)
        try:
            yield
        finally:
            await asyncio.to_thread(lock.release)

    def collection_guard(self, cache_key: str) -> AsyncIterator[None]:
        return self._file_guard(cache_key, "collection")

    async def get(self, cache_key: str) -> RawResult | None:
        path = self._path(cache_key)
        if not path.exists():
            return None
        table = await asyncio.to_thread(pq.read_table, path)
        rows = table.to_pylist()
        if len(rows) != 1:
            raise ValueError("cache files must contain exactly one record")
        return RawResult.model_validate(rows[0])

    async def put(self, record: RawResult) -> None:
        async with self._file_guard(record.cache_key, "write"):
            existing = await self.get(record.cache_key)
            if existing is not None:
                if existing.model_dump(mode="json") != record.model_dump(
                    mode="json"
                ):
                    raise CacheIdentityCollisionError(
                        "cache key already stores a different record"
                    )
                return

            final_path = self._path(record.cache_key)
            temp_path = self.root / (
                f".{record.cache_key}.{uuid4().hex}.tmp.parquet"
            )
            row = record.model_dump(mode="json")
            row["ts_utc"] = record.ts_utc
            table = pa.Table.from_pylist(
                [row],
                schema=raw_result_arrow_schema(),
            )
            try:
                await asyncio.to_thread(pq.write_table, table, temp_path)
                await asyncio.to_thread(os.replace, temp_path, final_path)
            finally:
                if temp_path.exists():
                    temp_path.unlink()
