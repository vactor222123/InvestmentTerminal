"""
Safe application service for supported historical replay modes.
"""

from investment_terminal.history.historical_deployment_repository import (
    HistoricalDeploymentRepository,
)
from investment_terminal.history.historical_holdings_repository import (
    HistoricalHoldingsRepository,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_portfolio_summary_repository import (
    HistoricalPortfolioSummaryRepository,
)
from investment_terminal.history.historical_recommendations_repository import (
    HistoricalRecommendationsRepository,
)
from investment_terminal.history.historical_replay_models import (
    HistoricalReplayRequest,
    HistoricalReplayResult,
)
from investment_terminal.history.historical_review_package_loader import (
    HistoricalReviewPackageLoader,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_timeline_repository import (
    HistoricalTimelineRepository,
)


class HistoricalReplayService:
    """
    Replay exact archived evidence or a normalized historical projection.

    The service never recalculates history, never accesses external data and
    never mutates the archive or structured History projection.
    """

    NORMALIZED_VIEW_WARNING = (
        "Normalized historical view is a rebuildable SQLite projection; "
        "the archived Review Package remains canonical evidence"
    )

    def __init__(
        self,
        *,
        snapshot_repository: HistoricalSnapshotRepository,
        import_state_repository: HistoricalImportStateRepository,
        portfolio_summary_repository: HistoricalPortfolioSummaryRepository,
        holdings_repository: HistoricalHoldingsRepository,
        recommendations_repository: HistoricalRecommendationsRepository,
        deployment_repository: HistoricalDeploymentRepository,
        timeline_repository: HistoricalTimelineRepository,
        review_package_loader: HistoricalReviewPackageLoader,
    ) -> None:
        dependencies = (
            (
                "snapshot_repository",
                snapshot_repository,
                HistoricalSnapshotRepository,
            ),
            (
                "import_state_repository",
                import_state_repository,
                HistoricalImportStateRepository,
            ),
            (
                "portfolio_summary_repository",
                portfolio_summary_repository,
                HistoricalPortfolioSummaryRepository,
            ),
            (
                "holdings_repository",
                holdings_repository,
                HistoricalHoldingsRepository,
            ),
            (
                "recommendations_repository",
                recommendations_repository,
                HistoricalRecommendationsRepository,
            ),
            (
                "deployment_repository",
                deployment_repository,
                HistoricalDeploymentRepository,
            ),
            (
                "timeline_repository",
                timeline_repository,
                HistoricalTimelineRepository,
            ),
            (
                "review_package_loader",
                review_package_loader,
                HistoricalReviewPackageLoader,
            ),
        )

        for field_name, value, expected_type in dependencies:
            if not isinstance(
                value,
                expected_type,
            ):
                raise TypeError(
                    f"{field_name} must be a {expected_type.__name__}"
                )

        self.snapshot_repository = snapshot_repository
        self.import_state_repository = import_state_repository
        self.portfolio_summary_repository = (
            portfolio_summary_repository
        )
        self.holdings_repository = holdings_repository
        self.recommendations_repository = (
            recommendations_repository
        )
        self.deployment_repository = deployment_repository
        self.timeline_repository = timeline_repository
        self.review_package_loader = review_package_loader

    def replay(
        self,
        request: HistoricalReplayRequest,
    ) -> HistoricalReplayResult:
        """Execute one supported replay request."""
        if not isinstance(
            request,
            HistoricalReplayRequest,
        ):
            raise TypeError(
                "request must be a HistoricalReplayRequest"
            )

        if not request.is_supported:
            raise NotImplementedError(
                "Historical replay mode is defined but not supported: "
                f"{request.mode}"
            )

        snapshot = self.snapshot_repository.require(
            request.snapshot_id
        )

        if request.mode == HistoricalReplayRequest.EXACT_ARCHIVED_PACKAGE:
            return self._replay_exact(
                snapshot=snapshot,
                request=request,
            )

        if request.mode == HistoricalReplayRequest.NORMALIZED_HISTORICAL_VIEW:
            return self._replay_normalized(
                snapshot=snapshot,
                request=request,
            )

        raise RuntimeError(
            f"Unhandled supported historical replay mode: {request.mode}"
        )

    def _replay_exact(
        self,
        *,
        snapshot,
        request: HistoricalReplayRequest,
    ) -> HistoricalReplayResult:
        payload = self.review_package_loader.load(
            snapshot
        )

        return HistoricalReplayResult(
            snapshot_id=snapshot.snapshot_id,
            mode=request.mode,
            package_schema_version=snapshot.package_schema_version,
            evidence_checksum_sha256=snapshot.checksum_sha256,
            payload=payload,
            warnings=(),
        )

    def _replay_normalized(
        self,
        *,
        snapshot,
        request: HistoricalReplayRequest,
    ) -> HistoricalReplayResult:
        state = self.import_state_repository.require(
            snapshot.snapshot_id
        )
        summary = self.portfolio_summary_repository.get(
            snapshot.snapshot_id
        )
        holdings = self.holdings_repository.list_for_snapshot(
            snapshot.snapshot_id
        )
        recommendations = (
            self.recommendations_repository.list_for_snapshot(
                snapshot.snapshot_id
            )
        )
        deployment = self.deployment_repository.list_for_snapshot(
            snapshot.snapshot_id
        )
        timeline = self.timeline_repository.list_for_snapshot(
            snapshot.snapshot_id
        )

        warnings = [
            self.NORMALIZED_VIEW_WARNING,
        ]

        if state.status != "IMPORTED":
            warnings.append(
                "Snapshot structured import state is "
                f"{state.status}; normalized view may be incomplete"
            )

        payload = {
            "snapshot": snapshot.to_dict(),
            "import_state": state.to_dict(),
            "portfolio_summary": (
                None
                if summary is None
                else summary.to_dict()
            ),
            "holdings": [
                item.to_dict()
                for item in holdings
            ],
            "recommendations": [
                item.to_dict()
                for item in recommendations
            ],
            "deployment": [
                item.to_dict()
                for item in deployment
            ],
            "timeline_events": [
                item.to_dict()
                for item in timeline
            ],
        }

        return HistoricalReplayResult(
            snapshot_id=snapshot.snapshot_id,
            mode=request.mode,
            package_schema_version=snapshot.package_schema_version,
            evidence_checksum_sha256=snapshot.checksum_sha256,
            payload=payload,
            warnings=tuple(
                warnings
            ),
        )
