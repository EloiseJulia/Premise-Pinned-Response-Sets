from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pprs.cache import CacheIdentityCollisionError, ParquetRecordCache
from pprs.data.schema import TaskId
from pprs.parsing import ParseResult, parse_response
from pprs.providers.base import (
    Provider,
    ProviderFailure,
    ProviderRequest,
    ProviderResponse,
    ProviderTimeout,
)
from pprs.records.schema import (
    ElicitationPath,
    ParseStatus,
    PremiseType,
    RawResult,
)


class CollectionContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_tag: str = Field(min_length=1)
    git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    prereg_tag: str | None
    task: TaskId
    item_id: str = Field(min_length=1)
    judge_id: str = Field(min_length=1)
    path: ElicitationPath
    sample_id: int = Field(ge=0)
    premise_id: str | None = None
    premise_type: PremiseType | None = None
    premise_value: str | None = None
    premise_round: int | None = Field(default=None, ge=0)
    prompt_template_id: str = Field(min_length=1)
    option_permutation_seed: int
    valid_tokens: tuple[str, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_stage_coordinates(self) -> CollectionContext:
        expected_tokens = {
            TaskId.CHAOSNLI_SNLI: ("A", "B", "C"),
            TaskId.CHAOSNLI_MNLI: ("A", "B", "C"),
            TaskId.SUMMEVAL_RELEVANCE: ("A", "B"),
        }[self.task]
        if self.valid_tokens != expected_tokens:
            raise ValueError("valid tokens must match the locked task contract")

        coordinates = (
            self.premise_id,
            self.premise_type,
            self.premise_value,
            self.premise_round,
        )
        if self.path is not ElicitationPath.PREMISE_PINNED:
            if any(value is not None for value in coordinates):
                raise ValueError(
                    "non-premise collection cannot carry premise coordinates"
                )
            return self

        is_disclosure = (
            self.premise_id is None
            and self.premise_type is None
            and self.premise_value is None
            and self.premise_round is not None
        )
        is_scoring = all(value is not None for value in coordinates)
        if not (is_disclosure or is_scoring):
            raise ValueError(
                "premise collection must be disclosure or complete scoring"
            )
        return self


class Collector:
    def __init__(
        self,
        provider: Provider,
        cache: ParquetRecordCache,
    ) -> None:
        self.provider = provider
        self.cache = cache

    async def collect(
        self,
        request: ProviderRequest,
        context: CollectionContext,
    ) -> RawResult:
        self._validate_request_compatibility(request, context)
        identity = request.identity
        cache_key = identity.cache_key()
        async with self.cache.collection_guard(cache_key):
            cached = await self.cache.get(cache_key)
            if cached is not None:
                self._validate_cached_record(cached, request, context)
                return cached

            started = perf_counter()
            try:
                response = await self.provider.complete(request)
                result = self._from_response(
                    request,
                    context,
                    response,
                    elapsed_ms=self._elapsed_ms(started),
                )
            except ProviderTimeout as exc:
                result = self._failure_record(
                    request,
                    context,
                    status=ParseStatus.TIMEOUT,
                    raw_text=exc.raw_text,
                    provider_error=str(exc),
                    http_status=exc.http_status,
                    retry_count=exc.retry_count,
                    elapsed_ms=self._elapsed_ms(started),
                )
            except ProviderFailure as exc:
                result = self._failure_record(
                    request,
                    context,
                    status=ParseStatus.PROVIDER_ERROR,
                    raw_text=exc.raw_text,
                    provider_error=str(exc),
                    http_status=exc.http_status,
                    retry_count=exc.retry_count,
                    elapsed_ms=self._elapsed_ms(started),
                )

            await self.cache.put(result)
            return result

    @staticmethod
    def _validate_request_compatibility(
        request: ProviderRequest,
        context: CollectionContext,
    ) -> None:
        response_format = request.identity.response_format
        if context.path in {
            ElicitationPath.FORCED_CHOICE,
            ElicitationPath.PLACEBO,
        }:
            expected = "forced_choice_json_v1"
        elif context.path is ElicitationPath.MULTI_LABEL:
            expected = "response_set_json_v1"
        elif context.premise_id is None:
            expected = "premise_disclosure_json_v1"
        else:
            expected = "forced_choice_json_v1"

        if response_format.value != expected:
            raise ValueError(
                f"{context.path.value} stage requires response format {expected}"
            )

    @staticmethod
    def _validate_cached_record(
        cached: RawResult,
        request: ProviderRequest,
        context: CollectionContext,
    ) -> None:
        identity = request.identity
        expected = {
            "cache_key": identity.cache_key(),
            "run_tag": context.run_tag,
            "git_sha": context.git_sha,
            "prereg_tag": context.prereg_tag,
            "task": context.task,
            "item_id": context.item_id,
            "judge_id": context.judge_id,
            "path": context.path,
            "sample_id": context.sample_id,
            "premise_id": context.premise_id,
            "premise_type": context.premise_type,
            "premise_value": context.premise_value,
            "premise_round": context.premise_round,
            "model_snapshot": identity.model_snapshot,
            "provider": request.provider,
            "temperature": identity.temperature,
            "top_p": identity.top_p,
            "seed": identity.seed,
            "prompt_template_id": context.prompt_template_id,
            "prompt_hash": identity.prompt_hash(),
            "option_permutation_seed": context.option_permutation_seed,
        }
        if any(getattr(cached, field) != value for field, value in expected.items()):
            raise CacheIdentityCollisionError(
                "cached record metadata conflicts with this request"
            )

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, round((perf_counter() - started) * 1000))

    def _from_response(
        self,
        request: ProviderRequest,
        context: CollectionContext,
        response: ProviderResponse,
        *,
        elapsed_ms: int,
    ) -> RawResult:
        if response.refused:
            parse_result = ParseResult(status=ParseStatus.REFUSED)
        else:
            parse_result = parse_response(
                response.raw_text,
                request.identity.response_format,
                context.valid_tokens,
            )
        return self._record(
            request,
            context,
            parse_result=parse_result,
            raw_text=response.raw_text,
            provider_error=None,
            http_status=response.http_status,
            retry_count=response.retry_count,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            elapsed_ms=elapsed_ms,
        )

    def _failure_record(
        self,
        request: ProviderRequest,
        context: CollectionContext,
        *,
        status: ParseStatus,
        raw_text: str,
        provider_error: str,
        elapsed_ms: int,
        http_status: int | None = None,
        retry_count: int = 0,
    ) -> RawResult:
        return self._record(
            request,
            context,
            parse_result=ParseResult(status=status),
            raw_text=raw_text,
            provider_error=provider_error,
            http_status=http_status,
            retry_count=retry_count,
            prompt_tokens=None,
            completion_tokens=None,
            elapsed_ms=elapsed_ms,
        )

    @staticmethod
    def _record(
        request: ProviderRequest,
        context: CollectionContext,
        *,
        parse_result: ParseResult,
        raw_text: str,
        provider_error: str | None,
        http_status: int | None,
        retry_count: int,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        elapsed_ms: int,
    ) -> RawResult:
        identity = request.identity
        return RawResult(
            cache_key=identity.cache_key(),
            run_tag=context.run_tag,
            git_sha=context.git_sha,
            prereg_tag=context.prereg_tag,
            task=context.task,
            item_id=context.item_id,
            judge_id=context.judge_id,
            path=context.path,
            sample_id=context.sample_id,
            premise_id=context.premise_id,
            premise_type=context.premise_type,
            premise_value=context.premise_value,
            premise_round=context.premise_round,
            model_snapshot=identity.model_snapshot,
            provider=request.provider,
            temperature=identity.temperature,
            top_p=identity.top_p,
            seed=identity.seed,
            prompt_template_id=context.prompt_template_id,
            prompt_hash=identity.prompt_hash(),
            option_permutation_seed=context.option_permutation_seed,
            raw_text=raw_text,
            parsed_choice_hard=parse_result.parsed_choice_hard,
            parsed_choice_set=parse_result.parsed_choice_set,
            parsed_premises=parse_result.parsed_premises,
            parse_status=parse_result.status,
            provider_error=provider_error,
            http_status=http_status,
            retry_count=retry_count,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            wall_clock_ms=elapsed_ms,
            ts_utc=datetime.now(timezone.utc),
        )
