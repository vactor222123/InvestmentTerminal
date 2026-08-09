"""
Methodology-aware descriptive aggregation for historical outcome observations.
"""

from dataclasses import dataclass
from statistics import mean, median
from typing import Any

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.history.historical_outcome_aggregation import (
    HistoricalOutcomeActionCount,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalRecommendationObservation,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalOutcomeMethodology,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class HistoricalMethodologyOutcomeSummary:
    """
    Descriptive aggregate for one exact methodology identity.

    Raw price movement summaries use COMPLETE observations only and must not be
    interpreted as portfolio performance, effectiveness, confidence, or causality.
    """

    methodology: HistoricalOutcomeMethodology
    total_count: int
    complete_count: int
    partial_count: int
    unavailable_count: int
    not_mature_count: int
    coverage_fraction: float | None
    mean_price_change_fraction: float | None
    median_price_change_fraction: float | None
    action_counts: tuple[HistoricalOutcomeActionCount, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.methodology,
            HistoricalOutcomeMethodology,
        ):
            raise TypeError(
                "methodology must be a HistoricalOutcomeMethodology"
            )

        counts = (
            self.total_count,
            self.complete_count,
            self.partial_count,
            self.unavailable_count,
            self.not_mature_count,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in counts
        ):
            raise ValueError(
                "summary counts must be non-negative integers"
            )

        if (
            self.complete_count
            + self.partial_count
            + self.unavailable_count
            + self.not_mature_count
            != self.total_count
        ):
            raise ValueError(
                "status counts must sum to total_count"
            )

        expected_coverage = (
            None
            if self.total_count == 0
            else self.complete_count / self.total_count
        )
        if self.coverage_fraction != expected_coverage:
            raise ValueError(
                "coverage_fraction must equal complete_count / total_count"
            )

        if self.complete_count == 0:
            if (
                self.mean_price_change_fraction is not None
                or self.median_price_change_fraction is not None
            ):
                raise ValueError(
                    "price-change summaries require COMPLETE observations"
                )
        elif (
            self.mean_price_change_fraction is None
            or self.median_price_change_fraction is None
        ):
            raise ValueError(
                "COMPLETE observations require mean and median summaries"
            )

        if not isinstance(
            self.action_counts,
            tuple,
        ):
            raise TypeError(
                "action_counts must be a tuple"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "methodology": self.methodology.to_dict(),
            "total_count": self.total_count,
            "complete_count": self.complete_count,
            "partial_count": self.partial_count,
            "unavailable_count": self.unavailable_count,
            "not_mature_count": self.not_mature_count,
            "coverage_fraction": self.coverage_fraction,
            "mean_price_change_fraction": self.mean_price_change_fraction,
            "median_price_change_fraction": self.median_price_change_fraction,
            "action_counts": [
                item.to_dict()
                for item in self.action_counts
            ],
            "metric_semantics": (
                "Raw close-price movement across COMPLETE observations for one "
                "exact methodology identity only; not portfolio performance, "
                "recommendation effectiveness, confidence calibration, or causality"
            ),
        }


class HistoricalMethodologyOutcomeAggregator:
    """
    Aggregate methodology-aware observations without mixing identities.
    """

    def summarize_one(
        self,
        results: tuple[HistoricalMethodologyAwareObservationResult, ...],
    ) -> HistoricalMethodologyOutcomeSummary:
        self._validate_results(results)

        if not results:
            raise ValueError(
                "summarize_one requires at least one observation"
            )

        methodology = results[0].methodology
        if any(
            result.methodology.identity_key != methodology.identity_key
            for result in results
        ):
            raise ValueError(
                "cannot aggregate mixed methodology identities"
            )

        complete = tuple(
            result
            for result in results
            if result.observation.status
            == HistoricalRecommendationObservation.COMPLETE
        )
        complete_movements = tuple(
            result.outcome.price_change_fraction
            for result in complete
            if result.outcome is not None
        )

        if len(complete_movements) != len(complete):
            raise ValueError(
                "COMPLETE observations must contain calculated outcomes"
            )

        action_map: dict[str, int] = {}
        for result in results:
            action = result.observation.action
            if action is None:
                continue
            normalized = normalize_required_text(
                action,
                field_name="action",
                uppercase=True,
            )
            action_map[normalized] = action_map.get(normalized, 0) + 1

        total_count = len(results)
        complete_count = len(complete)
        partial_count = sum(
            result.observation.status
            == HistoricalRecommendationObservation.PARTIAL
            for result in results
        )
        unavailable_count = sum(
            result.observation.status
            == HistoricalRecommendationObservation.UNAVAILABLE
            for result in results
        )
        not_mature_count = sum(
            result.observation.status
            == HistoricalRecommendationObservation.NOT_MATURE
            for result in results
        )

        return HistoricalMethodologyOutcomeSummary(
            methodology=methodology,
            total_count=total_count,
            complete_count=complete_count,
            partial_count=partial_count,
            unavailable_count=unavailable_count,
            not_mature_count=not_mature_count,
            coverage_fraction=complete_count / total_count,
            mean_price_change_fraction=(
                None if not complete_movements else mean(complete_movements)
            ),
            median_price_change_fraction=(
                None if not complete_movements else median(complete_movements)
            ),
            action_counts=tuple(
                HistoricalOutcomeActionCount(
                    action=action,
                    count=action_map[action],
                )
                for action in sorted(action_map)
            ),
        )

    def summarize_grouped(
        self,
        results: tuple[HistoricalMethodologyAwareObservationResult, ...],
    ) -> tuple[HistoricalMethodologyOutcomeSummary, ...]:
        self._validate_results(results)

        groups: dict[
            str,
            list[HistoricalMethodologyAwareObservationResult],
        ] = {}
        for result in results:
            groups.setdefault(
                result.methodology.identity_key,
                [],
            ).append(result)

        return tuple(
            self.summarize_one(
                tuple(groups[identity])
            )
            for identity in sorted(groups)
        )

    @staticmethod
    def _validate_results(
        results: tuple[HistoricalMethodologyAwareObservationResult, ...],
    ) -> None:
        if not isinstance(results, tuple):
            raise TypeError(
                "results must be a tuple"
            )
        if any(
            not isinstance(
                result,
                HistoricalMethodologyAwareObservationResult,
            )
            for result in results
        ):
            raise TypeError(
                "results must contain only "
                "HistoricalMethodologyAwareObservationResult values"
            )
