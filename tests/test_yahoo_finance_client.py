"""
Tests for YahooFinanceClient.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pandas as pd
import pytest

from investment_terminal.clients.yahoo_finance_client import (
    YahooFinanceClient,
)
from investment_terminal.utils.exceptions import APIError


def create_period() -> tuple[datetime, datetime]:
    return (
        datetime(
            2026,
            7,
            1,
            tzinfo=timezone.utc,
        ),
        datetime(
            2026,
            7,
            4,
            tzinfo=timezone.utc,
        ),
    )


def create_history_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0, 103.0],
            "High": [105.0, 108.0],
            "Low": [98.0, 101.0],
            "Close": [103.0, 106.0],
            "Volume": [1_000_000, 1_200_000],
        },
        index=pd.DatetimeIndex(
            [
                "2026-07-01T00:00:00Z",
                "2026-07-02T00:00:00Z",
            ]
        ),
    )


def test_get_candles_returns_candle_models() -> None:
    ticker = Mock()
    ticker.history.return_value = (
        create_history_frame()
    )

    ticker_factory = Mock(
        return_value=ticker
    )

    client = YahooFinanceClient(
        ticker_factory=ticker_factory
    )

    start, end = create_period()

    candles = client.get_candles(
        symbol=" msft ",
        resolution="d",
        start=start,
        end=end,
    )

    assert len(candles) == 2
    assert candles[0].symbol == "MSFT"
    assert candles[0].resolution == "D"
    assert candles[0].open_price == 100.0
    assert candles[0].high_price == 105.0
    assert candles[0].low_price == 98.0
    assert candles[0].close_price == 103.0
    assert candles[0].volume == 1_000_000
    assert candles[0].currency == "USD"
    assert candles[0].timestamp.tzinfo is not None

    ticker_factory.assert_called_once_with(
        "MSFT"
    )

    ticker.history.assert_called_once_with(
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        actions=False,
        repair=False,
        raise_errors=True,
    )


def test_get_candles_returns_empty_list() -> None:
    ticker = Mock()
    ticker.history.return_value = pd.DataFrame()

    client = YahooFinanceClient(
        ticker_factory=Mock(
            return_value=ticker
        )
    )

    start, end = create_period()

    assert client.get_candles(
        symbol="MSFT",
        resolution="D",
        start=start,
        end=end,
    ) == []


def test_get_candles_maps_weekly_resolution() -> None:
    ticker = Mock()
    ticker.history.return_value = pd.DataFrame()

    client = YahooFinanceClient(
        ticker_factory=Mock(
            return_value=ticker
        )
    )

    start, end = create_period()

    client.get_candles(
        symbol="MSFT",
        resolution="W",
        start=start,
        end=end,
    )

    assert (
        ticker.history.call_args.kwargs["interval"]
        == "1wk"
    )


def test_get_candles_rejects_resolution() -> None:
    client = YahooFinanceClient(
        ticker_factory=Mock()
    )

    start, end = create_period()

    with pytest.raises(
        ValueError,
        match="Unsupported",
    ):
        client.get_candles(
            symbol="MSFT",
            resolution="15",
            start=start,
            end=end,
        )


def test_get_candles_rejects_missing_column() -> None:
    frame = create_history_frame().drop(
        columns=["Volume"]
    )

    ticker = Mock()
    ticker.history.return_value = frame

    client = YahooFinanceClient(
        ticker_factory=Mock(
            return_value=ticker
        )
    )

    start, end = create_period()

    with pytest.raises(
        APIError,
        match="Volume",
    ):
        client.get_candles(
            symbol="MSFT",
            resolution="D",
            start=start,
            end=end,
        )


def test_get_candles_rejects_invalid_ohlc() -> None:
    frame = create_history_frame()
    frame.loc[
        frame.index[0],
        "High",
    ] = 50.0

    ticker = Mock()
    ticker.history.return_value = frame

    client = YahooFinanceClient(
        ticker_factory=Mock(
            return_value=ticker
        )
    )

    start, end = create_period()

    with pytest.raises(
        APIError,
        match="high price",
    ):
        client.get_candles(
            symbol="MSFT",
            resolution="D",
            start=start,
            end=end,
        )


def test_get_candles_converts_provider_error() -> None:
    ticker = Mock()
    ticker.history.side_effect = RuntimeError(
        "Provider failure"
    )

    client = YahooFinanceClient(
        ticker_factory=Mock(
            return_value=ticker
        )
    )

    start, end = create_period()

    with pytest.raises(
        APIError,
        match="historical request failed",
    ):
        client.get_candles(
            symbol="MSFT",
            resolution="D",
            start=start,
            end=end,
        )