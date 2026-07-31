"""
Tests for the Finnhub API client.
"""

from unittest.mock import Mock

import pytest
import requests

from investment_terminal.clients.finnhub_client import FinnhubClient
from investment_terminal.utils.exceptions import APIError, ConfigurationError


def create_client_with_mock_session() -> tuple[FinnhubClient, Mock]:
    """
    Create a Finnhub client with a mocked HTTP session.
    """
    session = Mock(spec=requests.Session)

    client = FinnhubClient(
        api_key="test-key",
        timeout=5.0,
        session=session,
    )

    return client, session


def test_client_accepts_valid_configuration() -> None:
    client = FinnhubClient(
        api_key="test-key",
        timeout=5.0,
    )

    assert client.api_key == "test-key"
    assert client.timeout == 5.0
    assert client.base_url == "https://finnhub.io/api/v1"

    client.close()


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

    client.close()


def test_client_rejects_empty_endpoint() -> None:
    client = FinnhubClient(api_key="test-key")

    with pytest.raises(ValueError):
        client.build_url("   ")

    client.close()


def test_get_json_returns_dictionary() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "c": 100.0,
        "t": 1234567890,
    }

    session.get.return_value = response

    result = client.get_json(
        "/quote",
        params={"symbol": "MSFT"},
    )

    assert result == {
        "c": 100.0,
        "t": 1234567890,
    }

    session.get.assert_called_once_with(
        "https://finnhub.io/api/v1/quote",
        params={
            "symbol": "MSFT",
            "token": "test-key",
        },
        timeout=5.0,
    )


def test_get_json_converts_timeout_to_api_error() -> None:
    client, session = create_client_with_mock_session()

    session.get.side_effect = requests.Timeout()

    with pytest.raises(APIError, match="timed out"):
        client.get_json(
            "/quote",
            params={"symbol": "MSFT"},
        )


def test_get_json_converts_connection_error() -> None:
    client, session = create_client_with_mock_session()

    session.get.side_effect = requests.ConnectionError()

    with pytest.raises(APIError, match="connect"):
        client.get_json(
            "/quote",
            params={"symbol": "MSFT"},
        )


def test_get_json_converts_http_error() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.status_code = 401

    http_error = requests.HTTPError(response=response)

    session.get.return_value = response
    response.raise_for_status.side_effect = http_error

    with pytest.raises(APIError, match="401"):
        client.get_json(
            "/quote",
            params={"symbol": "MSFT"},
        )


def test_get_json_rejects_invalid_json() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("Invalid JSON")

    session.get.return_value = response

    with pytest.raises(APIError, match="invalid JSON"):
        client.get_json(
            "/quote",
            params={"symbol": "MSFT"},
        )


def test_get_json_rejects_non_object_payload() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = ["unexpected", "list"]

    session.get.return_value = response

    with pytest.raises(APIError, match="JSON object"):
        client.get_json(
            "/quote",
            params={"symbol": "MSFT"},
        )


def test_get_json_rejects_api_error_payload() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "error": "Invalid API key",
    }

    session.get.return_value = response

    with pytest.raises(APIError, match="Invalid API key"):
        client.get_json(
            "/quote",
            params={"symbol": "MSFT"},
        )


def test_context_manager_closes_session() -> None:
    session = Mock(spec=requests.Session)

    with FinnhubClient(
        api_key="test-key",
        session=session,
    ) as client:
        assert client.api_key == "test-key"

    session.close.assert_called_once()