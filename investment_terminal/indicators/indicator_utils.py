"""
Shared validation and conversion utilities for technical indicators.
"""

from collections.abc import Sequence
from math import isfinite
from numbers import Real

import pandas as pd

from investment_terminal.models.candle import Candle


def close_series(
    candles: Sequence[Candle],
) -> pd.Series:
    """
    Validate ordered candles and return closing prices.
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


def validate_period(period: int) -> None:
    """
    Validate an indicator lookback period.
    """
    if (
        isinstance(period, bool)
        or not isinstance(period, int)
        or period <= 0
    ):
        raise ValueError(
            "period must be a positive integer"
        )


def series_to_optional_list(
    series: pd.Series,
) -> list[float | None]:
    """
    Convert a pandas Series to plain Python values.
    """
    return [
        None if pd.isna(value) else float(value)
        for value in series
    ]