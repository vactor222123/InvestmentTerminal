"""
Pure comparator for normalized historical recommendations.
"""

from investment_terminal.history.historical_comparison_models import (
    RecommendationChange,
    ScalarChange,
)
from investment_terminal.history.historical_recommendation_models import (
    HistoricalRecommendation,
)


class HistoricalRecommendationsComparator:
    """Compare recommendations strictly by stable recommendation_key."""

    def compare(
        self,
        *,
        previous: tuple[HistoricalRecommendation, ...],
        current: tuple[HistoricalRecommendation, ...],
    ) -> tuple[RecommendationChange, ...]:
        previous_by_key = self._index(
            previous,
            field_name="previous",
        )
        current_by_key = self._index(
            current,
            field_name="current",
        )

        keys = tuple(
            sorted(
                set(
                    previous_by_key
                )
                | set(
                    current_by_key
                )
            )
        )

        return tuple(
            self._compare_key(
                key,
                previous_by_key.get(
                    key
                ),
                current_by_key.get(
                    key
                ),
            )
            for key in keys
        )

    @classmethod
    def _compare_key(
        cls,
        key: str,
        previous: HistoricalRecommendation | None,
        current: HistoricalRecommendation | None,
    ) -> RecommendationChange:
        if previous is None:
            change_type = "ADDED"
        elif current is None:
            change_type = "REMOVED"
        elif cls._equivalent(
            previous,
            current,
        ):
            change_type = "UNCHANGED"
        else:
            change_type = "CHANGED"

        return RecommendationChange(
            recommendation_key=key,
            change_type=change_type,
            previous=(
                None
                if previous is None
                else previous.comparison_payload()
            ),
            current=(
                None
                if current is None
                else current.comparison_payload()
            ),
            score=ScalarChange.between(
                None
                if previous is None
                else previous.score,
                None
                if current is None
                else current.score,
            ),
            confidence=ScalarChange.between(
                None
                if previous is None
                else previous.confidence,
                None
                if current is None
                else current.confidence,
            ),
        )

    @staticmethod
    def _equivalent(
        previous: HistoricalRecommendation,
        current: HistoricalRecommendation,
    ) -> bool:
        return (
            previous.comparison_payload()
            == current.comparison_payload()
            and previous.score
            == current.score
            and previous.confidence
            == current.confidence
        )

    @staticmethod
    def _index(
        recommendations: object,
        *,
        field_name: str,
    ) -> dict[str, HistoricalRecommendation]:
        if not isinstance(
            recommendations,
            tuple,
        ):
            raise TypeError(
                f"{field_name} must be a tuple"
            )

        indexed: dict[
            str,
            HistoricalRecommendation,
        ] = {}

        for recommendation in recommendations:
            if not isinstance(
                recommendation,
                HistoricalRecommendation,
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    "HistoricalRecommendation values"
                )

            key = recommendation.recommendation_key
            if key in indexed:
                raise ValueError(
                    f"{field_name} contains duplicate recommendation_key {key}"
                )

            indexed[
                key
            ] = recommendation

        return indexed
