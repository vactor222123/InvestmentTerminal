"""
Aggregate orchestration service for historical snapshot comparisons.
"""

from investment_terminal.history.historical_comparison_facts_repository import (
    HistoricalComparisonFactsRepository,
)
from investment_terminal.history.historical_comparison_models import (
    SnapshotComparison,
)
from investment_terminal.history.historical_deployment_comparator import (
    HistoricalDeploymentComparator,
)
from investment_terminal.history.historical_deployment_repository import (
    HistoricalDeploymentRepository,
)
from investment_terminal.history.historical_holdings_comparator import (
    HistoricalHoldingsComparator,
)
from investment_terminal.history.historical_holdings_repository import (
    HistoricalHoldingsRepository,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_portfolio_summary_comparator import (
    HistoricalPortfolioSummaryComparator,
)
from investment_terminal.history.historical_portfolio_summary_repository import (
    HistoricalPortfolioSummaryRepository,
)
from investment_terminal.history.historical_recommendations_comparator import (
    HistoricalRecommendationsComparator,
)
from investment_terminal.history.historical_recommendations_repository import (
    HistoricalRecommendationsRepository,
)
from investment_terminal.history.historical_snapshot_compatibility import (
    HistoricalSnapshotCompatibilityService,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)


class HistoricalSnapshotComparisonService:
    """
    Orchestrate one complete snapshot comparison using typed History boundaries.

    The service contains no persistence queries and no leaf comparison logic.
    """

    def __init__(
        self,
        *,
        snapshot_repository: HistoricalSnapshotRepository,
        import_state_repository: HistoricalImportStateRepository,
        facts_repository: HistoricalComparisonFactsRepository,
        summary_repository: HistoricalPortfolioSummaryRepository,
        holdings_repository: HistoricalHoldingsRepository,
        recommendations_repository: HistoricalRecommendationsRepository,
        deployment_repository: HistoricalDeploymentRepository,
        compatibility_service: HistoricalSnapshotCompatibilityService,
        summary_comparator: HistoricalPortfolioSummaryComparator | None = None,
        holdings_comparator: HistoricalHoldingsComparator | None = None,
        recommendations_comparator: HistoricalRecommendationsComparator | None = None,
        deployment_comparator: HistoricalDeploymentComparator | None = None,
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
                "facts_repository",
                facts_repository,
                HistoricalComparisonFactsRepository,
            ),
            (
                "summary_repository",
                summary_repository,
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
                "compatibility_service",
                compatibility_service,
                HistoricalSnapshotCompatibilityService,
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

        optional_dependencies = (
            (
                "summary_comparator",
                summary_comparator,
                HistoricalPortfolioSummaryComparator,
            ),
            (
                "holdings_comparator",
                holdings_comparator,
                HistoricalHoldingsComparator,
            ),
            (
                "recommendations_comparator",
                recommendations_comparator,
                HistoricalRecommendationsComparator,
            ),
            (
                "deployment_comparator",
                deployment_comparator,
                HistoricalDeploymentComparator,
            ),
        )

        for field_name, value, expected_type in optional_dependencies:
            if (
                value is not None
                and not isinstance(
                    value,
                    expected_type,
                )
            ):
                raise TypeError(
                    f"{field_name} must be a {expected_type.__name__} or None"
                )

        self.snapshot_repository = snapshot_repository
        self.import_state_repository = import_state_repository
        self.facts_repository = facts_repository
        self.summary_repository = summary_repository
        self.holdings_repository = holdings_repository
        self.recommendations_repository = recommendations_repository
        self.deployment_repository = deployment_repository
        self.compatibility_service = compatibility_service
        self.summary_comparator = (
            summary_comparator
            or HistoricalPortfolioSummaryComparator()
        )
        self.holdings_comparator = (
            holdings_comparator
            or HistoricalHoldingsComparator()
        )
        self.recommendations_comparator = (
            recommendations_comparator
            or HistoricalRecommendationsComparator()
        )
        self.deployment_comparator = (
            deployment_comparator
            or HistoricalDeploymentComparator()
        )

    def compare(
        self,
        *,
        earlier_snapshot_id: str,
        later_snapshot_id: str,
    ) -> SnapshotComparison:
        """Compare two registered snapshots in explicit chronological roles."""
        earlier_snapshot = self.snapshot_repository.require(
            earlier_snapshot_id
        )
        later_snapshot = self.snapshot_repository.require(
            later_snapshot_id
        )

        earlier_state = self.import_state_repository.require(
            earlier_snapshot.snapshot_id
        )
        later_state = self.import_state_repository.require(
            later_snapshot.snapshot_id
        )

        earlier_facts = self.facts_repository.get(
            earlier_snapshot.snapshot_id
        )
        later_facts = self.facts_repository.get(
            later_snapshot.snapshot_id
        )

        compatibility = self.compatibility_service.assess(
            earlier_snapshot=earlier_snapshot,
            later_snapshot=later_snapshot,
            earlier_state=earlier_state,
            later_state=later_state,
            earlier_facts=earlier_facts,
            later_facts=later_facts,
        )

        notes = (
            compatibility.blockers
            + compatibility.warnings
        )

        if not compatibility.may_compare:
            return SnapshotComparison(
                earlier_snapshot_id=earlier_snapshot.snapshot_id,
                later_snapshot_id=later_snapshot.snapshot_id,
                compatibility_status=compatibility.status,
                compatibility_notes=notes,
                portfolio_summary=None,
                holdings=(),
                recommendations=(),
                deployment=(),
            )

        summary_change = self.summary_comparator.compare(
            previous=self.summary_repository.get(
                earlier_snapshot.snapshot_id
            ),
            current=self.summary_repository.get(
                later_snapshot.snapshot_id
            ),
        )
        holdings_changes = self.holdings_comparator.compare(
            previous=self.holdings_repository.list_for_snapshot(
                earlier_snapshot.snapshot_id
            ),
            current=self.holdings_repository.list_for_snapshot(
                later_snapshot.snapshot_id
            ),
        )
        recommendation_changes = (
            self.recommendations_comparator.compare(
                previous=(
                    self.recommendations_repository.list_for_snapshot(
                        earlier_snapshot.snapshot_id
                    )
                ),
                current=(
                    self.recommendations_repository.list_for_snapshot(
                        later_snapshot.snapshot_id
                    )
                ),
            )
        )
        deployment_changes = self.deployment_comparator.compare(
            previous=self.deployment_repository.list_for_snapshot(
                earlier_snapshot.snapshot_id
            ),
            current=self.deployment_repository.list_for_snapshot(
                later_snapshot.snapshot_id
            ),
        )

        return SnapshotComparison(
            earlier_snapshot_id=earlier_snapshot.snapshot_id,
            later_snapshot_id=later_snapshot.snapshot_id,
            compatibility_status=compatibility.status,
            compatibility_notes=notes,
            portfolio_summary=summary_change,
            holdings=holdings_changes,
            recommendations=recommendation_changes,
            deployment=deployment_changes,
        )
