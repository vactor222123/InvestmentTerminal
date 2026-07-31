"""
Tests for the Finnhub API client foundation.
"""

import pytest

from investment_terminal.clients.finnhub_client import FinnhubClient
from investment_terminal.utils.exceptions import ConfigurationError


def test_client_accepts_valid_configuration() -> None:
    client = FinnhubClient(
        api_key="test-key",
        timeout=5.0,
    )

    assert client.api_key == "test-key"
    assert client.timeout == 5.0
    assert client.base_url == "https://finnhub.io/api/v1"


def test_client_rejects_empty_api_key() -> None:
    with pytest.raises(ConfigurationError):
        FinnhubClient(api_key="   ")


def test_client_rejects_invalid_timeout() -> None:
    with pytest.raises(ConfigurationError):
        FinnhubClient(
            api_key="test-key",
            timeout=0,
        )


def test_client_builds_normalized_url() -> None:
    client = FinnhubClient(api_key="test-key")

    assert (
        client.build_url("/quote")
        == "https://finnhub.io/api/v1/quote"
    )


def test_client_rejects_empty_endpoint() -> None:
    client = FinnhubClient(api_key="test-key")

    with pytest.raises(ValueError):
        client.build_url("   ")