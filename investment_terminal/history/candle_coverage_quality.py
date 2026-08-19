"""Deterministic daily-candle coverage quality against explicit sessions."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from investment_terminal.history.historical_local_session_calendar import (
    HistoricalLocalSessionCalendar,
)
from investment_terminal.models.candle import Candle
from investment_terminal.utils.validation import validate_aware_datetime


@dataclass(frozen=True, slots=True)
class CandleCoverageQualityResult:
    """Measured agreement between daily candles and explicit sessions."""

    symbol: str
    resolution: str
    start_at: datetime
    end_at: datetime
    calendar_identity: str
    expected_session_count: int
    observed_session_count: int
    missing_session_keys: tuple[str, ...]
    unexpected_candle_timestamps: tuple[datetime, ...]

    @property
    def completeness_ratio(self) -> float | None:
        if self.expected_session_count == 0:
            return None
        return self.observed_session_count / self.expected_session_count

    @property
    def is_complete(self) -> bool:
        return (
            self.expected_session_count > 0
            and not self.missing_session_keys
            and not self.unexpected_candle_timestamps
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "symbol": self.symbol,
            "resolution": self.resolution,
            "start_at": self.start_at.isoformat(),
            "end_at": self.end_at.isoformat(),
            "calendar_identity": self.calendar_identity,
            "expected_session_count": self.expected_session_count,
            "observed_session_count": self.observed_session_count,
            "missing_session_count": len(self.missing_session_keys),
            "missing_session_keys": list(self.missing_session_keys),
            "unexpected_candle_count": len(
                self.unexpected_candle_timestamps
            ),
            "unexpected_candle_timestamps": [
                value.isoformat()
                for value in self.unexpected_candle_timestamps
            ],
            "completeness_ratio": self.completeness_ratio,
            "is_complete": self.is_complete,
        }


class CandleCoverageQualityService:
    """Compare daily candle dates with explicit calendar session dates."""

    def evaluate(
        self,
        *,
        symbol: str,
        resolution: str,
        start_at: datetime,
        end_at: datetime,
        candles: Iterable[Candle],
        calendar: HistoricalLocalSessionCalendar,
    ) -> CandleCoverageQualityResult:
        normalized_symbol = self._text(symbol, "symbol")
        normalized_resolution = self._text(resolution, "resolution")
        if normalized_resolution != "D":
            raise ValueError("coverage quality currently supports D only")
        validate_aware_datetime(start_at, field_name="start_at")
        validate_aware_datetime(end_at, field_name="end_at")
        if start_at > end_at:
            raise ValueError("start_at must not be later than end_at")
        if not isinstance(calendar, HistoricalLocalSessionCalendar):
            raise TypeError("calendar must be a HistoricalLocalSessionCalendar")

        materialized = tuple(candles)
        if any(not isinstance(item, Candle) for item in materialized):
            raise TypeError("candles must contain only Candle values")
        for candle in materialized:
            if candle.symbol.strip().upper() != normalized_symbol:
                raise ValueError("every candle must match symbol")
            if candle.resolution.strip().upper() != normalized_resolution:
                raise ValueError("every candle must match resolution")
            validate_aware_datetime(candle.timestamp, field_name="candle timestamp")
            if not start_at <= candle.timestamp <= end_at:
                raise ValueError("every candle must be inside the requested window")

        timestamps = tuple(item.timestamp for item in materialized)
        if len(set(timestamps)) != len(timestamps):
            raise ValueError("candle timestamps must be unique")

        sessions = calendar.list_between(start_at=start_at, end_at=end_at)
        timezone = ZoneInfo(calendar.identity.timezone)
        sessions_by_date = {
            session.session_date: session
            for session in sessions
        }
        candles_by_date = {
            candle.timestamp.astimezone(timezone).date(): candle
            for candle in materialized
        }
        if len(candles_by_date) != len(materialized):
            raise ValueError("daily candles must have unique calendar-local dates")

        missing = tuple(
            session.session_key
            for session in sessions
            if session.session_date not in candles_by_date
        )
        unexpected = tuple(
            candle.timestamp
            for local_date, candle in sorted(
                candles_by_date.items(),
                key=lambda item: item[1].timestamp,
            )
            if local_date not in sessions_by_date
        )
        observed = len(sessions) - len(missing)

        return CandleCoverageQualityResult(
            symbol=normalized_symbol,
            resolution=normalized_resolution,
            start_at=start_at,
            end_at=end_at,
            calendar_identity=calendar.identity.identity_key,
            expected_session_count=len(sessions),
            observed_session_count=observed,
            missing_session_keys=missing,
            unexpected_candle_timestamps=unexpected,
        )

    @staticmethod
    def _text(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")
        return value.strip().upper()
