"""
Read-only SQLite repository for historical timeline events.
"""

import json
import sqlite3
from datetime import datetime

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.history.historical_timeline_models import (
    HistoricalTimelineEvent,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class HistoricalTimelineRepository:
    """Query canonical historical timeline events from structured history."""

    def __init__(
        self,
        store: HistoricalSQLiteStore,
    ) -> None:
        if not isinstance(
            store,
            HistoricalSQLiteStore,
        ):
            raise TypeError(
                "store must be a HistoricalSQLiteStore"
            )

        self.store = store

    def list_for_snapshot(
        self,
        snapshot_id: str,
    ) -> tuple[HistoricalTimelineEvent, ...]:
        """Return events for one snapshot in deterministic timeline order."""
        normalized_id = HistoricalSnapshot._normalize_uuid(
            snapshot_id,
            field_name="snapshot_id",
        )

        return self._query(
            """
            SELECT *
            FROM timeline_events
            WHERE snapshot_id = ?
            ORDER BY occurred_at, event_id
            """,
            (
                normalized_id,
            ),
        )

    def find_by_type(
        self,
        event_type: str,
    ) -> tuple[HistoricalTimelineEvent, ...]:
        """Return events matching one normalized event type."""
        normalized_type = normalize_required_text(
            event_type,
            field_name="event_type",
            uppercase=True,
        )

        return self._query(
            """
            SELECT *
            FROM timeline_events
            WHERE event_type = ?
            ORDER BY occurred_at, event_id
            """,
            (
                normalized_type,
            ),
        )

    def find_by_subject(
        self,
        subject_key: str,
    ) -> tuple[HistoricalTimelineEvent, ...]:
        """Return events matching one non-empty subject key."""
        normalized_subject = normalize_required_text(
            subject_key,
            field_name="subject_key",
        )

        return self._query(
            """
            SELECT *
            FROM timeline_events
            WHERE subject_key = ?
            ORDER BY occurred_at, event_id
            """,
            (
                normalized_subject,
            ),
        )

    def find_between(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> tuple[HistoricalTimelineEvent, ...]:
        """Return events whose occurrence time is inside an inclusive range."""
        validate_aware_datetime(
            start,
            field_name="start",
        )
        validate_aware_datetime(
            end,
            field_name="end",
        )

        if end < start:
            raise ValueError(
                "end must not be earlier than start"
            )

        return self._query(
            """
            SELECT *
            FROM timeline_events
            WHERE occurred_at >= ?
              AND occurred_at <= ?
            ORDER BY occurred_at, event_id
            """,
            (
                start.isoformat(),
                end.isoformat(),
            ),
        )

    def latest(
        self,
        limit: int,
    ) -> tuple[HistoricalTimelineEvent, ...]:
        """
        Return the latest events in newest-first order.

        The returned order matches the meaning of "latest": most recent event
        first, with event_id providing deterministic tie-breaking.
        """
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit <= 0
        ):
            raise ValueError(
                "limit must be a positive integer"
            )

        return self._query(
            """
            SELECT *
            FROM timeline_events
            ORDER BY occurred_at DESC, event_id DESC
            LIMIT ?
            """,
            (
                limit,
            ),
        )

    def count(
        self,
    ) -> int:
        """Return the number of timeline events."""
        self.store.initialize()

        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS event_count
                FROM timeline_events
                """
            ).fetchone()

        return int(
            row["event_count"]
        )

    def _query(
        self,
        sql: str,
        parameters: tuple[object, ...],
    ) -> tuple[HistoricalTimelineEvent, ...]:
        self.store.initialize()

        with self.store.connect() as connection:
            rows = connection.execute(
                sql,
                parameters,
            ).fetchall()

        return tuple(
            self._from_row(
                row
            )
            for row in rows
        )

    @staticmethod
    def _from_row(
        row: sqlite3.Row,
    ) -> HistoricalTimelineEvent:
        try:
            payload = json.loads(
                row["payload_json"]
            )
        except (
            json.JSONDecodeError,
            TypeError,
        ) as exc:
            raise ValueError(
                "timeline payload_json must contain valid JSON"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "timeline payload_json must contain a JSON object"
            )

        return HistoricalTimelineEvent(
            event_id=row["event_id"],
            snapshot_id=row["snapshot_id"],
            event_type=row["event_type"],
            occurred_at=datetime.fromisoformat(
                row["occurred_at"]
            ),
            subject_key=row["subject_key"],
            payload=payload,
        )
