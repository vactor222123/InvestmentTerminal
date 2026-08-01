"""
Momentum technical indicators.
"""

from collections.abc import Sequence

from investment_terminal.indicators.indicator_utils import (
    close_series,
    series_to_optional_list,
    validate_period,
)
from investment_terminal.models.candle import Candle


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

        relative_strength = (
            average_gain / average_loss
        )

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