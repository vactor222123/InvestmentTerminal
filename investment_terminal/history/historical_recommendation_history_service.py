"""
Application service for chronological historical recommendation state.
"""

from investment_terminal.history.historical_recommendation_transition_models import (
    HistoricalRecommendationState,
    HistoricalRecommendationTransition,
)
from investment_terminal.history.historical_recommendations_repository import (
    HistoricalRecommendationsRepository,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


class HistoricalRecommendationHistoryService:
    """
    Build chronological recommendation state and transitions from typed History.

    The service performs no SQL and no price/outcome calculation.
    """

    def __init__(
        self,
        *,
        snapshot_repository: HistoricalSnapshotRepository,
        recommendations_repository: HistoricalRecommendationsRepository,
    ) -> None:
        if not isinstance(
            snapshot_repository,
            HistoricalSnapshotRepository,
        ):
            raise TypeError(
                "snapshot_repository must be a HistoricalSnapshotRepository"
            )
        if not isinstance(
            recommendations_repository,
            HistoricalRecommendationsRepository,
        ):
            raise TypeError(
                "recommendations_repository must be a HistoricalRecommendationsRepository"
            )

        self.snapshot_repository = snapshot_repository
        self.recommendations_repository = recommendations_repository

    def states_for(
        self,
        recommendation_key: str,
    ) -> tuple[HistoricalRecommendationState, ...]:
        """
        Return one state per snapshot from the key's first observation onward.

        Snapshots before the key first appears are not represented as
        `present=False`, because absence before first observation does not prove
        that a recommendation previously existed.
        """
        normalized_key = normalize_required_text(
            recommendation_key,
            field_name="recommendation_key",
        )

        snapshots = self.snapshot_repository.list_all()
        states: list[HistoricalRecommendationState] = []
        has_been_observed = False

        for snapshot in snapshots:
            recommendations = (
                self.recommendations_repository.list_for_snapshot(
                    snapshot.snapshot_id
                )
            )
            by_key = {
                item.recommendation_key: item
                for item in recommendations
            }
            recommendation = by_key.get(
                normalized_key
            )

            if recommendation is None:
                if not has_been_observed:
                    continue

                states.append(
                    HistoricalRecommendationState(
                        snapshot_id=snapshot.snapshot_id,
                        generated_at=snapshot.generated_at,
                        recommendation_key=normalized_key,
                        present=False,
                    )
                )
                continue

            has_been_observed = True
            states.append(
                HistoricalRecommendationState(
                    snapshot_id=snapshot.snapshot_id,
                    generated_at=snapshot.generated_at,
                    recommendation_key=normalized_key,
                    present=True,
                    symbol=recommendation.symbol,
                    action=recommendation.action,
                    score=recommendation.score,
                    confidence=recommendation.confidence,
                )
            )

        return tuple(
            states
        )

    def transitions_for(
        self,
        recommendation_key: str,
    ) -> tuple[HistoricalRecommendationTransition, ...]:
        """Return deterministic chronological transitions for one stable key."""
        states = self.states_for(
            recommendation_key
        )

        if not states:
            return ()

        transitions = [
            HistoricalRecommendationTransition(
                recommendation_key=states[0].recommendation_key,
                transition_type=(
                    HistoricalRecommendationTransition.FIRST_OBSERVED
                ),
                previous=None,
                current=states[0],
                duration_seconds=None,
            )
        ]

        for previous, current in zip(
            states,
            states[1:],
        ):
            transitions.append(
                HistoricalRecommendationTransition(
                    recommendation_key=current.recommendation_key,
                    transition_type=self._classify(
                        previous=previous,
                        current=current,
                    ),
                    previous=previous,
                    current=current,
                    duration_seconds=(
                        current.generated_at
                        - previous.generated_at
                    ).total_seconds(),
                )
            )

        return tuple(
            transitions
        )

    @staticmethod
    def _classify(
        *,
        previous: HistoricalRecommendationState,
        current: HistoricalRecommendationState,
    ) -> str:
        if previous.present and not current.present:
            return HistoricalRecommendationTransition.DISAPPEARED

        if not previous.present and current.present:
            return HistoricalRecommendationTransition.REAPPEARED

        if not previous.present and not current.present:
            return HistoricalRecommendationTransition.UNCHANGED

        if previous.action != current.action:
            return HistoricalRecommendationTransition.ACTION_CHANGED

        if (
            previous.score != current.score
            or previous.confidence != current.confidence
        ):
            return HistoricalRecommendationTransition.METRICS_CHANGED

        if previous.symbol != current.symbol:
            return HistoricalRecommendationTransition.DESCRIPTIVE_CHANGED

        return HistoricalRecommendationTransition.UNCHANGED
