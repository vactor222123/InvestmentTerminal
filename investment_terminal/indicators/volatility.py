"""
Volatility technical indicators.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from investment_terminal.indicators.indicator_utils import (
    close_series,
    ohlc_frame,
    series_to_optional_list,
    validate_period,
)
from investment_terminal.models.candle import Candle


@dataclass(frozen=True, slots=True)
class BollingerBandsResult:
    """
    Full Bollinger Bands series.
    """

    middle: list[float | None]
    upper: list[float | None]
    lower: list[float | None]
    bandwidth_percent: list[float | None]


class VolatilityIndicators:
    """
    Calculate volatility indicators.
    """

    @staticmethod
    def atr(
        candles: Sequence[Candle],
        period: int = 14,
    ) -> list[float | None]:
        """
        Calculate Average True Range using Wilder smoothing.
        """
        frame = ohlc_frame(candles)
        validate_period(period)

        previous_close = frame["close"].shift(1)

        high_low = frame["high"] - frame["low"]
        high_previous_close = (
            frame["high"] - previous_close
        ).abs()
        low_previous_close = (
            frame["low"] - previous_close
        ).abs()

        true_range = frame[
            ["high", "low"]
        ].copy()

        true_range["high_low"] = high_low
        true_range["high_previous_close"] = (
            high_previous_close
        )
        true_range["low_previous_close"] = (
            low_previous_close
        )

        true_range_series = true_range[
            [
                "high_low",
                "high_previous_close",
                "low_previous_close",
            ]
        ].max(axis=1)

        result = true_range_series.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period,
        ).mean()

        return series_to_optional_list(result)

    @staticmethod
    def bollinger_bands(
        candles: Sequence[Candle],
        period: int = 20,
        standard_deviations: float = 2.0,
    ) -> BollingerBandsResult:
        """
        Calculate Bollinger Bands and percentage bandwidth.
        """
        closes = close_series(candles)
        validate_period(period)

        if (
            isinstance(standard_deviations, bool)
            or not isinstance(
                standard_deviations,
                (int, float),
            )
            or standard_deviations <= 0
        ):
            raise ValueError(
                "standard_deviations must be "
                "a positive number"
            )

        middle = closes.rolling(
            window=period,
            min_periods=period,
        ).mean()

        deviation = closes.rolling(
            window=period,
            min_periods=period,
        ).std(ddof=0)

        upper = (
            middle
            + deviation * float(standard_deviations)
        )
        lower = (
            middle
            - deviation * float(standard_deviations)
        )

        bandwidth_percent = (
            (upper - lower) / middle * 100.0
        )

        return BollingerBandsResult(
            middle=series_to_optional_list(middle),
            upper=series_to_optional_list(upper),
            lower=series_to_optional_list(lower),
            bandwidth_percent=series_to_optional_list(
                bandwidth_percent
            ),
        )