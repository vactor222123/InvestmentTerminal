"""
Structured portfolio recommendation models.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.portfolio.ranking_models import (
    RankingCandidate,
)


RECOMMENDATION_LABELS = (
    "STRONG_BUY",
    "BUY",
    "ACCUMULATE",
    "HOLD",
    "WATCH",
    "AVOID",
)


@dataclass(frozen=True, slots=True)
class CandidateRecommendation:
    """
    Contextual recommendation for one ranked candidate.
    """

    candidate: RankingCandidate
    recommendation: str
    rationale: tuple[str, ...]
    cautions: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.candidate,
            RankingCandidate,
        ):
            raise TypeError(
                "candidate must be a RankingCandidate"
            )

        normalized_recommendation = (
            self._normalize_recommendation(
                self.recommendation
            )
        )

        self._validate_text_collection(
            self.rationale,
            field_name="rationale",
            allow_empty=False,
        )
        self._validate_text_collection(
            self.cautions,
            field_name="cautions",
            allow_empty=True,
        )

        object.__setattr__(
            self,
            "recommendation",
            normalized_recommendation,
        )

    @property
    def rank(self) -> int:
        return self.candidate.rank

    @property
    def symbol(self) -> str:
        return self.candidate.symbol

    @property
    def currency(self) -> str:
        return self.candidate.currency

    @property
    def overall_score(self) -> float:
        return self.candidate.overall_score

    @property
    def confidence_score(self) -> float:
        return self.candidate.confidence_score

    @property
    def risk_level(self) -> str:
        return self.candidate.risk_level

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the recommendation to JSON-ready data.
        """
        return {
            "rank": self.rank,
            "symbol": self.symbol,
            "currency": self.currency,
            "recommendation": self.recommendation,
            "overall_score": self.overall_score,
            "confidence_score": self.confidence_score,
            "risk_level": self.risk_level,
            "rationale": list(self.rationale),
            "cautions": list(self.cautions),
            "candidate": self.candidate.to_dict(),
        }

    @staticmethod
    def _normalize_recommendation(
        value: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                "recommendation must be a non-empty string"
            )

        normalized = (
            value.strip()
            .upper()
            .replace(" ", "_")
        )

        if normalized not in RECOMMENDATION_LABELS:
            supported = ", ".join(
                RECOMMENDATION_LABELS
            )
            raise ValueError(
                "Unsupported recommendation "
                f"'{normalized}'. "
                f"Supported values: {supported}."
            )

        return normalized

    @staticmethod
    def _validate_text_collection(
        values: object,
        field_name: str,
        allow_empty: bool,
    ) -> None:
        if not isinstance(values, tuple):
            raise TypeError(
                f"{field_name} must be a tuple"
            )

        if not values and not allow_empty:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        if any(
            not isinstance(value, str)
            or not value.strip()
            for value in values
        ):
            raise ValueError(
                f"{field_name} must contain only "
                "non-empty strings"
            )


@dataclass(frozen=True, slots=True)
class PortfolioRecommendationResult:
    """
    Recommendation result for a ranked asset universe.
    """

    schema_version: str
    generated_at: datetime
    recommendations: tuple[
        CandidateRecommendation,
        ...
    ]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, str)
            or not self.schema_version.strip()
        ):
            raise ValueError(
                "schema_version must be a non-empty string"
            )

        if not isinstance(
            self.generated_at,
            datetime,
        ):
            raise TypeError(
                "generated_at must be a datetime"
            )

        if not isinstance(
            self.recommendations,
            tuple,
        ):
            raise TypeError(
                "recommendations must be a tuple"
            )

        if not self.recommendations:
            raise ValueError(
                "recommendations must not be empty"
            )

        if any(
            not isinstance(
                recommendation,
                CandidateRecommendation,
            )
            for recommendation
            in self.recommendations
        ):
            raise TypeError(
                "recommendations must contain only "
                "CandidateRecommendation objects"
            )

        symbols = [
            recommendation.symbol
            for recommendation
            in self.recommendations
        ]

        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "recommendations must contain "
                "unique symbols"
            )

        expected_ranks = list(
            range(
                1,
                len(self.recommendations) + 1,
            )
        )
        actual_ranks = [
            recommendation.rank
            for recommendation
            in self.recommendations
        ]

        if actual_ranks != expected_ranks:
            raise ValueError(
                "recommendation ranks must be "
                "consecutive and start at one"
            )

        object.__setattr__(
            self,
            "schema_version",
            self.schema_version.strip(),
        )

    @property
    def universe_size(self) -> int:
        return len(self.recommendations)

    @property
    def top_recommendation(
        self,
    ) -> CandidateRecommendation:
        return self.recommendations[0]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the complete result to JSON-ready data.
        """
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at.isoformat(),
            "universe_size": self.universe_size,
            "top_symbol": (
                self.top_recommendation.symbol
            ),
            "top_recommendation": (
                self.top_recommendation
                .recommendation
            ),
            "recommendations": [
                recommendation.to_dict()
                for recommendation
                in self.recommendations
            ],
        }