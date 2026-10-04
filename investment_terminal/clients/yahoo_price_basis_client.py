"""One-request, read-only Yahoo history adapter for price-basis qualification."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf


class YahooPriceBasisClient:
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
            (cache_location_setter or yf.set_tz_cache_location)(
                str(directory.resolve())
            )

    def get_daily_frame(
        self, *, symbol: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        # Deliberately separate from strict OHLCV ingestion; no persistence.
        return self._ticker_factory(symbol).history(
            start=start,
            end=end,
            interval="1d",
            auto_adjust=False,
            actions=True,
            repair=False,
            raise_errors=True,
        )
