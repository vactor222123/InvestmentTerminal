"""
Deterministic trading-session observation-window policy.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, ClassVar

from investment_terminal.history.historical_local_session_calendar import (
    HistoricalLocalSessionCalendar,
)
from investment_terminal.history.historical_market_session_models import (
    HistoricalMarketSession,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
)
from investment_terminal.utils.validation import (
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalTradingSessionWindowResolution:
    """Resolved trading-session endpoint and maturity."""

    origin_at: datetime
    endpoint_at: datetime
    as_of: datetime
    is_mature: bool
    endpoint_session: HistoricalMarketSession
    counted_session_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        validate_aware_datetime(self.origin_at, field_name="origin_at")
        validate_aware_datetime(self.endpoint_at, field_name="endpoint_at")
        validate_aware_datetime(self.as_of, field_name="as_of")

        if not isinstance(self.endpoint_session, HistoricalMarketSession):
            raise TypeError(
                "endpoint_session must be a HistoricalMarketSession"
            )
        if self.endpoint_at != self.endpoint_session.closes_at:
            raise ValueError(
                "endpoint_at must equal endpoint_session.closes_at"
            )
        if self.endpoint_at <= self.origin_at:
            raise ValueError(
                "endpoint_at must be later than origin_at"
            )
        if not isinstance(self.counted_session_keys, tuple):
            raise TypeError(
                "counted_session_keys must be a tuple"
            )
        if not self.counted_session_keys:
            raise ValueError(
                "counted_session_keys must not be empty"
            )
        if self.counted_session_keys[-1] != self.endpoint_session.session_key:
            raise ValueError(
                "last counted session must be the endpoint session"
            )
        if len(set(self.counted_session_keys)) != len(self.counted_session_keys):
            raise ValueError(
                "counted_session_keys must be unique"
            )

        expected_maturity = self.as_of >= self.endpoint_at
        if self.is_mature is not expected_maturity:
            raise ValueError(
                "is_mature must match as_of relative to endpoint_at"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin_at": self.origin_at.isoformat(),
            "endpoint_at": self.endpoint_at.isoformat(),
            "as_of": self.as_of.isoformat(),
            "is_mature": self.is_mature,
            "endpoint_session": self.endpoint_session.to_dict(),
            "counted_session_keys": list(self.counted_session_keys),
        }


class HistoricalTradingSessionWindowPolicy:
    """
    Resolve explicit TRADING_SESSIONS windows against a supplied local calendar.

    Canonical v1 semantics:
    - origin session is not implicitly included;
    - only sessions whose opens_at is strictly later than origin are counted;
    - window.value selects the Nth such explicit session;
    - endpoint_at is that session's closes_at;
    - maturity means as_of >= endpoint_at;
    - no weekday inference, nearest-session inference, or candle lookup occurs.
    """

    TRADING_SESSIONS: ClassVar[str] = "TRADING_SESSIONS"

    def __init__(
        self,
        calendar: HistoricalLocalSessionCalendar,
    ) -> None:
        if not isinstance(calendar, HistoricalLocalSessionCalendar):
            raise TypeError(
                "calendar must be a HistoricalLocalSessionCalendar"
            )
        self.calendar = calendar

    def resolve(
        self,
        *,
        origin_at: datetime,
        window: HistoricalObservationWindow,
        as_of: datetime,
    ) -> HistoricalTradingSessionWindowResolution:
        validate_aware_datetime(origin_at, field_name="origin_at")
        validate_aware_datetime(as_of, field_name="as_of")

        if not isinstance(window, HistoricalObservationWindow):
            raise TypeError(
                "window must be a HistoricalObservationWindow"
            )
        if window.kind != self.TRADING_SESSIONS:
            raise ValueError(
                "window kind is not supported by this policy: "
                f"{window.kind}"
            )

        origin_utc = origin_at.astimezone(timezone.utc)
        as_of_utc = as_of.astimezone(timezone.utc)

        sessions = self.calendar.sessions_after(
            origin_at,
            inclusive=False,
        )
        if len(sessions) < window.value:
            raise ValueError(
                "local session calendar does not contain enough "
                "sessions after origin to resolve the requested window"
            )

        counted = sessions[: window.value]
        endpoint_session = counted[-1]
        endpoint_utc = endpoint_session.closes_at.astimezone(
            timezone.utc
        )

        return HistoricalTradingSessionWindowResolution(
            origin_at=origin_utc,
            endpoint_at=endpoint_utc,
            as_of=as_of_utc,
            is_mature=(as_of_utc >= endpoint_utc),
            endpoint_session=endpoint_session,
            counted_session_keys=tuple(
                session.session_key
                for session in counted
            ),
        )
