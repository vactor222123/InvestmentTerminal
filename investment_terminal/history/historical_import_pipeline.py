"""
End-to-end import pipeline for one archived historical snapshot.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from investment_terminal.history.historical_deployment_importer import (
    HistoricalDeploymentImporter,
)
from investment_terminal.history.historical_holdings_importer import (
    HistoricalHoldingsImporter,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
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
    """Import one archived Review Package into structured historical tables."""

    def __init__(
        self,
        *,
        store: HistoricalSQLiteStore,
        loader: HistoricalReviewPackageLoader,
        state_repository: HistoricalImportStateRepository | None = None,
        clock: Callable[[], datetime] | None = None,
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

        if (
            state_repository is not None
            and not isinstance(
                state_repository,
                HistoricalImportStateRepository,
            )
        ):
            raise TypeError(
                "state_repository must be a HistoricalImportStateRepository"
            )

        self.store = store
        self.loader = loader
        self.state_repository = state_repository
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
        self.deployment_importer = HistoricalDeploymentImporter(
            store
        )
        self.timeline_builder = HistoricalTimelineBuilder(
            store
        )
        self._clock = clock or (
            lambda: datetime.now(
                timezone.utc
            )
        )

    def import_snapshot(
        self,
        snapshot: HistoricalSnapshot,
    ) -> HistoricalImportResult:
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

        if self.state_repository is None:
            if self.repository.has_detail_import(
                snapshot.snapshot_id
            ):
                raise ValueError(
                    "Historical snapshot details have already been imported"
                )
            payload = self.loader.load(
                snapshot
            )
            return self._import_details(
                snapshot=snapshot,
                payload=payload,
            )

        state = self.state_repository.require(
            snapshot.snapshot_id
        )

        if state.status == "IMPORTED":
            raise ValueError(
                "Historical snapshot details have already been imported"
            )

        if state.status not in (
            "METADATA_ONLY",
            "FAILED",
        ):
            raise ValueError(
                "Historical snapshot import state is not ready for import: "
                f"{state.status}"
            )

        try:
            payload = self.loader.load(
                snapshot
            )
            self.state_repository.mark_verified(
                snapshot.snapshot_id,
                at=self._now(),
            )

            with self.store.transaction() as connection:
                self.state_repository.mark_importing(
                    snapshot.snapshot_id,
                    at=self._now(),
                    importer_version=snapshot.product_version,
                    connection=connection,
                )
                result = self._import_details(
                    snapshot=snapshot,
                    payload=payload,
                    connection=connection,
                )
                self.state_repository.mark_imported(
                    snapshot.snapshot_id,
                    at=self._now(),
                    connection=connection,
                )

            return result
        except BaseException as exc:
            current = self.state_repository.require(
                snapshot.snapshot_id
            )

            if current.status not in (
                "FAILED",
                "IMPORTED",
            ):
                reason = (
                    str(
                        exc
                    ).strip()
                    or exc.__class__.__name__
                )
                self.state_repository.mark_failed(
                    snapshot.snapshot_id,
                    reason=reason,
                    at=self._now(),
                )

            raise

    def _import_details(
        self,
        *,
        snapshot: HistoricalSnapshot,
        payload: dict,
        connection=None,
    ) -> HistoricalImportResult:
        if connection is None:
            with self.store.transaction() as owned_connection:
                return self._import_details(
                    snapshot=snapshot,
                    payload=payload,
                    connection=owned_connection,
                )

        self.summary_importer.import_summary(
            snapshot=snapshot,
            payload=payload,
            connection=connection,
        )
        holdings = self.holdings_importer.import_holdings(
            snapshot=snapshot,
            payload=payload,
            connection=connection,
        )
        recommendations = (
            self.recommendations_importer
            .import_recommendations(
                snapshot=snapshot,
                payload=payload,
                connection=connection,
            )
        )
        deployment = self.deployment_importer.import_deployment(
            snapshot=snapshot,
            payload=payload,
            connection=connection,
        )
        timeline_events = self.timeline_builder.build(
            snapshot,
            connection=connection,
        )

        return HistoricalImportResult(
            snapshot_id=snapshot.snapshot_id,
            holdings_imported=holdings,
            recommendations_imported=recommendations,
            deployment_imported=deployment,
            timeline_events_created=timeline_events,
        )

    def _now(
        self,
    ) -> datetime:
        value = self._clock()

        if (
            not isinstance(
                value,
                datetime,
            )
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "clock must return a timezone-aware datetime"
            )

        return value

    def _remove_partial_import(
        self,
        snapshot_id: str,
    ) -> None:
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
