"""Narrow Yahoo adapter for privacy-safe raw candle diagnostics."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from investment_terminal.utils.exceptions import APIError


class YahooRawCandleDiagnosticClient:
    """Fetch one unconverted daily frame for bounded operational diagnosis."""

    def __init__(
        self,
        ticker_factory: Callable[[str], Any] | None = None,
        *,
        cache_directory: str | Path | None = None,
        cache_location_setter: Callable[[str], None] | None = None,
    ) -> None:
        self._ticker_factory = ticker_factory or yf.Ticker
        if cache_directory is not None:
            directory = Path(cache_directory)
            directory.mkdir(parents=True, exist_ok=True)
            if not directory.is_dir():
                raise ValueError("cache_directory must identify a directory")
            setter = cache_location_setter or yf.set_tz_cache_location
            setter(str(directory.resolve()))

    def get_daily_frame(
        self,
        *,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Return the exact raw frame used by the production Yahoo request."""
        try:
            frame = self._ticker_factory(symbol).history(
                start=start,
                end=end,
                interval="1d",
                auto_adjust=False,
                actions=False,
                repair=False,
                raise_errors=True,
            )
        except Exception as exc:
            raise APIError("Yahoo raw candle diagnostic request failed") from exc
        if not isinstance(frame, pd.DataFrame):
            raise ValueError("Yahoo raw candle diagnostic returned an invalid data type")
        return frame
