"""
Tests for TechnicalAnalysisService.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from investment_terminal.models.candle import Candle
from investment_terminal.services.technical_analysis_service import (
    TechnicalAnalysisService,
)


def create_candles(
    count: int,
    start_price: float = 100.0,
    daily_change: float = 1.0,
) -> list[Candle]:
    start = datetime(
        2025,
        1,
        1,
        tzinfo=timezone.utc,
    )

    candles: list[Candle] = []

    for index in range(count):
        close_price = (
            start_price
            + daily_change * index
        )

        candles.append(
            Candle(
                symbol="MSFT",
                resolution="D",
                timestamp=(
                    start
                    + timedelta(days=index)
                ),
                open_price=close_price,
                high_price=close_price + 1.0,
                low_price=close_price - 1.0,
                close_price=close_price,
                volume=1_000_000 + index,
                currency="USD",
            )
        )

    return candles


def test_analyze_returns_complete_snapshot() -> None:
    candles = create_candles(
        count=250,
        daily_change=1.0,
    )

    repository = Mock()
    repository.get_range.return_value = candles

    service = TechnicalAnalysisService(
        repository=repository
    )

    result = service.analyze(
        symbol=" msft ",
        resolution="d",
    )

    assert result.symbol == "MSFT"
    assert result.resolution == "D"
    assert result.latest_price == 349.0
    assert result.currency == "USD"

    assert result.sma20 is not None
    assert result.sma50 is not None
    assert result.sma200 is not None
    assert result.ema20 is not None
    assert result.rsi14 is not None

    assert result.price_above_sma20 is True
    assert result.price_above_sma50 is True
    assert result.price_above_sma200 is True
    assert result.sma50_above_sma200 is True

    assert result.trend == "STRONG_UPTREND"

    assert (
        result.data_quality.candle_count
        == 250
    )
    assert (
        result.data_quality.completeness_percent
        == 100.0
    )
    assert (
        result.data_quality.missing_indicators
        == ()
    )
    assert (
        result.data_quality.sufficient_for_long_term
        is True
    )

    repository.get_range.assert_called_once_with(
        symbol="MSFT",
        resolution="D",
    )


def test_analyze_reports_incomplete_data() -> None:
    candles = create_candles(
        count=30,
    )

    repository = Mock()
    repository.get_range.return_value = candles

    service = TechnicalAnalysisService(
        repository=repository
    )

    result = service.analyze("MSFT")

    assert result.sma20 is not None
    assert result.sma50 is None
    assert result.sma200 is None
    assert result.ema20 is not None
    assert result.rsi14 is not None

    assert result.trend == "INSUFFICIENT_DATA"

    assert (
        result.data_quality.completeness_percent
        == 15.0
    )
    assert (
        result.data_quality.missing_indicators
        == ("sma50", "sma200")
    )
    assert (
        result.data_quality.sufficient_for_long_term
        is False
    )


def test_analyze_classifies_strong_downtrend() -> None:
    candles = create_candles(
        count=250,
        start_price=400.0,
        daily_change=-1.0,
    )

    repository = Mock()
    repository.get_range.return_value = candles

    service = TechnicalAnalysisService(
        repository=repository
    )

    result = service.analyze("MSFT")

    assert result.trend == "STRONG_DOWNTREND"
    assert result.price_above_sma200 is False
    assert result.sma50_above_sma200 is False


def test_analyze_rejects_missing_candles() -> None:
    repository = Mock()
    repository.get_range.return_value = []

    service = TechnicalAnalysisService(
        repository=repository
    )

    with pytest.raises(
        ValueError,
        match="No candles",
    ):
        service.analyze("MSFT")


@pytest.mark.parametrize(
    "symbol",
    [
        "",
        "   ",
        None,
    ],
)
def test_analyze_rejects_invalid_symbol(
    symbol,
) -> None:
    service = TechnicalAnalysisService(
        repository=Mock()
    )

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        service.analyze(symbol)


def test_analyze_returns_latest_timestamp() -> None:
    candles = create_candles(
        count=250,
    )

    repository = Mock()
    repository.get_range.return_value = candles

    result = TechnicalAnalysisService(
        repository=repository
    ).analyze("MSFT")

    assert result.timestamp == candles[-1].timestamp