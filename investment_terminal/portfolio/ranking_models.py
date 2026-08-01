"""
Structured portfolio ranking models.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.decision_engine.decision_model import (
    DecisionResult,
)


@dataclass(frozen=True, slots=True)
class RankingCandidate:
    """
    One ranked portfolio candidate.

    Analytical values are exposed as properties and remain sourced
    from the underlying DecisionResult.
    """

    rank: int
    decision: DecisionResult

    def __post_init__(self) -> None:
        if (
            isinstance(self.rank, bool)
            or not isinstance(self.rank, int)
            or self.rank < 1
        ):
            raise ValueError(
                "rank must be a positive integer"
            )

        if not isinstance(
            self.decision,
            DecisionResult,
        ):
            raise TypeError(
                "decision must be a DecisionResult"
            )

    @property
    def symbol(self) -> str:
        return self.decision.symbol

    @property
    def currency(self) -> str:
        return self.decision.currency

    @property
    def overall_score(self) -> float:
        return self.decision.scores.overall

    @property
    def confidence_score(self) -> float:
        return self.decision.confidence.score

    @property
    def fundamental_score(self) -> float:
        return self.decision.scores.fundamental

    @property
    def technical_score(self) -> float:
        return self.decision.scores.technical

    @property
    def classification(self) -> str:
        return self.decision.classification

    @property
    def business_quality(self) -> str:
        return self.decision.quality.business_quality

    @property
    def risk_level(self) -> str:
        return self.decision.quality.risk_level

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the candidate to a JSON-ready dictionary.
        """
        return {
            "rank": self.rank,
            "symbol": self.symbol,
            "currency": self.currency,
            "overall_score": self.overall_score,
            "confidence_score": self.confidence_score,
            "fundamental_score": self.fundamental_score,
            "technical_score": self.technical_score,
            "classification": self.classification,
            "business_quality": self.business_quality,
            "risk_level": self.risk_level,
            "decision": self.decision.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class RankingResult:
    """
    Ranked result for an analyzed asset universe.
    """

    schema_version: str
    generated_at: datetime
    candidates: tuple[RankingCandidate, ...]

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

        if not isinstance(self.candidates, tuple):
            raise TypeError(
                "candidates must be a tuple"
            )

        if not self.candidates:
            raise ValueError(
                "candidates must not be empty"
            )

        if any(
            not isinstance(
                candidate,
                RankingCandidate,
            )
            for candidate in self.candidates
        ):
            raise TypeError(
                "candidates must contain only "
                "RankingCandidate objects"
            )

        symbols = [
            candidate.symbol
            for candidate in self.candidates
        ]

        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "candidates must contain unique symbols"
            )

        expected_ranks = list(
            range(
                1,
                len(self.candidates) + 1,
            )
        )
        actual_ranks = [
            candidate.rank
            for candidate in self.candidates
        ]

        if actual_ranks != expected_ranks:
            raise ValueError(
                "candidate ranks must be consecutive "
                "and start at one"
            )

        object.__setattr__(
            self,
            "schema_version",
            self.schema_version.strip(),
        )

    @property
    def universe_size(self) -> int:
        return len(self.candidates)

    @property
    def top_candidate(self) -> RankingCandidate:
        return self.candidates[0]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the ranking to a JSON-ready dictionary.
        """
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at.isoformat(),
            "universe_size": self.universe_size,
            "top_symbol": self.top_candidate.symbol,
            "candidates": [
                candidate.to_dict()
                for candidate in self.candidates
            ],
        }