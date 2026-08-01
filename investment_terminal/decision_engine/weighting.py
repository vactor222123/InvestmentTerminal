"""
Decision-score weighting components.
"""

from dataclasses import dataclass
from math import isfinite
from numbers import Real


@dataclass(frozen=True, slots=True)
class DecisionWeights:
    """
    Weights used to combine analysis scores.
    """

    technical: float = 0.40
    fundamental: float = 0.60

    def __post_init__(self) -> None:
        for field_name in (
            "technical",
            "fundamental",
        ):
            value = getattr(self, field_name)

            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not isfinite(float(value))
            ):
                raise ValueError(
                    f"{field_name} weight must be "
                    "a finite number"
                )

            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(
                    f"{field_name} weight must be "
                    "between 0 and 1"
                )

        total = self.technical + self.fundamental

        if abs(total - 1.0) > 0.0001:
            raise ValueError(
                "Decision weights must sum to 1.0"
            )


class DecisionWeighting:
    """
    Combine independent analysis scores.
    """

    @staticmethod
    def calculate_overall(
        technical_score: float,
        fundamental_score: float,
        weights: DecisionWeights,
    ) -> float:
        """
        Calculate the weighted overall score.
        """
        DecisionWeighting._validate_score(
            technical_score,
            field_name="technical_score",
        )
        DecisionWeighting._validate_score(
            fundamental_score,
            field_name="fundamental_score",
        )

        if not isinstance(weights, DecisionWeights):
            raise TypeError(
                "weights must be DecisionWeights"
            )

        result = (
            technical_score * weights.technical
            + fundamental_score * weights.fundamental
        )

        return round(result, 2)

    @staticmethod
    def _validate_score(
        value: object,
        field_name: str,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
        ):
            raise ValueError(
                f"{field_name} must be a finite number"
            )

        if not 0.0 <= float(value) <= 100.0:
            raise ValueError(
                f"{field_name} must be between 0 and 100"
            )