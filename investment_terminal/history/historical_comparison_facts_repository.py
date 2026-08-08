"""
Read-only repository for normalized snapshot comparison facts.
"""

import sqlite3

from investment_terminal.history.historical_comparison_facts import (
    HistoricalComparisonFacts,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


class HistoricalComparisonFactsRepository:
    """
    Query only normalized facts required by snapshot compatibility checks.

    Compatibility policy belongs to the compatibility service. This repository
    owns the underlying History persistence queries and returns a typed read
    model without exposing SQLite rows to callers.
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

    def get(
        self,
        snapshot_id: str,
    ) -> HistoricalComparisonFacts:
        """Return normalized comparison facts for a registered snapshot."""
        normalized_id = HistoricalSnapshot._normalize_uuid(
            snapshot_id,
            field_name="snapshot_id",
        )

        self.store.initialize()

        with self.store.connect() as connection:
            if not self._snapshot_exists(
                connection,
                normalized_id,
            ):
                raise KeyError(
                    f"No historical snapshot found for {snapshot_id}"
                )

            summary = connection.execute(
                """
                SELECT
                    portfolio_name,
                    base_currency,
                    source_status
                FROM portfolio_summary
                WHERE snapshot_id = ?
                """,
                (
                    normalized_id,
                ),
            ).fetchone()

            holdings_count = self._count_rows(
                connection,
                table="holdings",
                snapshot_id=normalized_id,
            )
            recommendations_count = self._count_rows(
                connection,
                table="recommendations",
                snapshot_id=normalized_id,
            )
            deployment_count = self._count_rows(
                connection,
                table="deployment",
                snapshot_id=normalized_id,
            )
            timeline_event_count = self._count_rows(
                connection,
                table="timeline_events",
                snapshot_id=normalized_id,
            )

        return HistoricalComparisonFacts(
            snapshot_id=normalized_id,
            portfolio_summary_present=summary is not None,
            portfolio_name=(
                None
                if summary is None
                else summary["portfolio_name"]
            ),
            base_currency=(
                None
                if summary is None
                else summary["base_currency"]
            ),
            source_status=(
                None
                if summary is None
                else summary["source_status"]
            ),
            holdings_count=holdings_count,
            recommendations_count=recommendations_count,
            deployment_count=deployment_count,
            timeline_event_count=timeline_event_count,
        )

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

    @staticmethod
    def _count_rows(
        connection: sqlite3.Connection,
        *,
        table: str,
        snapshot_id: str,
    ) -> int:
        row = connection.execute(
            f"""
            SELECT COUNT(*) AS row_count
            FROM {table}
            WHERE snapshot_id = ?
            """,
            (
                snapshot_id,
            ),
        ).fetchone()

        return int(
            row["row_count"]
        )
