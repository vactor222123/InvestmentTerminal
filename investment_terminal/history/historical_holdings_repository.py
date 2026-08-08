"""
Read-only repository for normalized historical holdings.
"""

from investment_terminal.history.historical_holding_models import (
    HistoricalHolding,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


class HistoricalHoldingsRepository:
    """Query typed holding projections without exposing SQLite."""

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
    ) -> tuple[HistoricalHolding, ...]:
        """Return holdings ordered by stable holding key."""
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
                    holding_key,
                    symbol,
                    name,
                    asset_type,
                    sleeve,
                    strategy,
                    currency,
                    quantity,
                    unit_price,
                    market_value,
                    weight
                FROM holdings
                WHERE snapshot_id = ?
                ORDER BY holding_key
                """,
                (
                    normalized_id,
                ),
            ).fetchall()

        return tuple(
            HistoricalHolding(
                snapshot_id=row["snapshot_id"],
                holding_key=row["holding_key"],
                symbol=row["symbol"],
                name=row["name"],
                asset_type=row["asset_type"],
                sleeve=row["sleeve"],
                strategy=row["strategy"],
                currency=row["currency"],
                quantity=row["quantity"],
                unit_price=row["unit_price"],
                market_value=row["market_value"],
                weight=row["weight"],
            )
            for row in rows
        )
