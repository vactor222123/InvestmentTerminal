"""Explicit yfinance repaired-frame adapter for one-series qualification."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

from investment_terminal.utils.exceptions import APIError
from investment_terminal.utils.validation import normalize_required_text


@dataclass(frozen=True, slots=True)
class YahooRepairedFrame:
    frame: pd.DataFrame
    library_version: str
    repaired_row_count: int


class YahooRepairedCandleQualificationClient:
    """Fetch one daily frame with yfinance repair explicitly enabled."""

    REPAIR_METHOD_IDENTITY = "YFINANCE_PRICE_REPAIR_V1"

    def __init__(
        self,
        ticker_factory: Callable[[str], Any] | None = None,
        *,
        cache_directory: str | Path | None = None,
        cache_location_setter: Callable[[str], None] | None = None,
        library_version: str | None = None,
    ) -> None:
        self._ticker_factory = ticker_factory or yf.Ticker
        self.library_version = normalize_required_text(
            library_version or yf.__version__, field_name="library_version"
        )
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
    ) -> YahooRepairedFrame:
        try:
            frame = self._ticker_factory(symbol).history(
                start=start,
                end=end,
                interval="1d",
                auto_adjust=False,
                actions=False,
                repair=True,
                raise_errors=True,
            )
        except Exception as exc:
            raise APIError("Yahoo repaired candle qualification request failed") from exc
        if not isinstance(frame, pd.DataFrame):
            raise ValueError("Yahoo repaired candle qualification returned invalid data")
        repaired_count = 0
        if "Repaired?" in frame.columns:
            repaired_count = sum(
                1
                for value in frame["Repaired?"]
                if isinstance(value, (bool, np.bool_)) and bool(value)
            )
        return YahooRepairedFrame(
            frame=frame,
            library_version=self.library_version,
            repaired_row_count=repaired_count,
        )
