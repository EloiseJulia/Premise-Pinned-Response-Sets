from pathlib import Path


def test_provider_integration_uses_only_litellm_directly() -> None:
    project = Path("pyproject.toml").read_text().lower()
    for provider_package in (
        "openai",
        "anthropic",
        "mistralai",
    ):
        assert provider_package not in project
