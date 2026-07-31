"""
Tests for the Finnhub API client.
"""

from unittest.mock import Mock

import pytest
import requests

from investment_terminal.clients.finnhub_client import FinnhubClient
from investment_terminal.utils.exceptions import APIError, ConfigurationError
from datetime import datetime, timezone

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

def test_get_quote_returns_quote_model() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "c": 412.75,
        "t": 1_700_000_000,
    }

    session.get.return_value = response

    quote = client.get_quote(" msft ")

    assert quote.symbol == "MSFT"
    assert quote.price == 412.75
    assert quote.currency == "USD"
    assert quote.timestamp is not None
    assert quote.timestamp.tzinfo is not None


def test_get_quote_accepts_explicit_currency() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "c": 210.50,
        "t": 1_700_000_000,
    }

    session.get.return_value = response

    quote = client.get_quote(
        symbol="SAP.DE",
        currency="EUR",
    )

    assert quote.symbol == "SAP.DE"
    assert quote.currency == "EUR"


def test_get_quote_rejects_empty_symbol() -> None:
    client, _ = create_client_with_mock_session()

    with pytest.raises(ValueError, match="symbol"):
        client.get_quote("   ")


def test_get_quote_rejects_missing_price() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "t": 1_700_000_000,
    }

    session.get.return_value = response

    with pytest.raises(APIError, match="current price"):
        client.get_quote("MSFT")


def test_get_quote_rejects_zero_price() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "c": 0,
        "t": 1_700_000_000,
    }

    session.get.return_value = response

    with pytest.raises(APIError, match="greater than zero"):
        client.get_quote("MSFT")


def test_get_quote_rejects_invalid_timestamp() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "c": 412.75,
        "t": 0,
    }

    session.get.return_value = response

    with pytest.raises(APIError, match="timestamp"):
        client.get_quote("MSFT")

def test_get_candles_returns_candle_models() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "s": "ok",
        "o": [100.0, 101.0],
        "h": [105.0, 106.0],
        "l": [98.0, 99.0],
        "c": [103.0, 104.0],
        "v": [1_000_000, 1_100_000],
        "t": [1_700_000_000, 1_700_086_400],
    }

    session.get.return_value = response

    start = datetime(
        2023,
        11,
        14,
        tzinfo=timezone.utc,
    )
    end = datetime(
        2023,
        11,
        17,
        tzinfo=timezone.utc,
    )

    candles = client.get_candles(
        symbol="msft",
        resolution="d",
        start=start,
        end=end,
    )

    assert len(candles) == 2
    assert candles[0].symbol == "MSFT"
    assert candles[0].resolution == "D"
    assert candles[0].open_price == 100.0
    assert candles[0].close_price == 103.0
    assert candles[0].currency == "USD"


def test_get_candles_returns_empty_list_for_no_data() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "s": "no_data",
    }

    session.get.return_value = response

    start = datetime(
        2023,
        1,
        1,
        tzinfo=timezone.utc,
    )
    end = datetime(
        2023,
        1,
        2,
        tzinfo=timezone.utc,
    )

    assert client.get_candles(
        symbol="MSFT",
        resolution="D",
        start=start,
        end=end,
    ) == []


def test_get_candles_rejects_inconsistent_array_lengths() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "s": "ok",
        "o": [100.0],
        "h": [105.0],
        "l": [98.0],
        "c": [103.0, 104.0],
        "v": [1_000_000],
        "t": [1_700_000_000],
    }

    session.get.return_value = response

    start = datetime(
        2023,
        1,
        1,
        tzinfo=timezone.utc,
    )
    end = datetime(
        2023,
        1,
        2,
        tzinfo=timezone.utc,
    )

    with pytest.raises(APIError, match="inconsistent lengths"):
        client.get_candles(
            symbol="MSFT",
            resolution="D",
            start=start,
            end=end,
        )


def test_get_candles_rejects_missing_field() -> None:
    client, session = create_client_with_mock_session()

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "s": "ok",
        "o": [100.0],
        "h": [105.0],
        "l": [98.0],
        "c": [103.0],
        "t": [1_700_000_000],
    }

    session.get.return_value = response

    start = datetime(
        2023,
        1,
        1,
        tzinfo=timezone.utc,
    )
    end = datetime(
        2023,
        1,
        2,
        tzinfo=timezone.utc,
    )

    with pytest.raises(APIError, match="missing 'v'"):
        client.get_candles(
            symbol="MSFT",
            resolution="D",
            start=start,
            end=end,
        )


def test_get_candles_rejects_invalid_date_range() -> None:
    client, _ = create_client_with_mock_session()

    moment = datetime(
        2023,
        1,
        1,
        tzinfo=timezone.utc,
    )

    with pytest.raises(ValueError, match="earlier"):
        client.get_candles(
            symbol="MSFT",
            resolution="D",
            start=moment,
            end=moment,
        )