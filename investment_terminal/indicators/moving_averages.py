"""
Moving-average technical indicators.
"""

from collections.abc import Sequence

from investment_terminal.indicators.indicator_utils import (
    close_series,
    series_to_optional_list,
    validate_period,
)
from investment_terminal.models.candle import Candle


class MovingAverages:
    """
    Calculate moving averages from ordered candles.
    """

    @staticmethod
    def sma(
        candles: Sequence[Candle],
        period: int,
    ) -> list[float | None]:
        """
        Calculate a simple moving average of closing prices.
        """
        closes = close_series(candles)
        validate_period(period)

        result = closes.rolling(
            window=period,
            min_periods=period,
        ).mean()

        return series_to_optional_list(result)

    @staticmethod
    def ema(
        candles: Sequence[Candle],
        period: int,
    ) -> list[float | None]:
        """
        Calculate an exponential moving average.
        """
        closes = close_series(candles)
        validate_period(period)

        result = closes.ewm(
            span=period,
            adjust=False,
            min_periods=period,
        ).mean()

        return series_to_optional_list(result)