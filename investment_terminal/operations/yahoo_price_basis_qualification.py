"""Redacted, bounded field-shape qualification; no adjustment claim."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Any, Protocol

import pandas as pd

from investment_terminal.utils.validation import normalize_required_text


class DailyFrameClient(Protocol):
    def get_daily_frame(
        self, *, symbol: str, start: datetime, end: datetime
    ) -> object: ...


FIELDS = ("Adj Close", "Dividends", "Stock Splits")


@dataclass(frozen=True, slots=True)
class PriceBasisRequest:
    symbol: str
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        symbol = normalize_required_text(self.symbol, field_name="symbol", uppercase=True)
        if any(character.isspace() for character in symbol):
            raise ValueError("symbol must not contain whitespace")
        object.__setattr__(self, "symbol", symbol)
        for name, value in (("start", self.start), ("end", self.end)):
            if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
                raise ValueError(f"{name} must be a UTC datetime")
            if value.time() != datetime.min.time():
                raise ValueError(f"{name} must be UTC midnight")
        if not self.start < self.end <= self.start + timedelta(days=3660):
            raise ValueError("window must be positive and at most 3660 days")


class PriceBasisQualification:
    """Exactly one provider request, then an aggregate-only result."""

    def __init__(self, client: DailyFrameClient) -> None:
        self._client = client

    def qualify(self, request: PriceBasisRequest) -> dict[str, Any]:
        if not isinstance(request, PriceBasisRequest):
            raise TypeError("request must be PriceBasisRequest")
        base: dict[str, Any] = {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE",
            "request": {
                "interval": "1d",
                "start_utc": request.start.isoformat(),
                "end_utc_exclusive": request.end.isoformat(),
                "auto_adjust": False,
                "actions": True,
                "repair": False,
            },
            "status": None,
            "row_count": None,
            "fields": {name: {"present": False, "valid_count": None, "nonzero_count": None} for name in FIELDS},
            "failure_category": None,
            "limitations": [
                "field shape does not establish adjustment methodology",
                "no adjusted prices, actions, or returns are stored",
                "one request does not establish provider reliability or session completeness",
            ],
        }
        try:
            frame = self._client.get_daily_frame(
                symbol=request.symbol, start=request.start, end=request.end
            )
        except Exception:
            base["status"] = "PROVIDER_FAILURE"
            base["failure_category"] = "PROVIDER_REQUEST"
            return base
        if not isinstance(frame, pd.DataFrame):
            return self._malformed(base, "FRAME_TYPE")
        if frame.empty:
            base["status"] = "EMPTY"
            base["row_count"] = 0
            return base
        base["row_count"] = len(frame)
        if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
            return self._malformed(base, "TIMESTAMP_INDEX")
        index = frame.index.tz_convert(timezone.utc)
        if index.hasnans or not index.is_unique or not index.is_monotonic_increasing:
            return self._malformed(base, "TIMESTAMP_INDEX")
        if index[0].to_pydatetime() < request.start or index[-1].to_pydatetime() >= request.end:
            return self._malformed(base, "TIMESTAMP_WINDOW")
        if not frame.columns.is_unique or not all(isinstance(name, str) for name in frame.columns):
            return self._malformed(base, "COLUMN_SHAPE")
        if "Close" not in frame.columns:
            return self._malformed(base, "CLOSE_MISSING")
        if not self._numeric_column(frame["Close"], positive=True):
            return self._malformed(base, "CLOSE_INVALID")
        for name in FIELDS:
            if name not in frame.columns:
                continue
            values = frame[name]
            base["fields"][name]["present"] = True
            if not self._numeric_column(values, positive=name == "Adj Close"):
                return self._malformed(base, "CANDIDATE_INVALID")
            base["fields"][name]["valid_count"] = len(values)
            base["fields"][name]["nonzero_count"] = sum(float(value) != 0 for value in values)
        base["status"] = "QUALIFIED" if all(base["fields"][name]["present"] for name in FIELDS) else "MISSING_FIELDS"
        return base

    @staticmethod
    def _numeric_column(values: pd.Series, *, positive: bool) -> bool:
        for value in values:
            if isinstance(value, (bool, complex, str)):
                return False
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError):
                return False
            if not isfinite(number) or (number <= 0 if positive else number < 0):
                return False
        return True

    @staticmethod
    def _malformed(base: dict[str, Any], category: str) -> dict[str, Any]:
        base["status"] = "MALFORMED"
        base["failure_category"] = category
        # Partial counts can be misleading after a failed frame validation.
        base["fields"] = {name: {"present": False, "valid_count": None, "nonzero_count": None} for name in FIELDS}
        return base
