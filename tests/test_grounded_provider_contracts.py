from abc import ABC

import pytest

from investment_terminal.ai.providers.contracts import (
    GroundedProviderConfig,
    GroundedProviderCredentialSource,
    StaticGroundedProviderCredentialSource,
)


def test_provider_config_is_non_secret_and_serializable() -> None:
    config = GroundedProviderConfig(
        provider_identity="OPENAI",
        model_identity="MODEL@1",
        timeout_seconds=30,
        max_retries=2,
    )

    assert config.to_dict() == {
        "provider_identity": "OPENAI",
        "model_identity": "MODEL@1",
        "timeout_seconds": 30.0,
        "max_retries": 2,
    }
    assert "api_key" not in config.to_dict()


def test_provider_config_rejects_invalid_timeout() -> None:
    with pytest.raises(
        ValueError,
        match="positive number",
    ):
        GroundedProviderConfig(
            provider_identity="OPENAI",
            model_identity="MODEL@1",
            timeout_seconds=0,
            max_retries=0,
        )


def test_provider_config_rejects_negative_retries() -> None:
    with pytest.raises(
        ValueError,
        match="non-negative integer",
    ):
        GroundedProviderConfig(
            provider_identity="OPENAI",
            model_identity="MODEL@1",
            timeout_seconds=10,
            max_retries=-1,
        )


def test_credential_source_is_abstract_boundary() -> None:
    assert issubclass(
        GroundedProviderCredentialSource,
        ABC,
    )
    with pytest.raises(
        TypeError,
    ):
        GroundedProviderCredentialSource()  # type: ignore[abstract]


def test_static_credential_source_returns_secret_without_serialization() -> None:
    source = StaticGroundedProviderCredentialSource(
        provider_identity="OPENAI",
        api_key="secret-value",
    )

    assert source.get_api_key(
        provider_identity="OPENAI"
    ) == "secret-value"

    assert not hasattr(
        source,
        "to_dict",
    )


def test_static_credential_source_rejects_other_provider() -> None:
    source = StaticGroundedProviderCredentialSource(
        provider_identity="OPENAI",
        api_key="secret-value",
    )

    with pytest.raises(
        KeyError,
        match="No credential configured",
    ):
        source.get_api_key(
            provider_identity="OTHER"
        )


def test_contract_imports_no_provider_sdk_or_network_client() -> None:
    import investment_terminal.ai.providers.contracts as module

    names = {
        name.lower()
        for name in module.__dict__
    }

    forbidden = (
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "aiohttp",
    )
    assert not any(
        item in names
        for item in forbidden
    )
