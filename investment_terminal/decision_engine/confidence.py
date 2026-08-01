"""
Decision confidence calculations.
"""

from investment_terminal.decision_engine.decision_model import (
    DecisionConfidence,
)


class ConfidenceEngine:
    """
    Calculate confidence from data quality and missing fields.
    """

    @staticmethod
    def calculate(
        technical_quality: float,
        fundamental_quality: float,
        technical_missing_count: int = 0,
        fundamental_missing_count: int = 0,
    ) -> DecisionConfidence:
        """
        Calculate confidence for a combined decision.
        """
        ConfidenceEngine._validate_quality(
            technical_quality,
            field_name="technical_quality",
        )
        ConfidenceEngine._validate_quality(
            fundamental_quality,
            field_name="fundamental_quality",
        )

        for field_name, value in (
            (
                "technical_missing_count",
                technical_missing_count,
            ),
            (
                "fundamental_missing_count",
                fundamental_missing_count,
            ),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be "
                    "a non-negative integer"
                )

        base_score = (
            technical_quality
            + fundamental_quality
        ) / 2.0

        missing_data_penalty = min(
            (
                technical_missing_count
                + fundamental_missing_count
            )
            * 1.5,
            30.0,
        )

        confidence_score = max(
            base_score - missing_data_penalty,
            0.0,
        )

        return DecisionConfidence(
            score=round(confidence_score, 2),
            classification=(
                ConfidenceEngine.classify(
                    confidence_score
                )
            ),
            technical_data_quality=round(
                technical_quality,
                2,
            ),
            fundamental_data_quality=round(
                fundamental_quality,
                2,
            ),
            missing_data_penalty=round(
                missing_data_penalty,
                2,
            ),
        )

    @staticmethod
    def classify(score: float) -> str:
        """
        Classify confidence on a descriptive scale.
        """
        if score >= 90.0:
            return "VERY HIGH"

        if score >= 75.0:
            return "HIGH"

        if score >= 60.0:
            return "MODERATE"

        if score >= 40.0:
            return "LOW"

        return "VERY LOW"

    @staticmethod
    def _validate_quality(
        value: object,
        field_name: str,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            raise ValueError(
                f"{field_name} must be numeric"
            )

        if not 0.0 <= float(value) <= 100.0:
            raise ValueError(
                f"{field_name} must be between 0 and 100"
            )