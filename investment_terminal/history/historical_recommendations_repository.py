"""
Read-only repository for normalized historical recommendations.
"""

import json

from investment_terminal.history.historical_recommendation_models import (
    HistoricalRecommendation,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


class HistoricalRecommendationsRepository:
    """Query typed recommendation projections without exposing SQLite."""

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
    ) -> tuple[HistoricalRecommendation, ...]:
        """Return recommendations ordered by stable recommendation key."""
        normalized_id = HistoricalSnapshot._normalize_uuid(
            snapshot_id,
            field_name="snapshot_id",
        )

        self.store.initialize()

        with self.store.connect() as connection:
            snapshot_exists = connection.execute(
                """
                SELECT 1
                FROM snapshots
                WHERE snapshot_id = ?
                """,
                (
                    normalized_id,
                ),
            ).fetchone()

            if snapshot_exists is None:
                raise KeyError(
                    f"No historical snapshot found for {snapshot_id}"
                )

            rows = connection.execute(
                """
                SELECT
                    snapshot_id,
                    recommendation_key,
                    symbol,
                    action,
                    score,
                    confidence,
                    rationale,
                    payload_json
                FROM recommendations
                WHERE snapshot_id = ?
                ORDER BY recommendation_key
                """,
                (
                    normalized_id,
                ),
            ).fetchall()

        return tuple(
            self._from_row(
                row
            )
            for row in rows
        )

    @staticmethod
    def _from_row(
        row,
    ) -> HistoricalRecommendation:
        try:
            payload = json.loads(
                row["payload_json"]
            )
        except (
            json.JSONDecodeError,
            TypeError,
        ) as exc:
            raise ValueError(
                "recommendation payload_json must contain valid JSON"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "recommendation payload_json must contain a JSON object"
            )

        return HistoricalRecommendation(
            snapshot_id=row["snapshot_id"],
            recommendation_key=row["recommendation_key"],
            symbol=row["symbol"],
            action=row["action"],
            score=row["score"],
            confidence=row["confidence"],
            rationale=row["rationale"],
            payload=payload,
        )
