"""
Read-only repository for normalized historical deployment records.
"""

import json

from investment_terminal.history.historical_deployment_models import (
    HistoricalDeployment,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


class HistoricalDeploymentRepository:
    """Query typed deployment projections without exposing SQLite."""

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
    ) -> tuple[HistoricalDeployment, ...]:
        """Return deployment records ordered by stable deployment key."""
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
                    deployment_key,
                    amount,
                    share,
                    reason,
                    payload_json
                FROM deployment
                WHERE snapshot_id = ?
                ORDER BY deployment_key
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
    ) -> HistoricalDeployment:
        try:
            payload = json.loads(
                row["payload_json"]
            )
        except (
            json.JSONDecodeError,
            TypeError,
        ) as exc:
            raise ValueError(
                "deployment payload_json must contain valid JSON"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "deployment payload_json must contain a JSON object"
            )

        return HistoricalDeployment(
            snapshot_id=row["snapshot_id"],
            deployment_key=row["deployment_key"],
            amount=row["amount"],
            share=row["share"],
            reason=row["reason"],
            payload=payload,
        )
