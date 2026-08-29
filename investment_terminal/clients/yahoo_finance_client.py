"""
Yahoo Finance historical market-data client.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from numbers import Real
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf
from curl_cffi.requests.exceptions import RequestException, Timeout
from yfinance.exceptions import (
    YFException,
    YFInvalidPeriodError,
    YFPricesMissingError,
    YFRateLimitError,
    YFTickerMissingError,
    YFTzMissingError,
)

from investment_terminal.models.candle import Candle
from investment_terminal.utils.exceptions import APIError


class YahooCandleFailureCategory(str, Enum):
    """Stable privacy-safe categories for Yahoo candle failures."""

    RATE_LIMITED = "RATE_LIMITED"
    NO_PRICE_DATA = "NO_PRICE_DATA"
    INVALID_REQUEST = "INVALID_REQUEST"
    TIMEOUT = "TIMEOUT"
    TRANSPORT_FAILURE = "TRANSPORT_FAILURE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    RESPONSE_SHAPE = "RESPONSE_SHAPE"
    RESPONSE_TIMESTAMP = "RESPONSE_TIMESTAMP"
    RESPONSE_NUMERIC = "RESPONSE_NUMERIC"
    RESPONSE_OHLC = "RESPONSE_OHLC"
    CANDLE_SET_VALIDATION = "CANDLE_SET_VALIDATION"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    UNEXPECTED = "UNEXPECTED"


class YahooCandleInvalidResponseError(APIError):
    """API-compatible local validation error with a stable privacy-safe type."""

    def __init__(
        self,
        category: YahooCandleFailureCategory,
        message: str = "Yahoo candle response failed local validation",
    ) -> None:
        if category not in {
            YahooCandleFailureCategory.RESPONSE_SHAPE,
            YahooCandleFailureCategory.RESPONSE_TIMESTAMP,
            YahooCandleFailureCategory.RESPONSE_NUMERIC,
            YahooCandleFailureCategory.RESPONSE_OHLC,
            YahooCandleFailureCategory.CANDLE_SET_VALIDATION,
        }:
            raise ValueError("Invalid Yahoo candle response category")
        self.category = category
        super().__init__(message)


def classify_yahoo_candle_failure(error: BaseException) -> YahooCandleFailureCategory:
    """Classify a causal chain without inspecting or returning message text."""
    chain: list[BaseException] = []
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        current = current.__cause__ or current.__context__

    for item in chain:
        if isinstance(item, YahooCandleInvalidResponseError):
            return item.category

    if any(isinstance(item, YFRateLimitError) for item in chain):
        return YahooCandleFailureCategory.RATE_LIMITED
    if any(
        isinstance(
            item,
            (YFPricesMissingError, YFTzMissingError, YFTickerMissingError),
        )
        for item in chain
    ):
        return YahooCandleFailureCategory.NO_PRICE_DATA
    if any(isinstance(item, YFInvalidPeriodError) for item in chain):
        return YahooCandleFailureCategory.INVALID_REQUEST
    if any(isinstance(item, (TimeoutError, Timeout)) for item in chain):
        return YahooCandleFailureCategory.TIMEOUT
    if any(isinstance(item, RequestException) for item in chain):
        return YahooCandleFailureCategory.TRANSPORT_FAILURE
    if any(isinstance(item, YFException) for item in chain):
        return YahooCandleFailureCategory.PROVIDER_FAILURE
    if isinstance(error, APIError) and len(chain) == 1:
        return YahooCandleFailureCategory.INVALID_RESPONSE
    if isinstance(error, (TypeError, ValueError)):
        return YahooCandleFailureCategory.INVALID_RESPONSE
    return YahooCandleFailureCategory.UNEXPECTED


class YahooFinanceClient:
    """
    Download historical OHLCV candles through yfinance.
    """

    RESOLUTION_MAP = {
        "D": "1d",
        "W": "1wk",
        "M": "1mo",
    }

    def __init__(
        self,
        ticker_factory: Callable[[str], Any] | None = None,
        *,
        cache_directory: str | Path | None = None,
        cache_location_setter: Callable[[str], None] | None = None,
    ) -> None:
        """
        Create the client.

        ticker_factory is injectable so unit tests never use live data.
        A caller may explicitly place yfinance's operational cache in a
        writable runtime-owned directory.
        """
        self._ticker_factory = ticker_factory or yf.Ticker
        if cache_directory is not None:
            directory = Path(cache_directory)
            directory.mkdir(parents=True, exist_ok=True)
            if not directory.is_dir():
                raise ValueError("cache_directory must identify a directory")
            setter = cache_location_setter or yf.set_tz_cache_location
            setter(str(directory.resolve()))

    def get_candles(
        self,
        symbol: str,
        resolution: str,
        start: datetime,
        end: datetime,
        currency: str = "USD",
    ) -> list[Candle]:
        """
        Download historical OHLCV candles and convert them to models.
        """
        normalized_symbol = self._normalize_text(
            symbol,
            field_name="symbol",
        )
        normalized_resolution = self._normalize_text(
            resolution,
            field_name="resolution",
        )
        normalized_currency = self._normalize_text(
            currency,
            field_name="currency",
        )

        if not isinstance(start, datetime):
            raise TypeError("start must be a datetime")

        if not isinstance(end, datetime):
            raise TypeError("end must be a datetime")

        if start >= end:
            raise ValueError("start must be earlier than end")

        interval = self.RESOLUTION_MAP.get(
            normalized_resolution
        )

        if interval is None:
            supported = ", ".join(
                self.RESOLUTION_MAP
            )
            raise ValueError(
                "Unsupported Yahoo Finance resolution "
                f"'{normalized_resolution}'. "
                f"Supported values: {supported}."
            )

        try:
            ticker = self._ticker_factory(
                normalized_symbol
            )

            frame = ticker.history(
                start=start,
                end=end,
                interval=interval,
                auto_adjust=False,
                actions=False,
                repair=False,
                raise_errors=True,
            )
        except Exception as exc:
            raise APIError(
                "Yahoo Finance historical request failed "
                f"for {normalized_symbol}."
            ) from exc

        if not isinstance(frame, pd.DataFrame):
            raise YahooCandleInvalidResponseError(
                YahooCandleFailureCategory.RESPONSE_SHAPE,
                "Yahoo Finance returned an invalid data type.",
            )

        if frame.empty:
            return []

        required_columns = {
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        }

        missing_columns = (
            required_columns - set(frame.columns)
        )

        if missing_columns:
            missing = ", ".join(
                sorted(missing_columns)
            )
            raise YahooCandleInvalidResponseError(
                YahooCandleFailureCategory.RESPONSE_SHAPE,
                "Yahoo Finance response is missing columns: " + missing + ".",
            )

        candles: list[Candle] = []

        for index, row in frame.iterrows():
            timestamp = self._normalize_timestamp(
                index
            )

            open_price = self._require_positive_number(
                row["Open"],
                field_name="open price",
            )
            high_price = self._require_positive_number(
                row["High"],
                field_name="high price",
            )
            low_price = self._require_positive_number(
                row["Low"],
                field_name="low price",
            )
            close_price = self._require_positive_number(
                row["Close"],
                field_name="close price",
            )
            volume = self._require_non_negative_number(
                row["Volume"],
                field_name="volume",
            )

            if high_price < max(
                open_price,
                low_price,
                close_price,
            ):
                raise YahooCandleInvalidResponseError(
                    YahooCandleFailureCategory.RESPONSE_OHLC,
                    "Yahoo Finance candle high price is inconsistent.",
                )

            if low_price > min(
                open_price,
                high_price,
                close_price,
            ):
                raise YahooCandleInvalidResponseError(
                    YahooCandleFailureCategory.RESPONSE_OHLC,
                    "Yahoo Finance candle low price is inconsistent.",
                )

            candles.append(
                Candle(
                    symbol=normalized_symbol,
                    resolution=normalized_resolution,
                    timestamp=timestamp,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                    currency=normalized_currency,
                )
            )

        return candles

    @staticmethod
    def _normalize_timestamp(
        value: object,
    ) -> datetime:
        """
        Convert pandas index values to UTC datetime.
        """
        if isinstance(value, pd.Timestamp):
            timestamp = value.to_pydatetime()
        elif isinstance(value, datetime):
            timestamp = value
        else:
            raise YahooCandleInvalidResponseError(
                YahooCandleFailureCategory.RESPONSE_TIMESTAMP
            )

        if timestamp.tzinfo is None:
            return timestamp.replace(
                tzinfo=timezone.utc
            )

        return timestamp.astimezone(
            timezone.utc
        )

    @staticmethod
    def _require_positive_number(
        value: object,
        field_name: str,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
        ):
            raise YahooCandleInvalidResponseError(
                YahooCandleFailureCategory.RESPONSE_NUMERIC
            )

        numeric_value = float(value)

        if numeric_value <= 0:
            raise YahooCandleInvalidResponseError(
                YahooCandleFailureCategory.RESPONSE_NUMERIC
            )

        return numeric_value

    @staticmethod
    def _require_non_negative_number(
        value: object,
        field_name: str,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
        ):
            raise YahooCandleInvalidResponseError(
                YahooCandleFailureCategory.RESPONSE_NUMERIC
            )

        numeric_value = float(value)

        if numeric_value < 0:
            raise YahooCandleInvalidResponseError(
                YahooCandleFailureCategory.RESPONSE_NUMERIC
            )

        return numeric_value

    @staticmethod
    def _normalize_text(
        value: str,
        field_name: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} must be "
                "a non-empty string"
            )

        return value.strip().upper()
