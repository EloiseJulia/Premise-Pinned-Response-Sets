from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Iterable

from pprs.providers.base import (
    Provider,
    ProviderFailure,
    ProviderRequest,
    ProviderResponse,
    ProviderTimeout,
)

MockOutcome = str | ProviderResponse | ProviderFailure | ProviderTimeout


class MockProvider(Provider):
    def __init__(
        self,
        outcomes: Iterable[MockOutcome],
        *,
        delay_seconds: float = 0.0,
    ) -> None:
        self._outcomes = deque(outcomes)
        self.delay_seconds = delay_seconds
        self.invocation_count = 0

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        del request
        self.invocation_count += 1
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if not self._outcomes:
            raise ProviderFailure("mock provider has no configured outcome")

        outcome = self._outcomes.popleft()
        if isinstance(outcome, (ProviderFailure, ProviderTimeout)):
            raise outcome
        if isinstance(outcome, ProviderResponse):
            return outcome
        return ProviderResponse(raw_text=outcome, http_status=200)
