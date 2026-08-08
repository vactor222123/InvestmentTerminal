"""
Pure descriptive aggregation for historical recommendation outcome observations.
"""

from dataclasses import dataclass
from statistics import mean, median
from typing import Any

from investment_terminal.history.historical_outcome_models import (
    HistoricalRecommendationObservation,
)
from investment_terminal.history.historical_outcome_observation_service import (
    HistoricalOutcomeObservationResult,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeActionCount:
    """Count observations for one normalized recommendation action."""

    action: str
    count: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "action",
            normalize_required_text(
                self.action,
                field_name="action",
                uppercase=True,
            ),
        )
        if (
            isinstance(
                self.count,
                bool,
            )
            or not isinstance(
                self.count,
                int,
            )
            or self.count < 0
        ):
            raise ValueError(
                "count must be a non-negative integer"
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "action": self.action,
            "count": self.count,
        }


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeSummary:
    """
    Descriptive aggregate over outcome observations.

    `mean_price_change_fraction` and `median_price_change_fraction` are simple
    raw price-movement summaries over COMPLETE observations only. They are not
    portfolio performance, effectiveness, confidence, or causal metrics.
    """

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
        counts = (
            self.total_count,
            self.complete_count,
            self.partial_count,
            self.unavailable_count,
            self.not_mature_count,
        )

        if any(
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                int,
            )
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

        if self.total_count == 0:
            if self.coverage_fraction is not None:
                raise ValueError(
                    "coverage_fraction must be None when total_count is zero"
                )
        else:
            expected_coverage = (
                self.complete_count
                / self.total_count
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
        else:
            if (
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

        if any(
            not isinstance(
                item,
                HistoricalOutcomeActionCount,
            )
            for item in self.action_counts
        ):
            raise TypeError(
                "action_counts must contain HistoricalOutcomeActionCount values"
            )

        actions = tuple(
            item.action
            for item in self.action_counts
        )
        if actions != tuple(
            sorted(
                actions
            )
        ):
            raise ValueError(
                "action_counts must be ordered by action"
            )

        if len(
            set(
                actions
            )
        ) != len(
            actions
        ):
            raise ValueError(
                "action_counts must not contain duplicate actions"
            )

        if sum(
            item.count
            for item in self.action_counts
        ) > self.total_count:
            raise ValueError(
                "action_counts must not exceed total_count"
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
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
                "Raw close-price movement across COMPLETE observations only; "
                "not portfolio performance, recommendation effectiveness, "
                "confidence calibration, or evidence of causality"
            ),
        }


class HistoricalOutcomeAggregator:
    """Aggregate already-produced outcome observations without persistence."""

    def summarize(
        self,
        results: tuple[
            HistoricalOutcomeObservationResult,
            ...,
        ],
    ) -> HistoricalOutcomeSummary:
        if not isinstance(
            results,
            tuple,
        ):
            raise TypeError(
                "results must be a tuple"
            )

        if any(
            not isinstance(
                result,
                HistoricalOutcomeObservationResult,
            )
            for result in results
        ):
            raise TypeError(
                "results must contain only HistoricalOutcomeObservationResult values"
            )

        complete = tuple(
            result
            for result in results
            if result.observation.status
            == HistoricalRecommendationObservation.COMPLETE
        )
        partial_count = sum(
            1
            for result in results
            if result.observation.status
            == HistoricalRecommendationObservation.PARTIAL
        )
        unavailable_count = sum(
            1
            for result in results
            if result.observation.status
            == HistoricalRecommendationObservation.UNAVAILABLE
        )
        not_mature_count = sum(
            1
            for result in results
            if result.observation.status
            == HistoricalRecommendationObservation.NOT_MATURE
        )

        complete_movements = tuple(
            result.outcome.price_change_fraction
            for result in complete
            if result.outcome is not None
        )

        if len(
            complete_movements
        ) != len(
            complete
        ):
            raise ValueError(
                "COMPLETE observations must contain calculated outcomes"
            )

        action_map: dict[str, int] = {}
        for result in results:
            action = result.observation.action
            if action is None:
                continue

            normalized_action = normalize_required_text(
                action,
                field_name="action",
                uppercase=True,
            )
            action_map[
                normalized_action
            ] = (
                action_map.get(
                    normalized_action,
                    0,
                )
                + 1
            )

        total_count = len(
            results
        )
        complete_count = len(
            complete
        )

        return HistoricalOutcomeSummary(
            total_count=total_count,
            complete_count=complete_count,
            partial_count=partial_count,
            unavailable_count=unavailable_count,
            not_mature_count=not_mature_count,
            coverage_fraction=(
                None
                if total_count == 0
                else complete_count
                / total_count
            ),
            mean_price_change_fraction=(
                None
                if not complete_movements
                else mean(
                    complete_movements
                )
            ),
            median_price_change_fraction=(
                None
                if not complete_movements
                else median(
                    complete_movements
                )
            ),
            action_counts=tuple(
                HistoricalOutcomeActionCount(
                    action=action,
                    count=action_map[
                        action
                    ],
                )
                for action in sorted(
                    action_map
                )
            ),
        )
