"""
Momentum technical indicators.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from investment_terminal.indicators.indicator_utils import (
    close_series,
    series_to_optional_list,
    validate_period,
)
from investment_terminal.models.candle import Candle


@dataclass(frozen=True, slots=True)
class MACDResult:
    """
    Full MACD series.
    """

    macd_line: list[float | None]
    signal_line: list[float | None]
    histogram: list[float | None]


class MomentumIndicators:
    """
    Calculate momentum indicators from ordered candles.
    """

    @staticmethod
    def rsi(
        candles: Sequence[Candle],
        period: int = 14,
    ) -> list[float | None]:
        """
        Calculate RSI using Wilder smoothing.
        """
        closes = close_series(candles)
        validate_period(period)

        changes = closes.diff()

        gains = changes.clip(lower=0.0)
        losses = -changes.clip(upper=0.0)

        average_gain = gains.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period,
        ).mean()

        average_loss = losses.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period,
        ).mean()

        relative_strength = average_gain / average_loss

        result = 100.0 - (
            100.0 / (1.0 + relative_strength)
        )

        both_zero = (
            average_gain.eq(0.0)
            & average_loss.eq(0.0)
        )
        only_loss_zero = (
            average_gain.gt(0.0)
            & average_loss.eq(0.0)
        )

        result = result.mask(
            both_zero,
            50.0,
        )
        result = result.mask(
            only_loss_zero,
            100.0,
        )

        return series_to_optional_list(result)

    @staticmethod
    def macd(
        candles: Sequence[Candle],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> MACDResult:
        """
        Calculate MACD, signal line and histogram.
        """
        closes = close_series(candles)

        validate_period(fast_period)
        validate_period(slow_period)
        validate_period(signal_period)

        if fast_period >= slow_period:
            raise ValueError(
                "fast_period must be smaller than slow_period"
            )

        fast_ema = closes.ewm(
            span=fast_period,
            adjust=False,
            min_periods=fast_period,
        ).mean()

        slow_ema = closes.ewm(
            span=slow_period,
            adjust=False,
            min_periods=slow_period,
        ).mean()

        macd_line = fast_ema - slow_ema

        signal_line = macd_line.ewm(
            span=signal_period,
            adjust=False,
            min_periods=signal_period,
        ).mean()

        histogram = macd_line - signal_line

        return MACDResult(
            macd_line=series_to_optional_list(
                macd_line
            ),
            signal_line=series_to_optional_list(
                signal_line
            ),
            histogram=series_to_optional_list(
                histogram
            ),
        )