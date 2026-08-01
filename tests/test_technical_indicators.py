"""
Tests for core technical indicators.
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

    candles: list[Candle] = []

    for index, close_price in enumerate(closes):
        candles.append(
            Candle(
                symbol="TEST",
                resolution="D",
                timestamp=start
                + timedelta(days=index),
                open_price=close_price,
                high_price=close_price + 1,
                low_price=close_price - 1,
                close_price=close_price,
                volume=1_000_000,
                currency="USD",
            )
        )

    return candles


def test_sma_returns_expected_values() -> None:
    candles = create_candles(
        [10, 20, 30, 40, 50]
    )

    result = TechnicalIndicators.sma(
        candles,
        period=3,
    )

    assert result == [
        None,
        None,
        20.0,
        30.0,
        40.0,
    ]


def test_ema_returns_values_after_warmup() -> None:
    candles = create_candles(
        [10, 20, 30, 40, 50]
    )

    result = TechnicalIndicators.ema(
        candles,
        period=3,
    )

    assert result[:2] == [None, None]
    assert result[2] == pytest.approx(22.5)
    assert result[3] == pytest.approx(31.25)
    assert result[4] == pytest.approx(40.625)


def test_rsi_reaches_100_for_continuous_gains() -> None:
    candles = create_candles(
        [
            100,
            101,
            102,
            103,
            104,
            105,
            106,
            107,
            108,
            109,
            110,
            111,
            112,
            113,
            114,
            115,
        ]
    )

    result = TechnicalIndicators.rsi(
        candles,
        period=14,
    )

    assert result[-1] == pytest.approx(100.0)


def test_rsi_reaches_zero_for_continuous_losses() -> None:
    candles = create_candles(
        [
            115,
            114,
            113,
            112,
            111,
            110,
            109,
            108,
            107,
            106,
            105,
            104,
            103,
            102,
            101,
            100,
        ]
    )

    result = TechnicalIndicators.rsi(
        candles,
        period=14,
    )

    assert result[-1] == pytest.approx(0.0)


def test_rsi_is_50_for_unchanged_prices() -> None:
    candles = create_candles(
        [100.0] * 16
    )

    result = TechnicalIndicators.rsi(
        candles,
        period=14,
    )

    assert result[-1] == pytest.approx(50.0)


def test_latest_returns_latest_available_value() -> None:
    assert TechnicalIndicators.latest(
        [None, None, 10.0, 12.5]
    ) == 12.5


def test_latest_returns_none_without_values() -> None:
    assert TechnicalIndicators.latest(
        [None, None]
    ) is None


@pytest.mark.parametrize(
    "period",
    [
        0,
        -1,
        1.5,
        True,
    ],
)
def test_indicators_reject_invalid_period(
    period,
) -> None:
    candles = create_candles(
        [10, 20, 30]
    )

    with pytest.raises(
        ValueError,
        match="period",
    ):
        TechnicalIndicators.sma(
            candles,
            period=period,
        )


def test_indicators_reject_empty_candles() -> None:
    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        TechnicalIndicators.sma(
            [],
            period=3,
        )


def test_indicators_reject_unordered_candles() -> None:
    candles = create_candles(
        [10, 20, 30]
    )
    candles[1], candles[2] = (
        candles[2],
        candles[1],
    )

    with pytest.raises(
        ValueError,
        match="ordered",
    ):
        TechnicalIndicators.sma(
            candles,
            period=2,
        )


def test_indicators_reject_invalid_close_price() -> None:
    candles = create_candles(
        [10, 20, 30]
    )
    candles[1].close_price = 0

    with pytest.raises(
        ValueError,
        match="close price",
    ):
        TechnicalIndicators.ema(
            candles,
            period=2,
        )