"""
Tests for the specialized indicator modules.
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.indicators.momentum import (
    MomentumIndicators,
)
from investment_terminal.indicators.moving_averages import (
    MovingAverages,
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
            high_price=close_price + 1.0,
            low_price=close_price - 1.0,
            close_price=close_price,
            volume=1_000_000,
            currency="USD",
        )
        for index, close_price in enumerate(closes)
    ]


def test_moving_averages_sma() -> None:
    candles = create_candles(
        [10, 20, 30, 40, 50]
    )

    assert MovingAverages.sma(
        candles,
        period=3,
    ) == [
        None,
        None,
        20.0,
        30.0,
        40.0,
    ]


def test_moving_averages_ema() -> None:
    candles = create_candles(
        [10, 20, 30, 40, 50]
    )

    result = MovingAverages.ema(
        candles,
        period=3,
    )

    assert result[-1] == pytest.approx(
        40.625
    )


def test_momentum_rsi() -> None:
    candles = create_candles(
        [float(value) for value in range(100, 116)]
    )

    result = MomentumIndicators.rsi(
        candles,
        period=14,
    )

    assert result[-1] == pytest.approx(
        100.0
    )