"""
Transparent descriptive statistics for eligible historical price outcomes.
"""

from dataclasses import dataclass
from math import isfinite
from statistics import mean, median, stdev
from typing import Any

from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcome,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeDescriptiveSummary:
    """
    Descriptive statistics for raw historical price-change fractions.

    Positive/negative/zero counts describe price movement only. They do not
    encode recommendation success, failure, accuracy, effectiveness, or
    predictive confidence.
    """

    count: int
    mean_price_change_fraction: float
    median_price_change_fraction: float
    minimum_price_change_fraction: float
    maximum_price_change_fraction: float
    sample_standard_deviation: float | None
    positive_movement_count: int
    negative_movement_count: int
    zero_movement_count: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.count, bool)
            or not isinstance(self.count, int)
            or self.count <= 0
        ):
            raise ValueError(
                "count must be a positive integer"
            )

        for field_name in (
            "mean_price_change_fraction",
            "median_price_change_fraction",
            "minimum_price_change_fraction",
            "maximum_price_change_fraction",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(float(value))
            ):
                raise ValueError(
                    f"{field_name} must be a finite number"
                )
            object.__setattr__(
                self,
                field_name,
                float(value),
            )

        if self.sample_standard_deviation is not None:
            value = self.sample_standard_deviation
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(float(value))
                or float(value) < 0.0
            ):
                raise ValueError(
                    "sample_standard_deviation must be a finite "
                    "non-negative number or None"
                )
            object.__setattr__(
                self,
                "sample_standard_deviation",
                float(value),
            )

        for field_name in (
            "positive_movement_count",
            "negative_movement_count",
            "zero_movement_count",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if (
            self.positive_movement_count
            + self.negative_movement_count
            + self.zero_movement_count
            != self.count
        ):
            raise ValueError(
                "movement counts must sum to count"
            )

        if (
            self.minimum_price_change_fraction
            > self.maximum_price_change_fraction
        ):
            raise ValueError(
                "minimum_price_change_fraction must not exceed maximum"
            )

        if (
            self.mean_price_change_fraction
            < self.minimum_price_change_fraction
            or self.mean_price_change_fraction
            > self.maximum_price_change_fraction
        ):
            raise ValueError(
                "mean_price_change_fraction must lie within min/max"
            )

        if (
            self.median_price_change_fraction
            < self.minimum_price_change_fraction
            or self.median_price_change_fraction
            > self.maximum_price_change_fraction
        ):
            raise ValueError(
                "median_price_change_fraction must lie within min/max"
            )

        if self.count == 1 and self.sample_standard_deviation is not None:
            raise ValueError(
                "sample_standard_deviation must be None for one observation"
            )
        if self.count > 1 and self.sample_standard_deviation is None:
            raise ValueError(
                "sample_standard_deviation is required for multiple observations"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "mean_price_change_fraction": self.mean_price_change_fraction,
            "median_price_change_fraction": self.median_price_change_fraction,
            "minimum_price_change_fraction": self.minimum_price_change_fraction,
            "maximum_price_change_fraction": self.maximum_price_change_fraction,
            "sample_standard_deviation": self.sample_standard_deviation,
            "positive_movement_count": self.positive_movement_count,
            "negative_movement_count": self.negative_movement_count,
            "zero_movement_count": self.zero_movement_count,
        }


class HistoricalOutcomeDescriptiveSummaryService:
    """Calculate pure descriptive statistics from complete outcome values."""

    def summarize(
        self,
        *,
        outcomes: tuple[HistoricalRecommendationOutcome, ...],
    ) -> HistoricalOutcomeDescriptiveSummary | None:
        if not isinstance(outcomes, tuple):
            raise TypeError(
                "outcomes must be a tuple"
            )

        for outcome in outcomes:
            if not isinstance(
                outcome,
                HistoricalRecommendationOutcome,
            ):
                raise TypeError(
                    "outcomes must contain only "
                    "HistoricalRecommendationOutcome values"
                )

        if not outcomes:
            return None

        values = tuple(
            outcome.price_change_fraction
            for outcome in outcomes
        )

        return HistoricalOutcomeDescriptiveSummary(
            count=len(values),
            mean_price_change_fraction=mean(values),
            median_price_change_fraction=median(values),
            minimum_price_change_fraction=min(values),
            maximum_price_change_fraction=max(values),
            sample_standard_deviation=(
                None
                if len(values) == 1
                else stdev(values)
            ),
            positive_movement_count=sum(
                1
                for value in values
                if value > 0.0
            ),
            negative_movement_count=sum(
                1
                for value in values
                if value < 0.0
            ),
            zero_movement_count=sum(
                1
                for value in values
                if value == 0.0
            ),
        )
