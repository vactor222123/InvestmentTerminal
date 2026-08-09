import os

import pytest

from investment_terminal.ai.providers.environment import (
    EnvironmentGroundedProviderCredentialSource,
)


def source():
    return EnvironmentGroundedProviderCredentialSource(
        variable_by_provider={
            "OPENAI": "INVESTMENT_TERMINAL_OPENAI_API_KEY",
        }
    )


def test_environment_source_reads_explicit_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "INVESTMENT_TERMINAL_OPENAI_API_KEY",
        "secret-value",
    )

    assert source().get_api_key(
        provider_identity="OPENAI"
    ) == "secret-value"


def test_missing_environment_variable_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "INVESTMENT_TERMINAL_OPENAI_API_KEY",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="is not set",
    ):
        source().get_api_key(
            provider_identity="OPENAI"
        )


def test_empty_environment_variable_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "INVESTMENT_TERMINAL_OPENAI_API_KEY",
        "   ",
    )

    with pytest.raises(
        RuntimeError,
        match="is empty",
    ):
        source().get_api_key(
            provider_identity="OPENAI"
        )


def test_unknown_provider_mapping_fails_closed() -> None:
    with pytest.raises(
        KeyError,
        match="No environment credential mapping",
    ):
        source().get_api_key(
            provider_identity="OTHER"
        )


def test_configured_provider_metadata_excludes_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "INVESTMENT_TERMINAL_OPENAI_API_KEY",
        "secret-value",
    )
    item = source()

    assert item.configured_providers() == (
        "OPENAI",
    )
    assert item.environment_variable_name(
        provider_identity="OPENAI"
    ) == "INVESTMENT_TERMINAL_OPENAI_API_KEY"

    metadata = (
        repr(item)
        + str(item.configured_providers())
        + item.environment_variable_name(
            provider_identity="OPENAI"
        )
    )
    assert "secret-value" not in metadata


def test_environment_source_has_no_serialization_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "INVESTMENT_TERMINAL_OPENAI_API_KEY",
        "secret-value",
    )

    assert not hasattr(
        source(),
        "to_dict",
    )


def test_mapping_must_be_explicit_and_non_empty() -> None:
    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        EnvironmentGroundedProviderCredentialSource(
            variable_by_provider={}
        )


def test_environment_source_does_not_load_dotenv_or_mutate_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = "INVESTMENT_TERMINAL_OPENAI_API_KEY"
    monkeypatch.setenv(
        key,
        "secret-value",
    )
    before = dict(
        os.environ
    )

    assert source().get_api_key(
        provider_identity="OPENAI"
    ) == "secret-value"

    assert dict(
        os.environ
    ) == before


def test_module_imports_no_dotenv_or_provider_sdk() -> None:
    import investment_terminal.ai.providers.environment as module

    names = {
        name.lower()
        for name in module.__dict__
    }

    forbidden = (
        "dotenv",
        "openai",
        "anthropic",
        "httpx",
        "requests",
    )
    assert not any(
        item in names
        for item in forbidden
    )
