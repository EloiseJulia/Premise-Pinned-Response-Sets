from __future__ import annotations

import json
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from pprs.providers.base import (
    Provider,
    ProviderFailure,
    ProviderRequest,
    ProviderResponse,
    ProviderTimeout,
)


class LiteLLMProviderSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    api_base: str | None = Field(default=None, min_length=1)
    api_key: SecretStr | None = None
    allow_unauthenticated_local: bool = False
    temperature_unsupported_models: tuple[str, ...] = ()

    @classmethod
    def from_ghc_api_env(cls) -> "LiteLLMProviderSettings":
        api_base = os.environ.get("GHC_API_BASE_URL")
        if not api_base:
            raise ValueError(
                "GHC_API_BASE_URL is required for the local ghc-api provider"
            )
        api_key = os.environ.get("GHC_API_KEY")
        unsupported = tuple(
            pattern.strip()
            for pattern in os.environ.get(
                "GHC_API_TEMPERATURE_UNSUPPORTED_MODELS",
                "",
            ).split(",")
            if pattern.strip()
        )
        return cls(
            api_base=api_base,
            api_key=SecretStr(api_key) if api_key else None,
            allow_unauthenticated_local=api_key is None,
            temperature_unsupported_models=unsupported,
        )


def _raw_text_from_exception(exc: Exception) -> str:
    raw_response = getattr(exc, "raw_response", None)
    if isinstance(raw_response, str):
        return raw_response
    response = getattr(exc, "response", None)
    response_text = getattr(response, "text", None)
    if isinstance(response_text, str) and response_text:
        return response_text
    body = getattr(exc, "body", None)
    if isinstance(body, str):
        return body
    if body is not None:
        return json.dumps(body, ensure_ascii=True, sort_keys=True)
    debug_info = getattr(exc, "litellm_debug_info", None)
    if isinstance(debug_info, str) and debug_info:
        return debug_info
    message = getattr(exc, "message", None)
    if isinstance(message, str) and message:
        return message
    return str(exc)


def _retry_count_from_exception(exc: Exception) -> int:
    value = getattr(exc, "num_retries", None)
    if value is None:
        value = getattr(exc, "retry_count", 0)
    return int(value or 0)


def _http_status_from_exception(exc: Exception) -> int | None:
    value = getattr(exc, "status_code", None)
    if value is None:
        value = getattr(exc, "exception_status_code", None)
    if value is None:
        value = getattr(getattr(exc, "response", None), "status_code", None)
    return int(value) if value is not None else None


def _redact_secret(text: str, secret: str | None) -> str:
    if secret:
        return text.replace(secret, "[REDACTED]")
    return text


class LiteLLMProvider(Provider):
    def __init__(
        self,
        settings: LiteLLMProviderSettings | None = None,
    ) -> None:
        self.settings = settings or LiteLLMProviderSettings()
        self.invocation_count = 0

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        import litellm

        identity = request.identity
        if self.settings.api_base is None:
            raise ProviderFailure(
                "explicit api_base is required; refusing provider fallback"
            )
        if any(
            pattern in identity.model_snapshot
            for pattern in self.settings.temperature_unsupported_models
        ):
            raise ProviderFailure(
                "model snapshot does not support the locked temperature field"
            )
        model = f"{request.provider}/{identity.model_snapshot}"
        max_completion_tokens = {
            "forced_choice_json_v1": 64,
            "response_set_json_v1": 128,
            "premise_disclosure_json_v1": 2048,
        }[identity.response_format.value]
        call_kwargs: dict[str, Any] = {}
        if self.settings.api_base is not None:
            call_kwargs["api_base"] = self.settings.api_base.rstrip("/")
        if self.settings.api_key is not None:
            call_kwargs["api_key"] = self.settings.api_key.get_secret_value()
        elif self.settings.allow_unauthenticated_local:
            call_kwargs["api_key"] = "local-proxy-no-auth"
        else:
            raise ProviderFailure(
                "api_key is required unless unauthenticated local mode is explicit"
            )
        secret = (
            self.settings.api_key.get_secret_value()
            if self.settings.api_key is not None
            else None
        )
        sanitized_failure: ProviderFailure | ProviderTimeout | None = None
        response: Any | None = None
        try:
            self.invocation_count += 1
            response: Any = await litellm.acompletion(
                model=model,
                messages=[
                    {"role": "user", "content": identity.rendered_prompt}
                ],
                temperature=identity.temperature,
                top_p=identity.top_p,
                seed=identity.seed,
                max_completion_tokens=max_completion_tokens,
                timeout=120,
                num_retries=0,
                response_format={"type": "json_object"},
                **call_kwargs,
            )
        except litellm.exceptions.Timeout as exc:
            sanitized_failure = ProviderTimeout(
                _redact_secret(str(exc), secret),
                raw_text=_redact_secret(
                    _raw_text_from_exception(exc),
                    secret,
                ),
                http_status=_http_status_from_exception(exc),
                retry_count=_retry_count_from_exception(exc),
            )
        except (
            litellm.exceptions.APIError,
            litellm.exceptions.APIConnectionError,
            litellm.exceptions.APIResponseValidationError,
            litellm.exceptions.AuthenticationError,
            litellm.exceptions.BadGatewayError,
            litellm.exceptions.BadRequestError,
            litellm.exceptions.BlockedPiiEntityError,
            litellm.exceptions.BudgetExceededError,
            litellm.exceptions.ContentPolicyViolationError,
            litellm.exceptions.ContextWindowExceededError,
            litellm.exceptions.GuardrailRaisedException,
            litellm.exceptions.ImageFetchError,
            litellm.exceptions.InternalServerError,
            litellm.exceptions.InvalidRequestError,
            litellm.exceptions.JSONSchemaValidationError,
            litellm.exceptions.LiteLLMUnknownProvider,
            litellm.exceptions.MidStreamFallbackError,
            litellm.exceptions.MockException,
            litellm.exceptions.ModifyResponseException,
            litellm.exceptions.NotFoundError,
            litellm.exceptions.OpenAIError,
            litellm.exceptions.PermissionDeniedError,
            litellm.exceptions.RateLimitError,
            litellm.exceptions.RejectedRequestError,
            litellm.exceptions.SensitiveDataRouteException,
            litellm.exceptions.ServiceUnavailableError,
            litellm.exceptions.UnprocessableEntityError,
            litellm.exceptions.UnsupportedParamsError,
        ) as exc:
            sanitized_failure = ProviderFailure(
                _redact_secret(str(exc), secret),
                raw_text=_redact_secret(
                    _raw_text_from_exception(exc),
                    secret,
                ),
                http_status=_http_status_from_exception(exc),
                retry_count=_retry_count_from_exception(exc),
            )

        if sanitized_failure is not None:
            raise sanitized_failure
        if response is None:
            raise ProviderFailure("LiteLLM returned no response")

        choice = response.choices[0]
        usage = getattr(response, "usage", None)
        return ProviderResponse(
            raw_text=choice.message.content or "",
            http_status=200,
            system_fingerprint=getattr(
                response,
                "system_fingerprint",
                None,
            ),
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            retry_count=0,
            refused=bool(getattr(choice.message, "refusal", None)),
        )
