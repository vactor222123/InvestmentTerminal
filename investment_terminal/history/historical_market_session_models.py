"""
Canonical immutable market-session contracts for historical outcome methodology.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalSessionCalendarIdentity:
    """
    Stable identity and provenance for one market-session calendar.

    This value object does not load, infer, or fetch sessions.
    """

    calendar_id: str
    version: int
    timezone: str
    source: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "calendar_id",
            normalize_required_text(
                self.calendar_id,
                field_name="calendar_id",
                uppercase=True,
            ),
        )

        if (
            isinstance(
                self.version,
                bool,
            )
            or not isinstance(
                self.version,
                int,
            )
            or self.version <= 0
        ):
            raise ValueError(
                "version must be a positive integer"
            )

        object.__setattr__(
            self,
            "timezone",
            normalize_required_text(
                self.timezone,
                field_name="timezone",
            ),
        )
        object.__setattr__(
            self,
            "source",
            normalize_required_text(
                self.source,
                field_name="source",
                uppercase=True,
            ),
        )

    @property
    def identity_key(
        self,
    ) -> str:
        return (
            f"{self.calendar_id}"
            f"@{self.version}"
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "calendar_id": self.calendar_id,
            "version": self.version,
            "identity_key": self.identity_key,
            "timezone": self.timezone,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class HistoricalMarketSession:
    """
    One explicitly identified market session.

    A session is factual calendar evidence. It does not select price evidence
    and does not imply that a candle exists for the session.
    """

    session_key: str
    session_date: date
    opens_at: datetime
    closes_at: datetime
    calendar: HistoricalSessionCalendarIdentity

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "session_key",
            normalize_required_text(
                self.session_key,
                field_name="session_key",
            ),
        )

        if (
            not isinstance(
                self.session_date,
                date,
            )
            or isinstance(
                self.session_date,
                datetime,
            )
        ):
            raise TypeError(
                "session_date must be a date"
            )

        validate_aware_datetime(
            self.opens_at,
            field_name="opens_at",
        )
        validate_aware_datetime(
            self.closes_at,
            field_name="closes_at",
        )

        if self.closes_at <= self.opens_at:
            raise ValueError(
                "closes_at must be later than opens_at"
            )

        if not isinstance(
            self.calendar,
            HistoricalSessionCalendarIdentity,
        ):
            raise TypeError(
                "calendar must be a HistoricalSessionCalendarIdentity"
            )

    @property
    def ordering_key(
        self,
    ) -> tuple[datetime, datetime, str]:
        return (
            self.opens_at,
            self.closes_at,
            self.session_key,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "session_key": self.session_key,
            "session_date": self.session_date.isoformat(),
            "opens_at": self.opens_at.isoformat(),
            "closes_at": self.closes_at.isoformat(),
            "calendar": self.calendar.to_dict(),
        }
