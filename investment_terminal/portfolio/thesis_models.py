"""
Structured investment thesis models.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.portfolio.recommendation_models import (
    CandidateRecommendation,
)


@dataclass(frozen=True, slots=True)
class InvestmentThesis:
    """
    Human-readable investment thesis for one ranked candidate.
    """

    recommendation: CandidateRecommendation
    headline: str
    thesis: str
    strengths: tuple[str, ...]
    risks: tuple[str, ...]
    action: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.recommendation,
            CandidateRecommendation,
        ):
            raise TypeError(
                "recommendation must be a "
                "CandidateRecommendation"
            )

        for field_name in (
            "headline",
            "thesis",
            "action",
        ):
            normalized = self._normalize_text(
                getattr(self, field_name),
                field_name=field_name,
            )

            object.__setattr__(
                self,
                field_name,
                normalized,
            )

        self._validate_text_collection(
            self.strengths,
            field_name="strengths",
            allow_empty=False,
        )
        self._validate_text_collection(
            self.risks,
            field_name="risks",
            allow_empty=True,
        )

    @property
    def rank(self) -> int:
        return self.recommendation.rank

    @property
    def symbol(self) -> str:
        return self.recommendation.symbol

    @property
    def currency(self) -> str:
        return self.recommendation.currency

    @property
    def recommendation_label(self) -> str:
        return self.recommendation.recommendation

    @property
    def overall_score(self) -> float:
        return self.recommendation.overall_score

    @property
    def confidence_score(self) -> float:
        return self.recommendation.confidence_score

    @property
    def risk_level(self) -> str:
        return self.recommendation.risk_level

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the thesis to JSON-ready data.
        """
        return {
            "rank": self.rank,
            "symbol": self.symbol,
            "currency": self.currency,
            "recommendation": self.recommendation_label,
            "overall_score": self.overall_score,
            "confidence_score": self.confidence_score,
            "risk_level": self.risk_level,
            "headline": self.headline,
            "thesis": self.thesis,
            "strengths": list(self.strengths),
            "risks": list(self.risks),
            "action": self.action,
            "recommendation_context": (
                self.recommendation.to_dict()
            ),
        }

    @staticmethod
    def _normalize_text(
        value: object,
        field_name: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} must be a non-empty string"
            )

        return value.strip()

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
class PortfolioThesisResult:
    """
    Investment theses for a complete ranked universe.
    """

    schema_version: str
    generated_at: datetime
    theses: tuple[InvestmentThesis, ...]

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

        if not isinstance(self.theses, tuple):
            raise TypeError(
                "theses must be a tuple"
            )

        if not self.theses:
            raise ValueError(
                "theses must not be empty"
            )

        if any(
            not isinstance(
                thesis,
                InvestmentThesis,
            )
            for thesis in self.theses
        ):
            raise TypeError(
                "theses must contain only "
                "InvestmentThesis objects"
            )

        symbols = [
            thesis.symbol
            for thesis in self.theses
        ]

        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "theses must contain unique symbols"
            )

        actual_ranks = [
            thesis.rank
            for thesis in self.theses
        ]
        expected_ranks = list(
            range(
                1,
                len(self.theses) + 1,
            )
        )

        if actual_ranks != expected_ranks:
            raise ValueError(
                "thesis ranks must be consecutive "
                "and start at one"
            )

        object.__setattr__(
            self,
            "schema_version",
            self.schema_version.strip(),
        )

    @property
    def universe_size(self) -> int:
        return len(self.theses)

    @property
    def top_thesis(self) -> InvestmentThesis:
        return self.theses[0]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert all theses to JSON-ready data.
        """
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at.isoformat(),
            "universe_size": self.universe_size,
            "top_symbol": self.top_thesis.symbol,
            "top_recommendation": (
                self.top_thesis.recommendation_label
            ),
            "theses": [
                thesis.to_dict()
                for thesis in self.theses
            ],
        }