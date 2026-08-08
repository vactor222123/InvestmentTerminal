"""
Build historical timeline events from normalized SQLite history.
"""

import json
import sqlite3
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Any

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


class HistoricalTimelineBuilder:
    """
    Build deterministic timeline events for one imported snapshot.

    Events are derived from normalized History Domain tables. The builder
    creates:

    - SNAPSHOT_ARCHIVED;
    - PORTFOLIO_SUMMARY_RECORDED;
    - HOLDING_RECORDED;
    - RECOMMENDATION_RECORDED;
    - DEPLOYMENT_RECORDED.

    Existing timeline events for the snapshot are rejected so that repeated
    execution cannot silently duplicate historical facts.
    """

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

    def build(
        self,
        snapshot: HistoricalSnapshot,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> int:
        """Create all timeline events available for one snapshot."""
        if not isinstance(
            snapshot,
            HistoricalSnapshot,
        ):
            raise TypeError(
                "snapshot must be a HistoricalSnapshot"
            )

        if connection is None:
            self.store.initialize()

        with (nullcontext(connection) if connection is not None else self.store.connect()) as connection:
            if not self._snapshot_exists(
                connection,
                snapshot.snapshot_id,
            ):
                raise ValueError(
                    "Snapshot must exist in SQLite before "
                    "timeline events are built"
                )

            existing = connection.execute(
                """
                SELECT COUNT(*) AS event_count
                FROM timeline_events
                WHERE snapshot_id = ?
                """,
                (
                    snapshot.snapshot_id,
                ),
            ).fetchone()

            if int(
                existing["event_count"]
            ) > 0:
                raise ValueError(
                    "Timeline events already exist for snapshot "
                    f"{snapshot.snapshot_id}"
                )

            events = self._collect_events(
                connection=connection,
                snapshot=snapshot,
            )

            connection.executemany(
                """
                INSERT INTO timeline_events (
                    snapshot_id,
                    event_type,
                    occurred_at,
                    subject_key,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                tuple(
                    (
                        snapshot.snapshot_id,
                        event["event_type"],
                        event["occurred_at"],
                        event["subject_key"],
                        event["payload_json"],
                    )
                    for event in events
                ),
            )

        return len(
            events
        )

    @classmethod
    def _collect_events(
        cls,
        *,
        connection: sqlite3.Connection,
        snapshot: HistoricalSnapshot,
    ) -> tuple[dict[str, Any], ...]:
        events: list[
            dict[str, Any]
        ] = [
            cls._event(
                event_type="SNAPSHOT_ARCHIVED",
                occurred_at=snapshot.archived_at,
                subject_key=snapshot.snapshot_id,
                payload=snapshot.to_dict(),
            )
        ]

        summary = connection.execute(
            """
            SELECT *
            FROM portfolio_summary
            WHERE snapshot_id = ?
            """,
            (
                snapshot.snapshot_id,
            ),
        ).fetchone()

        if summary is not None:
            events.append(
                cls._event(
                    event_type=(
                        "PORTFOLIO_SUMMARY_RECORDED"
                    ),
                    occurred_at=snapshot.generated_at,
                    subject_key=summary[
                        "portfolio_name"
                    ],
                    payload=dict(
                        summary
                    ),
                )
            )

        holdings = connection.execute(
            """
            SELECT *
            FROM holdings
            WHERE snapshot_id = ?
            ORDER BY holding_key
            """,
            (
                snapshot.snapshot_id,
            ),
        ).fetchall()

        for holding in holdings:
            events.append(
                cls._event(
                    event_type="HOLDING_RECORDED",
                    occurred_at=snapshot.generated_at,
                    subject_key=holding[
                        "holding_key"
                    ],
                    payload=dict(
                        holding
                    ),
                )
            )

        recommendations = connection.execute(
            """
            SELECT *
            FROM recommendations
            WHERE snapshot_id = ?
            ORDER BY recommendation_key
            """,
            (
                snapshot.snapshot_id,
            ),
        ).fetchall()

        for recommendation in recommendations:
            events.append(
                cls._event(
                    event_type=(
                        "RECOMMENDATION_RECORDED"
                    ),
                    occurred_at=snapshot.generated_at,
                    subject_key=recommendation[
                        "recommendation_key"
                    ],
                    payload=dict(
                        recommendation
                    ),
                )
            )

        deployment = connection.execute(
            """
            SELECT *
            FROM deployment
            WHERE snapshot_id = ?
            ORDER BY deployment_key
            """,
            (
                snapshot.snapshot_id,
            ),
        ).fetchall()

        for item in deployment:
            events.append(
                cls._event(
                    event_type="DEPLOYMENT_RECORDED",
                    occurred_at=snapshot.generated_at,
                    subject_key=item[
                        "deployment_key"
                    ],
                    payload=dict(
                        item
                    ),
                )
            )

        return tuple(
            events
        )

    @staticmethod
    def _event(
        *,
        event_type: str,
        occurred_at: datetime,
        subject_key: str | None,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if (
            occurred_at.tzinfo is None
            or occurred_at.utcoffset() is None
        ):
            raise ValueError(
                "timeline occurred_at must be timezone-aware"
            )

        normalized_time = occurred_at.astimezone(
            timezone.utc
        ).isoformat()

        return {
            "event_type": event_type,
            "occurred_at": normalized_time,
            "subject_key": subject_key,
            "payload_json": json.dumps(
                payload,
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
                allow_nan=False,
            ),
        }

    @staticmethod
    def _snapshot_exists(
        connection: sqlite3.Connection,
        snapshot_id: str,
    ) -> bool:
        row = connection.execute(
            """
            SELECT 1
            FROM snapshots
            WHERE snapshot_id = ?
            """,
            (
                snapshot_id,
            ),
        ).fetchone()

        return row is not None
