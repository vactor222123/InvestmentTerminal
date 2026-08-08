"""
Deterministic local read-only market-session calendar boundary.
"""

from datetime import date, datetime
from typing import Iterable

from investment_terminal.history.historical_market_session_models import (
    HistoricalMarketSession,
    HistoricalSessionCalendarIdentity,
)
from investment_terminal.utils.validation import (
    validate_aware_datetime,
)


class HistoricalLocalSessionCalendar:
    """
    Read-only deterministic calendar over explicitly supplied market sessions.

    The calendar does not infer sessions from weekdays, candles, or exchange
    names. It performs no network access and owns no persistence.
    """

    def __init__(
        self,
        *,
        identity: HistoricalSessionCalendarIdentity,
        sessions: Iterable[HistoricalMarketSession],
    ) -> None:
        if not isinstance(
            identity,
            HistoricalSessionCalendarIdentity,
        ):
            raise TypeError(
                "identity must be a HistoricalSessionCalendarIdentity"
            )

        materialized = tuple(
            sessions
        )

        if any(
            not isinstance(
                session,
                HistoricalMarketSession,
            )
            for session in materialized
        ):
            raise TypeError(
                "sessions must contain only HistoricalMarketSession values"
            )

        for session in materialized:
            if session.calendar != identity:
                raise ValueError(
                    "every session calendar must match the provider identity"
                )

        ordered = tuple(
            sorted(
                materialized,
                key=lambda item: item.ordering_key,
            )
        )

        keys = tuple(
            session.session_key
            for session in ordered
        )
        if len(
            set(
                keys
            )
        ) != len(
            keys
        ):
            raise ValueError(
                "session_key values must be unique"
            )

        dates = tuple(
            session.session_date
            for session in ordered
        )
        if len(
            set(
                dates
            )
        ) != len(
            dates
        ):
            raise ValueError(
                "session_date values must be unique within one calendar"
            )

        self._identity = identity
        self._sessions = ordered
        self._by_key = {
            session.session_key: session
            for session in ordered
        }
        self._by_date = {
            session.session_date: session
            for session in ordered
        }

    @property
    def identity(
        self,
    ) -> HistoricalSessionCalendarIdentity:
        return self._identity

    def list_all(
        self,
    ) -> tuple[HistoricalMarketSession, ...]:
        return self._sessions

    def get_by_key(
        self,
        session_key: str,
    ) -> HistoricalMarketSession | None:
        if (
            not isinstance(
                session_key,
                str,
            )
            or not session_key.strip()
        ):
            raise ValueError(
                "session_key must be a non-empty string"
            )

        normalized = session_key.strip()
        return self._by_key.get(
            normalized
        )

    def get_by_date(
        self,
        session_date: date,
    ) -> HistoricalMarketSession | None:
        if (
            not isinstance(
                session_date,
                date,
            )
            or isinstance(
                session_date,
                datetime,
            )
        ):
            raise TypeError(
                "session_date must be a date"
            )

        return self._by_date.get(
            session_date
        )

    def list_between(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
    ) -> tuple[HistoricalMarketSession, ...]:
        """
        Return sessions whose open timestamp lies within an inclusive interval.

        The explicit open timestamp is used so callers do not need to infer
        calendar-local dates from UTC timestamps.
        """
        validate_aware_datetime(
            start_at,
            field_name="start_at",
        )
        validate_aware_datetime(
            end_at,
            field_name="end_at",
        )

        if start_at > end_at:
            raise ValueError(
                "start_at must not be later than end_at"
            )

        return tuple(
            session
            for session in self._sessions
            if (
                session.opens_at >= start_at
                and session.opens_at <= end_at
            )
        )

    def first_session_opening_after(
        self,
        timestamp: datetime,
        *,
        inclusive: bool = False,
    ) -> HistoricalMarketSession | None:
        """
        Return the first session whose open is after the supplied timestamp.

        `inclusive=True` also permits a session opening exactly at timestamp.
        This method does not define trading-window origin semantics; callers
        must choose the inclusion rule explicitly.
        """
        validate_aware_datetime(
            timestamp,
            field_name="timestamp",
        )

        if not isinstance(
            inclusive,
            bool,
        ):
            raise TypeError(
                "inclusive must be a bool"
            )

        for session in self._sessions:
            if inclusive:
                if session.opens_at >= timestamp:
                    return session
            elif session.opens_at > timestamp:
                return session

        return None

    def sessions_after(
        self,
        timestamp: datetime,
        *,
        inclusive: bool = False,
    ) -> tuple[HistoricalMarketSession, ...]:
        """
        Return all sessions ordered after the supplied timestamp.

        This is a query primitive only. It does not count an observation
        window or choose an endpoint.
        """
        validate_aware_datetime(
            timestamp,
            field_name="timestamp",
        )

        if not isinstance(
            inclusive,
            bool,
        ):
            raise TypeError(
                "inclusive must be a bool"
            )

        return tuple(
            session
            for session in self._sessions
            if (
                session.opens_at >= timestamp
                if inclusive
                else session.opens_at > timestamp
            )
        )
