"""
Read-only repository for normalized historical portfolio summaries.
"""

from investment_terminal.history.historical_portfolio_summary_models import (
    HistoricalPortfolioSummary,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


class HistoricalPortfolioSummaryRepository:
    """Query typed portfolio-summary projections without exposing SQLite."""

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
    ) -> HistoricalPortfolioSummary | None:
        """Return one normalized summary, or None when the summary is absent."""
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

            row = connection.execute(
                """
                SELECT
                    snapshot_id,
                    portfolio_name,
                    base_currency,
                    total_value,
                    invested_value,
                    cash_value,
                    monthly_contribution,
                    source_status
                FROM portfolio_summary
                WHERE snapshot_id = ?
                """,
                (
                    normalized_id,
                ),
            ).fetchone()

        if row is None:
            return None

        return HistoricalPortfolioSummary(
            snapshot_id=row["snapshot_id"],
            portfolio_name=row["portfolio_name"],
            base_currency=row["base_currency"],
            total_value=row["total_value"],
            invested_value=row["invested_value"],
            cash_value=row["cash_value"],
            monthly_contribution=row["monthly_contribution"],
            source_status=row["source_status"],
        )
