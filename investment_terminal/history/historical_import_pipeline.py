"""
End-to-end import pipeline for one archived historical snapshot.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.history.historical_deployment_importer import (
    HistoricalDeploymentImporter,
)
from investment_terminal.history.historical_holdings_importer import (
    HistoricalHoldingsImporter,
)
from investment_terminal.history.historical_portfolio_summary_importer import (
    HistoricalPortfolioSummaryImporter,
)
from investment_terminal.history.historical_recommendations_importer import (
    HistoricalRecommendationsImporter,
)
from investment_terminal.history.historical_review_package_loader import (
    HistoricalReviewPackageLoader,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.history.historical_timeline_builder import (
    HistoricalTimelineBuilder,
)


@dataclass(frozen=True, slots=True)
class HistoricalImportResult:
    """Summary of one successful snapshot-detail import."""

    snapshot_id: str
    holdings_imported: int
    recommendations_imported: int
    deployment_imported: int
    timeline_events_created: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.snapshot_id, str)
            or not self.snapshot_id.strip()
        ):
            raise ValueError(
                "snapshot_id must be a non-empty string"
            )

        for field_name in (
            "holdings_imported",
            "recommendations_imported",
            "deployment_imported",
            "timeline_events_created",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

    def to_dict(
        self,
    ) -> dict[str, str | int]:
        return {
            "snapshot_id": self.snapshot_id,
            "holdings_imported": self.holdings_imported,
            "recommendations_imported": (
                self.recommendations_imported
            ),
            "deployment_imported": self.deployment_imported,
            "timeline_events_created": (
                self.timeline_events_created
            ),
        }


class HistoricalImportPipeline:
    """
    Import one archived Review Package into structured historical tables.

    Workflow:

        HistoricalSnapshot
            -> verify archived JSON
            -> portfolio_summary
            -> holdings
            -> recommendations
            -> deployment
            -> timeline_events

    Snapshot metadata must already exist in SQLite, normally through the
    manifest import service. If a later stage fails, all detail rows created
    for this snapshot are removed while the snapshot metadata is preserved.
    """

    def __init__(
        self,
        *,
        store: HistoricalSQLiteStore,
        loader: HistoricalReviewPackageLoader,
    ) -> None:
        if not isinstance(
            store,
            HistoricalSQLiteStore,
        ):
            raise TypeError(
                "store must be a HistoricalSQLiteStore"
            )

        if not isinstance(
            loader,
            HistoricalReviewPackageLoader,
        ):
            raise TypeError(
                "loader must be a HistoricalReviewPackageLoader"
            )

        self.store = store
        self.loader = loader
        self.repository = HistoricalSnapshotRepository(
            store
        )
        self.summary_importer = (
            HistoricalPortfolioSummaryImporter(
                store
            )
        )
        self.holdings_importer = HistoricalHoldingsImporter(
            store
        )
        self.recommendations_importer = (
            HistoricalRecommendationsImporter(
                store
            )
        )
        self.deployment_importer = (
            HistoricalDeploymentImporter(
                store
            )
        )
        self.timeline_builder = HistoricalTimelineBuilder(
            store
        )

    def import_snapshot(
        self,
        snapshot: HistoricalSnapshot,
    ) -> HistoricalImportResult:
        """Verify and import one snapshot into all structured tables."""
        if not isinstance(
            snapshot,
            HistoricalSnapshot,
        ):
            raise TypeError(
                "snapshot must be a HistoricalSnapshot"
            )

        registered = self.repository.get(
            snapshot.snapshot_id
        )

        if registered is None:
            raise ValueError(
                "Snapshot metadata must exist in SQLite before "
                "the Review Package is imported"
            )

        if registered != snapshot:
            raise ValueError(
                "Snapshot metadata does not match the registered "
                "SQLite record"
            )

        if self._has_detail_rows(
            snapshot.snapshot_id
        ):
            raise ValueError(
                "Historical snapshot details have already been imported"
            )

        payload = self.loader.load(
            snapshot
        )

        try:
            self.summary_importer.import_summary(
                snapshot=snapshot,
                payload=payload,
            )
            holdings = self.holdings_importer.import_holdings(
                snapshot=snapshot,
                payload=payload,
            )
            recommendations = (
                self.recommendations_importer
                .import_recommendations(
                    snapshot=snapshot,
                    payload=payload,
                )
            )
            deployment = (
                self.deployment_importer
                .import_deployment(
                    snapshot=snapshot,
                    payload=payload,
                )
            )
            timeline_events = self.timeline_builder.build(
                snapshot
            )
        except Exception:
            self._remove_partial_import(
                snapshot.snapshot_id
            )
            raise

        return HistoricalImportResult(
            snapshot_id=snapshot.snapshot_id,
            holdings_imported=holdings,
            recommendations_imported=recommendations,
            deployment_imported=deployment,
            timeline_events_created=timeline_events,
        )

    def _has_detail_rows(
        self,
        snapshot_id: str,
    ) -> bool:
        self.store.initialize()

        with self.store.connect() as connection:
            for table in (
                "portfolio_summary",
                "holdings",
                "recommendations",
                "deployment",
                "timeline_events",
            ):
                row = connection.execute(
                    f"""
                    SELECT 1
                    FROM {table}
                    WHERE snapshot_id = ?
                    LIMIT 1
                    """,
                    (
                        snapshot_id,
                    ),
                ).fetchone()

                if row is not None:
                    return True

        return False

    def _remove_partial_import(
        self,
        snapshot_id: str,
    ) -> None:
        """
        Remove detail rows from an incomplete pipeline run.

        Snapshot metadata is intentionally retained so the immutable manifest
        and structured snapshot index remain synchronized.
        """
        self.store.initialize()

        with self.store.connect() as connection:
            for table in (
                "timeline_events",
                "deployment",
                "recommendations",
                "holdings",
                "portfolio_summary",
            ):
                connection.execute(
                    f"""
                    DELETE FROM {table}
                    WHERE snapshot_id = ?
                    """,
                    (
                        snapshot_id,
                    ),
                )
