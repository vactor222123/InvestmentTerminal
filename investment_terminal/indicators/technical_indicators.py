"""
Core technical-indicator calculations.
"""

from collections.abc import Sequence
from math import isfinite
from numbers import Real

import pandas as pd

from investment_terminal.models.candle import Candle


class TechnicalIndicators:
    """
    Calculate technical indicators from ordered market candles.

    Returned lists have the same length as the input candles.
    Values that cannot yet be calculated are represented by None.
    """

    @classmethod
    def sma(
        cls,
        candles: Sequence[Candle],
        period: int,
    ) -> list[float | None]:
        """
        Calculate a simple moving average of closing prices.
        """
        closes = cls._close_series(candles)
        cls._validate_period(period)

        result = closes.rolling(
            window=period,
            min_periods=period,
        ).mean()

        return cls._series_to_optional_list(result)

    @classmethod
    def ema(
        cls,
        candles: Sequence[Candle],
        period: int,
    ) -> list[float | None]:
        """
        Calculate an exponential moving average of closing prices.

        The first value is emitted only after `period` observations.
        """
        closes = cls._close_series(candles)
        cls._validate_period(period)

        result = closes.ewm(
            span=period,
            adjust=False,
            min_periods=period,
        ).mean()

        return cls._series_to_optional_list(result)

    @classmethod
    def rsi(
        cls,
        candles: Sequence[Candle],
        period: int = 14,
    ) -> list[float | None]:
        """
        Calculate Relative Strength Index using Wilder smoothing.
        """
        closes = cls._close_series(candles)
        cls._validate_period(period)

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

        return cls._series_to_optional_list(result)

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

    @classmethod
    def _close_series(
        cls,
        candles: Sequence[Candle],
    ) -> pd.Series:
        """
        Validate candles and return ordered closing prices.
        """
        if isinstance(candles, (str, bytes)):
            raise TypeError(
                "candles must be a sequence of Candle objects"
            )

        candle_list = list(candles)

        if not candle_list:
            raise ValueError(
                "candles must not be empty"
            )

        closes: list[float] = []

        previous_timestamp = None

        for candle in candle_list:
            if not isinstance(candle, Candle):
                raise TypeError(
                    "candles must contain only Candle objects"
                )

            if candle.timestamp is None:
                raise ValueError(
                    "every candle must have a timestamp"
                )

            if (
                previous_timestamp is not None
                and candle.timestamp <= previous_timestamp
            ):
                raise ValueError(
                    "candles must be ordered by ascending timestamp"
                )

            previous_timestamp = candle.timestamp

            close_price = candle.close_price

            if (
                isinstance(close_price, bool)
                or not isinstance(close_price, Real)
                or not isfinite(float(close_price))
                or float(close_price) <= 0
            ):
                raise ValueError(
                    "every close price must be a positive finite number"
                )

            closes.append(float(close_price))

        return pd.Series(
            closes,
            dtype="float64",
        )

    @staticmethod
    def _validate_period(period: int) -> None:
        if (
            isinstance(period, bool)
            or not isinstance(period, int)
            or period <= 0
        ):
            raise ValueError(
                "period must be a positive integer"
            )

    @staticmethod
    def _series_to_optional_list(
        series: pd.Series,
    ) -> list[float | None]:
        """
        Convert a pandas Series to plain Python values.
        """
        return [
            None if pd.isna(value) else float(value)
            for value in series
        ]