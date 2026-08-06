import pytest

from pprs.providers.base import (
    CallIdentity,
    ProviderRequest,
    ResponseFormat,
)


@pytest.fixture
def identity() -> CallIdentity:
    return CallIdentity(
        rendered_prompt="Choose one option.",
        model_snapshot="mock-snapshot-2026-08-06",
        temperature=0.0,
        top_p=1.0,
        seed=42,
        response_format=ResponseFormat.FORCED_CHOICE_JSON,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rendered_prompt", "Changed prompt."),
        ("model_snapshot", "other-snapshot"),
        ("temperature", 0.7),
        ("top_p", 0.9),
        ("seed", 43),
        ("response_format", ResponseFormat.RESPONSE_SET_JSON),
    ],
)
def test_each_identity_field_changes_cache_key(
    identity: CallIdentity,
    field: str,
    value: object,
) -> None:
    changed = identity.model_copy(update={field: value})
    assert changed.cache_key() != identity.cache_key()


def test_provider_metadata_does_not_change_locked_cache_identity(
    identity: CallIdentity,
) -> None:
    first = ProviderRequest(identity=identity, provider="provider-a")
    second = ProviderRequest(identity=identity, provider="provider-b")
    assert first.identity.cache_key() == second.identity.cache_key()
