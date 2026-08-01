"""
Tests for MACD, ATR and Bollinger Bands.
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.indicators.technical_indicators import (
    TechnicalIndicators,
)
from investment_terminal.models.candle import Candle


def create_candles(
    closes: list[float],
) -> list[Candle]:
    start = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    return [
        Candle(
            symbol="TEST",
            resolution="D",
            timestamp=start + timedelta(days=index),
            open_price=close_price,
            high_price=close_price + 2.0,
            low_price=close_price - 2.0,
            close_price=close_price,
            volume=1_000_000,
            currency="USD",
        )
        for index, close_price in enumerate(closes)
    ]


def test_macd_returns_aligned_series() -> None:
    candles = create_candles(
        [float(value) for value in range(1, 61)]
    )

    result = TechnicalIndicators.macd(candles)

    assert len(result.macd_line) == 60
    assert len(result.signal_line) == 60
    assert len(result.histogram) == 60

    assert result.macd_line[-1] is not None
    assert result.signal_line[-1] is not None
    assert result.histogram[-1] is not None


def test_macd_histogram_matches_difference() -> None:
    candles = create_candles(
        [float(value) for value in range(1, 61)]
    )

    result = TechnicalIndicators.macd(candles)

    assert result.histogram[-1] == pytest.approx(
        result.macd_line[-1]
        - result.signal_line[-1]
    )


def test_macd_rejects_invalid_period_order() -> None:
    candles = create_candles(
        [float(value) for value in range(1, 40)]
    )

    with pytest.raises(
        ValueError,
        match="fast_period",
    ):
        TechnicalIndicators.macd(
            candles,
            fast_period=26,
            slow_period=12,
        )


def test_atr_returns_expected_constant_range() -> None:
    candles = create_candles(
        [100.0] * 20
    )

    result = TechnicalIndicators.atr(
        candles,
        period=14,
    )

    assert result[-1] == pytest.approx(4.0)


def test_atr_handles_price_gap() -> None:
    candles = create_candles(
        [100.0] * 14 + [120.0]
    )

    result = TechnicalIndicators.atr(
        candles,
        period=14,
    )

    assert result[-1] is not None
    assert result[-1] > 4.0


def test_bollinger_middle_matches_sma() -> None:
    candles = create_candles(
        [float(value) for value in range(1, 31)]
    )

    bands = TechnicalIndicators.bollinger_bands(
        candles,
        period=20,
    )
    sma = TechnicalIndicators.sma(
        candles,
        period=20,
    )

    assert bands.middle == sma


def test_bollinger_bands_are_ordered() -> None:
    candles = create_candles(
        [float(value) for value in range(1, 31)]
    )

    bands = TechnicalIndicators.bollinger_bands(
        candles,
        period=20,
    )

    assert bands.lower[-1] < bands.middle[-1]
    assert bands.middle[-1] < bands.upper[-1]
    assert bands.bandwidth_percent[-1] > 0


def test_bollinger_flat_prices_have_zero_width() -> None:
    candles = create_candles(
        [100.0] * 25
    )

    bands = TechnicalIndicators.bollinger_bands(
        candles,
        period=20,
    )

    assert bands.upper[-1] == pytest.approx(100.0)
    assert bands.middle[-1] == pytest.approx(100.0)
    assert bands.lower[-1] == pytest.approx(100.0)
    assert bands.bandwidth_percent[-1] == pytest.approx(
        0.0
    )


def test_bollinger_rejects_invalid_deviation() -> None:
    candles = create_candles(
        [100.0] * 25
    )

    with pytest.raises(
        ValueError,
        match="standard_deviations",
    ):
        TechnicalIndicators.bollinger_bands(
            candles,
            standard_deviations=0,
        )