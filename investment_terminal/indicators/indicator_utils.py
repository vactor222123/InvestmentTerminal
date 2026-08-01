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
    
def ohlc_frame(
    candles: Sequence[Candle],
) -> pd.DataFrame:
    """
    Validate candles and return OHLC data.
    """
    candle_list = list(candles)
    closes = close_series(candle_list)

    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []

    for candle in candle_list:
        numeric_values = {
            "open price": candle.open_price,
            "high price": candle.high_price,
            "low price": candle.low_price,
        }

        validated: dict[str, float] = {}

        for field_name, value in numeric_values.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not isfinite(float(value))
                or float(value) <= 0
            ):
                raise ValueError(
                    f"every {field_name} must be "
                    "a positive finite number"
                )

            validated[field_name] = float(value)

        open_price = validated["open price"]
        high_price = validated["high price"]
        low_price = validated["low price"]
        close_price = float(candle.close_price)

        if high_price < max(
            open_price,
            low_price,
            close_price,
        ):
            raise ValueError(
                "high price must be the highest OHLC value"
            )

        if low_price > min(
            open_price,
            high_price,
            close_price,
        ):
            raise ValueError(
                "low price must be the lowest OHLC value"
            )

        opens.append(open_price)
        highs.append(high_price)
        lows.append(low_price)

    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
        },
        dtype="float64",
    )