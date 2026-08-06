from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResponseFormat(StrEnum):
    FORCED_CHOICE_JSON = "forced_choice_json_v1"
    RESPONSE_SET_JSON = "response_set_json_v1"
    PREMISE_DISCLOSURE_JSON = "premise_disclosure_json_v1"


class CallIdentity(StrictModel):
    rendered_prompt: str = Field(min_length=1)
    model_snapshot: str = Field(min_length=1)
    temperature: float = Field(ge=0)
    top_p: float = Field(gt=0, le=1)
    seed: int
    response_format: ResponseFormat

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

    def cache_key(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def prompt_hash(self) -> str:
        return hashlib.sha256(
            self.rendered_prompt.encode("utf-8")
        ).hexdigest()


class ProviderRequest(StrictModel):
    identity: CallIdentity
    provider: str = Field(min_length=1)


class ProviderResponse(StrictModel):
    raw_text: str
    http_status: int | None = None
    system_fingerprint: str | None = None
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    retry_count: int = Field(default=0, ge=0)
    refused: bool = False


class ProviderTimeout(Exception):
    def __init__(
        self,
        message: str,
        *,
        raw_text: str = "",
        http_status: int | None = None,
        retry_count: int = 0,
    ) -> None:
        super().__init__(message)
        self.raw_text = raw_text
        self.http_status = http_status
        self.retry_count = retry_count


class ProviderFailure(Exception):
    def __init__(
        self,
        message: str,
        *,
        raw_text: str = "",
        http_status: int | None = None,
        retry_count: int = 0,
    ) -> None:
        super().__init__(message)
        self.raw_text = raw_text
        self.http_status = http_status
        self.retry_count = retry_count


class Provider(ABC):
    @abstractmethod
    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Return one raw provider response or raise a typed provider failure."""
