import asyncio
from pathlib import Path

from pprs.cache import ParquetRecordCache
from pprs.collector import CollectionContext, Collector
from pprs.data.schema import TaskId
from pprs.providers.base import (
    CallIdentity,
    ProviderFailure,
    ProviderRequest,
    ProviderResponse,
    ProviderTimeout,
    ResponseFormat,
)
from pprs.providers.mock import MockProvider
from pprs.records.schema import ElicitationPath, ParseStatus


def _request(response_format: ResponseFormat) -> ProviderRequest:
    return ProviderRequest(
        identity=CallIdentity(
            rendered_prompt="Rendered prompt",
            model_snapshot="mock-snapshot-2026-08-06",
            temperature=0.0,
            top_p=1.0,
            seed=42,
            response_format=response_format,
        ),
        provider="mock",
    )


def _context(
    path: ElicitationPath = ElicitationPath.FORCED_CHOICE,
    **updates: object,
) -> CollectionContext:
    payload = {
        "run_tag": "wp3-test",
        "git_sha": "a" * 40,
        "prereg_tag": None,
        "task": TaskId.CHAOSNLI_SNLI,
        "item_id": "46359n",
        "judge_id": "mock-judge",
        "path": path,
        "sample_id": 0,
        "prompt_template_id": "fixture-v1",
        "option_permutation_seed": 7,
        "valid_tokens": ("A", "B", "C"),
    }
    payload.update(updates)
    return CollectionContext.model_validate(payload)


def test_identical_concurrent_collection_invokes_provider_once(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        provider = MockProvider(
            ['{"choice":"A"}'],
            delay_seconds=0.01,
        )
        collector = Collector(provider, ParquetRecordCache(tmp_path))
        request = _request(ResponseFormat.FORCED_CHOICE_JSON)
        context = _context()
        first, second = await asyncio.gather(
            collector.collect(request, context),
            collector.collect(request, context),
        )
        assert first == second
        assert provider.invocation_count == 1

    asyncio.run(scenario())


def test_concurrent_collectors_share_cache_lock(tmp_path: Path) -> None:
    async def scenario() -> None:
        provider = MockProvider(
            ['{"choice":"A"}'],
            delay_seconds=0.01,
        )
        cache = ParquetRecordCache(tmp_path)
        first_collector = Collector(provider, cache)
        second_collector = Collector(provider, cache)
        request = _request(ResponseFormat.FORCED_CHOICE_JSON)
        context = _context()
        first, second = await asyncio.gather(
            first_collector.collect(request, context),
            second_collector.collect(request, context),
        )
        assert first == second
        assert provider.invocation_count == 1

    asyncio.run(scenario())


def test_separate_cache_instances_share_root_lock(tmp_path: Path) -> None:
    async def scenario() -> None:
        provider = MockProvider(
            ['{"choice":"A"}'],
            delay_seconds=0.01,
        )
        first_collector = Collector(
            provider,
            ParquetRecordCache(tmp_path),
        )
        second_collector = Collector(
            provider,
            ParquetRecordCache(tmp_path),
        )
        request = _request(ResponseFormat.FORCED_CHOICE_JSON)
        context = _context()
        first, second = await asyncio.gather(
            first_collector.collect(request, context),
            second_collector.collect(request, context),
        )
        assert first == second
        assert provider.invocation_count == 1

    asyncio.run(scenario())


def test_cache_coordination_survives_new_event_loop(tmp_path: Path) -> None:
    async def collect_once(provider: MockProvider) -> None:
        cache = ParquetRecordCache(tmp_path)
        collector = Collector(provider, cache)
        await asyncio.gather(
            collector.collect(
                _request(ResponseFormat.FORCED_CHOICE_JSON),
                _context(),
            ),
            Collector(provider, ParquetRecordCache(tmp_path)).collect(
                _request(ResponseFormat.FORCED_CHOICE_JSON),
                _context(),
            ),
        )

    first_provider = MockProvider(
        ['{"choice":"A"}'],
        delay_seconds=0.01,
    )
    asyncio.run(collect_once(first_provider))
    assert first_provider.invocation_count == 1

    second_provider = MockProvider(['{"choice":"B"}'])
    asyncio.run(collect_once(second_provider))
    assert second_provider.invocation_count == 0


def test_malformed_and_missing_payloads_preserve_raw_text(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        malformed_provider = MockProvider(["not-json"])
        malformed = await Collector(
            malformed_provider,
            ParquetRecordCache(tmp_path / "malformed"),
        ).collect(
            _request(ResponseFormat.FORCED_CHOICE_JSON),
            _context(),
        )
        assert malformed.parse_status is ParseStatus.MALFORMED_JSON
        assert malformed.raw_text == "not-json"
        assert malformed.parsed_choice_hard is None

        missing_provider = MockProvider(["{}"])
        missing = await Collector(
            missing_provider,
            ParquetRecordCache(tmp_path / "missing"),
        ).collect(
            _request(ResponseFormat.FORCED_CHOICE_JSON),
            _context(),
        )
        assert missing.parse_status is ParseStatus.MISSING_FIELD
        assert missing.raw_text == "{}"
        assert missing.parsed_choice_hard is None

    asyncio.run(scenario())


def test_timeout_and_provider_error_are_durable_failures(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        timeout = await Collector(
            MockProvider(
                [
                    ProviderTimeout(
                        "timed out",
                        raw_text="partial",
                        http_status=504,
                        retry_count=2,
                    )
                ]
            ),
            ParquetRecordCache(tmp_path / "timeout"),
        ).collect(
            _request(ResponseFormat.FORCED_CHOICE_JSON),
            _context(),
        )
        assert timeout.parse_status is ParseStatus.TIMEOUT
        assert timeout.raw_text == "partial"
        assert timeout.http_status == 504
        assert timeout.retry_count == 2
        assert timeout.parsed_choice_hard is None

        failure = await Collector(
            MockProvider(
                [
                    ProviderFailure(
                        "provider failed",
                        raw_text="provider body",
                        http_status=503,
                    )
                ]
            ),
            ParquetRecordCache(tmp_path / "provider"),
        ).collect(
            _request(ResponseFormat.FORCED_CHOICE_JSON),
            _context(),
        )
        assert failure.parse_status is ParseStatus.PROVIDER_ERROR
        assert failure.raw_text == "provider body"
        assert failure.http_status == 503
        assert failure.parsed_choice_hard is None

    asyncio.run(scenario())


def test_valid_tokens_must_match_task_before_collection(
    tmp_path: Path,
) -> None:
    provider = MockProvider(['{"choice":"A"}'])
    try:
        _context(valid_tokens=("A", "B"))
    except ValueError as exc:
        assert "locked task contract" in str(exc)
    else:
        raise AssertionError("invalid task token contract must fail")
    assert provider.invocation_count == 0


def test_refusal_is_not_success(tmp_path: Path) -> None:
    async def scenario() -> None:
        record = await Collector(
            MockProvider(
                [
                    ProviderResponse(
                        raw_text='{"choice":"A"}',
                        refused=True,
                    )
                ]
            ),
            ParquetRecordCache(tmp_path),
        ).collect(
            _request(ResponseFormat.FORCED_CHOICE_JSON),
            _context(),
        )
        assert record.parse_status is ParseStatus.REFUSED
        assert record.parsed_choice_hard is None

    asyncio.run(scenario())


def test_premise_disclosure_and_scoring_paths(tmp_path: Path) -> None:
    async def scenario() -> None:
        disclosure = await Collector(
            MockProvider(
                [
                    """
                    {
                      "premises": [{
                        "premise_id": "coverage",
                        "premise_type": "vagueness",
                        "statement": "How much coverage is required?",
                        "candidate_values": ["strict", "lenient"]
                      }]
                    }
                    """
                ]
            ),
            ParquetRecordCache(tmp_path / "disclosure"),
        ).collect(
            _request(ResponseFormat.PREMISE_DISCLOSURE_JSON),
            _context(
                ElicitationPath.PREMISE_PINNED,
                premise_round=0,
            ),
        )
        assert disclosure.parse_status is ParseStatus.OK
        assert disclosure.parsed_premises is not None

        scoring = await Collector(
            MockProvider(['{"choice":"B"}']),
            ParquetRecordCache(tmp_path / "scoring"),
        ).collect(
            _request(ResponseFormat.FORCED_CHOICE_JSON),
            _context(
                ElicitationPath.PREMISE_PINNED,
                premise_id="coverage",
                premise_type="vagueness",
                premise_value="strict",
                premise_round=0,
            ),
        )
        assert scoring.parse_status is ParseStatus.OK
        assert scoring.parsed_choice_hard == "B"

    asyncio.run(scenario())


def test_path_format_mismatch_fails_before_provider(tmp_path: Path) -> None:
    async def scenario() -> None:
        provider = MockProvider(['{"choices":["A"]}'])
        collector = Collector(provider, ParquetRecordCache(tmp_path))
        try:
            await collector.collect(
                _request(ResponseFormat.RESPONSE_SET_JSON),
                _context(ElicitationPath.FORCED_CHOICE),
            )
        except ValueError as exc:
            assert "requires response format" in str(exc)
        else:
            raise AssertionError("path/format mismatch must fail")
        assert provider.invocation_count == 0

    asyncio.run(scenario())
