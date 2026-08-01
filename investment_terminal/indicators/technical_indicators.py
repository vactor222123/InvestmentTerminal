"""
Public facade for technical-indicator calculations.
"""

from collections.abc import Sequence

from investment_terminal.indicators.momentum import (
    MACDResult,
    MomentumIndicators,
)
from investment_terminal.indicators.moving_averages import (
    MovingAverages,
)
from investment_terminal.indicators.volatility import (
    BollingerBandsResult,
    VolatilityIndicators,
)
from investment_terminal.models.candle import Candle


class TechnicalIndicators:
    """
    Stable public facade for technical indicators.

    Services should use this facade rather than depending directly
    on individual indicator modules.
    """

    @staticmethod
    def sma(
        candles: Sequence[Candle],
        period: int,
    ) -> list[float | None]:
        """
        Calculate a simple moving average.
        """
        return MovingAverages.sma(
            candles=candles,
            period=period,
        )

    @staticmethod
    def ema(
        candles: Sequence[Candle],
        period: int,
    ) -> list[float | None]:
        """
        Calculate an exponential moving average.
        """
        return MovingAverages.ema(
            candles=candles,
            period=period,
        )

    @staticmethod
    def rsi(
        candles: Sequence[Candle],
        period: int = 14,
    ) -> list[float | None]:
        """
        Calculate Relative Strength Index.
        """
        return MomentumIndicators.rsi(
            candles=candles,
            period=period,
        )

    @staticmethod
    def macd(
        candles: Sequence[Candle],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> MACDResult:
        """
        Calculate MACD.
        """
        return MomentumIndicators.macd(
            candles=candles,
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
        )

    @staticmethod
    def atr(
        candles: Sequence[Candle],
        period: int = 14,
    ) -> list[float | None]:
        """
        Calculate Average True Range.
        """
        return VolatilityIndicators.atr(
            candles=candles,
            period=period,
        )

    @staticmethod
    def bollinger_bands(
        candles: Sequence[Candle],
        period: int = 20,
        standard_deviations: float = 2.0,
    ) -> BollingerBandsResult:
        """
        Calculate Bollinger Bands.
        """
        return VolatilityIndicators.bollinger_bands(
            candles=candles,
            period=period,
            standard_deviations=standard_deviations,
        )

    @staticmethod
    def latest(
        values: Sequence[float | None],
    ) -> float | None:
        """
        Return the latest available indicator value.
        """
        for value in reversed(values):
            if value is not None:
                return value

        return None