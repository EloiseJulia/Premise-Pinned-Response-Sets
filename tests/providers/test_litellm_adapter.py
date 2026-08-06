from types import SimpleNamespace

import httpx
import litellm
import pytest

from pprs.providers.base import (
    CallIdentity,
    ProviderFailure,
    ProviderRequest,
    ResponseFormat,
)
from pprs.providers.litellm import (
    LiteLLMProvider,
    LiteLLMProviderSettings,
    _http_status_from_exception,
    _raw_text_from_exception,
    _retry_count_from_exception,
)


def test_litellm_exception_metadata_is_preserved() -> None:
    exc = RuntimeError("provider failed")
    exc.response = SimpleNamespace(text="provider raw body")
    exc.num_retries = 3
    exc.exception_status_code = 503

    assert _raw_text_from_exception(exc) == "provider raw body"
    assert _retry_count_from_exception(exc) == 3
    assert _http_status_from_exception(exc) == 503


def test_real_litellm_error_retains_available_provider_text() -> None:
    response = httpx.Response(
        503,
        text="provider raw body",
        request=httpx.Request("POST", "https://provider.invalid"),
    )
    exc = litellm.exceptions.ServiceUnavailableError(
        message="provider raw body",
        llm_provider="mock",
        model="mock-model",
        response=response,
        num_retries=4,
    )

    assert "provider raw body" in _raw_text_from_exception(exc)
    assert _http_status_from_exception(exc) == 503
    assert _retry_count_from_exception(exc) == 4


def test_json_schema_error_prefers_raw_provider_response() -> None:
    exc = RuntimeError("schema failed")
    exc.raw_response = "RAW-PROVIDER-TEXT"
    exc.message = "diagnostic"

    assert _raw_text_from_exception(exc) == "RAW-PROVIDER-TEXT"


def test_empty_raw_provider_response_stays_empty() -> None:
    exc = RuntimeError("schema failed")
    exc.raw_response = ""
    exc.message = "diagnostic"

    assert _raw_text_from_exception(exc) == ""


def test_local_endpoint_configuration_is_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    async def fake_completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"choice":"A"}',
                        refusal=None,
                    )
                )
            ],
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=3),
        )

    monkeypatch.setattr(litellm, "acompletion", fake_completion)
    provider = LiteLLMProvider(
        LiteLLMProviderSettings(
            api_base="http://127.0.0.1:8313/v1/",
            api_key="local-key",
        )
    )
    request = ProviderRequest(
        identity=CallIdentity(
            rendered_prompt="prompt",
            model_snapshot="snapshot",
            temperature=0.7,
            top_p=1.0,
            seed=42,
            response_format=ResponseFormat.FORCED_CHOICE_JSON,
        ),
        provider="openai",
    )

    response = __import__("asyncio").run(provider.complete(request))
    assert response.raw_text == '{"choice":"A"}'
    assert captured["api_base"] == "http://127.0.0.1:8313/v1"
    assert captured["api_key"] == "local-key"
    assert captured["temperature"] == 0.7
    assert captured["top_p"] == 1.0
    assert captured["seed"] == 42


def test_temperature_unsupported_model_fails_before_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    async def fake_completion(**kwargs):
        nonlocal called
        called = True
        return kwargs

    monkeypatch.setattr(litellm, "acompletion", fake_completion)
    provider = LiteLLMProvider(
        LiteLLMProviderSettings(
            api_base="http://127.0.0.1:8313/v1",
            temperature_unsupported_models=("gpt-5.6",),
        )
    )
    request = ProviderRequest(
        identity=CallIdentity(
            rendered_prompt="prompt",
            model_snapshot="gpt-5.6-sol",
            temperature=0.0,
            top_p=1.0,
            seed=42,
            response_format=ResponseFormat.FORCED_CHOICE_JSON,
        ),
        provider="openai",
    )

    with pytest.raises(ProviderFailure, match="locked temperature"):
        __import__("asyncio").run(provider.complete(request))
    assert not called


def test_missing_api_base_fails_before_litellm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    async def fake_completion(**kwargs):
        nonlocal called
        called = True
        return kwargs

    monkeypatch.setattr(litellm, "acompletion", fake_completion)
    provider = LiteLLMProvider()
    request = ProviderRequest(
        identity=CallIdentity(
            rendered_prompt="prompt",
            model_snapshot="snapshot",
            temperature=0.0,
            top_p=1.0,
            seed=42,
            response_format=ResponseFormat.FORCED_CHOICE_JSON,
        ),
        provider="openai",
    )

    with pytest.raises(ProviderFailure, match="explicit api_base"):
        __import__("asyncio").run(provider.complete(request))
    assert not called


def test_guardrail_error_is_mapped_to_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_completion(**kwargs):
        del kwargs
        raise litellm.exceptions.GuardrailRaisedException(
            guardrail_name="fixture",
            message="blocked",
        )

    monkeypatch.setattr(litellm, "acompletion", fake_completion)
    provider = LiteLLMProvider(
        LiteLLMProviderSettings(api_base="http://127.0.0.1:8313/v1")
    )
    request = ProviderRequest(
        identity=CallIdentity(
            rendered_prompt="prompt",
            model_snapshot="snapshot",
            temperature=0.0,
            top_p=1.0,
            seed=42,
            response_format=ResponseFormat.FORCED_CHOICE_JSON,
        ),
        provider="openai",
    )

    with pytest.raises(ProviderFailure, match="blocked"):
        __import__("asyncio").run(provider.complete(request))


def test_mapped_errors_redact_api_key_and_drop_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "super-secret-local-key"

    async def fake_completion(**kwargs):
        del kwargs
        raise litellm.exceptions.GuardrailRaisedException(
            guardrail_name="fixture",
            message=f"blocked with {secret}",
        )

    monkeypatch.setattr(litellm, "acompletion", fake_completion)
    provider = LiteLLMProvider(
        LiteLLMProviderSettings(
            api_base="http://127.0.0.1:8313/v1",
            api_key=secret,
        )
    )
    request = ProviderRequest(
        identity=CallIdentity(
            rendered_prompt="prompt",
            model_snapshot="snapshot",
            temperature=0.0,
            top_p=1.0,
            seed=42,
            response_format=ResponseFormat.FORCED_CHOICE_JSON,
        ),
        provider="openai",
    )

    with pytest.raises(ProviderFailure) as caught:
        __import__("asyncio").run(provider.complete(request))
    assert secret not in str(caught.value)
    assert secret not in caught.value.raw_text
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


def test_litellm_openai_error_is_mapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_completion(**kwargs):
        del kwargs
        raise litellm.exceptions.OpenAIError(
            original_exception=RuntimeError("openai failure")
        )

    monkeypatch.setattr(litellm, "acompletion", fake_completion)
    provider = LiteLLMProvider(
        LiteLLMProviderSettings(api_base="http://127.0.0.1:8313/v1")
    )
    request = ProviderRequest(
        identity=CallIdentity(
            rendered_prompt="prompt",
            model_snapshot="snapshot",
            temperature=0.0,
            top_p=1.0,
            seed=42,
            response_format=ResponseFormat.FORCED_CHOICE_JSON,
        ),
        provider="openai",
    )

    with pytest.raises(ProviderFailure):
        __import__("asyncio").run(provider.complete(request))
