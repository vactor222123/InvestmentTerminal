"""
Yahoo Finance historical market-data client.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from math import isfinite
from numbers import Real
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from investment_terminal.models.candle import Candle
from investment_terminal.utils.exceptions import APIError


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
            raise APIError(
                "Yahoo Finance returned an invalid data type."
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
            raise APIError(
                "Yahoo Finance response is missing columns: "
                f"{missing}."
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
                raise APIError(
                    "Yahoo Finance candle high price "
                    "is inconsistent."
                )

            if low_price > min(
                open_price,
                high_price,
                close_price,
            ):
                raise APIError(
                    "Yahoo Finance candle low price "
                    "is inconsistent."
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
            raise APIError(
                "Yahoo Finance returned an invalid timestamp."
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
            raise APIError(
                f"Yahoo Finance {field_name} "
                "must be a finite number."
            )

        numeric_value = float(value)

        if numeric_value <= 0:
            raise APIError(
                f"Yahoo Finance {field_name} "
                "must be greater than zero."
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
            raise APIError(
                f"Yahoo Finance {field_name} "
                "must be a finite number."
            )

        numeric_value = float(value)

        if numeric_value < 0:
            raise APIError(
                f"Yahoo Finance {field_name} "
                "must not be negative."
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
