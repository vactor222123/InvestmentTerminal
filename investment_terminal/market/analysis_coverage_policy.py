"""
Analysis-coverage policy for recommendation safety controls.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.services.fundamental_score_service import (
    FundamentalScoreResult,
)


FULL = "FULL"
REDUCED = "REDUCED"
INSUFFICIENT = "INSUFFICIENT"

SUPPORTED_COVERAGE_LEVELS = (
    FULL,
    REDUCED,
    INSUFFICIENT,
)

SPECIALIZED_BANK_WARNING = (
    "Specialized bank metrics are not yet available; "
    "the score uses a reduced generic metric set."
)


@dataclass(frozen=True, slots=True)
class AnalysisCoverageAssessment:
    """Structured assessment of analytical metric coverage."""

    level: str
    recommendation_cap: str | None
    allocation_eligible: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        normalized_level = self.level.strip().upper()

        if normalized_level not in SUPPORTED_COVERAGE_LEVELS:
            raise ValueError(
                "level must be one of: "
                + ", ".join(SUPPORTED_COVERAGE_LEVELS)
            )

        if (
            self.recommendation_cap is not None
            and (
                not isinstance(self.recommendation_cap, str)
                or not self.recommendation_cap.strip()
            )
        ):
            raise ValueError(
                "recommendation_cap must be a non-empty string or None"
            )

        if not isinstance(self.allocation_eligible, bool):
            raise TypeError(
                "allocation_eligible must be a bool"
            )

        if not isinstance(self.reasons, tuple):
            raise TypeError(
                "reasons must be a tuple"
            )

        if any(
            not isinstance(reason, str)
            or not reason.strip()
            for reason in self.reasons
        ):
            raise ValueError(
                "reasons must contain only non-empty strings"
            )

        object.__setattr__(
            self,
            "level",
            normalized_level,
        )
        object.__setattr__(
            self,
            "recommendation_cap",
            (
                self.recommendation_cap.strip().upper()
                if self.recommendation_cap is not None
                else None
            ),
        )
        object.__setattr__(
            self,
            "reasons",
            tuple(
                reason.strip()
                for reason in self.reasons
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "recommendation_cap": self.recommendation_cap,
            "allocation_eligible": self.allocation_eligible,
            "reasons": list(self.reasons),
        }


class AnalysisCoveragePolicy:
    """
    Classify whether current metrics are sufficient for recommendations.

    A high numerical confidence score does not automatically mean that
    the analytical framework is complete. Reduced-model coverage is
    therefore handled separately from ordinary missing-field quality.
    """

    MINIMUM_APPLICABLE_MAXIMUM = 50.0
    MINIMUM_DATA_QUALITY_FACTOR = 0.75

    def assess(
        self,
        fundamental_score: FundamentalScoreResult,
    ) -> AnalysisCoverageAssessment:
        if not isinstance(
            fundamental_score,
            FundamentalScoreResult,
        ):
            raise TypeError(
                "fundamental_score must be a FundamentalScoreResult"
            )

        applicable_maximum = self._applicable_maximum(
            fundamental_score
        )
        reasons: list[str] = []

        has_specialized_bank_gap = (
            SPECIALIZED_BANK_WARNING
            in fundamental_score.risk_factors
        )

        if has_specialized_bank_gap:
            reasons.append(
                "Specialized bank metrics are not yet available."
            )

        if (
            fundamental_score.data_quality_factor
            < self.MINIMUM_DATA_QUALITY_FACTOR
        ):
            reasons.append(
                "Applicable fundamental data coverage is below 75%."
            )

        if (
            applicable_maximum
            < self.MINIMUM_APPLICABLE_MAXIMUM
        ):
            reasons.append(
                "The active fundamental framework covers fewer than "
                "50 of 100 generic score points."
            )

        if (
            fundamental_score.data_quality_factor
            < self.MINIMUM_DATA_QUALITY_FACTOR
            or applicable_maximum
            < self.MINIMUM_APPLICABLE_MAXIMUM
        ):
            return AnalysisCoverageAssessment(
                level=INSUFFICIENT,
                recommendation_cap="AVOID",
                allocation_eligible=False,
                reasons=tuple(reasons),
            )

        if has_specialized_bank_gap:
            return AnalysisCoverageAssessment(
                level=REDUCED,
                recommendation_cap="WATCH",
                allocation_eligible=False,
                reasons=tuple(reasons),
            )

        return AnalysisCoverageAssessment(
            level=FULL,
            recommendation_cap=None,
            allocation_eligible=True,
            reasons=(),
        )

    @staticmethod
    def _applicable_maximum(
        fundamental_score: FundamentalScoreResult,
    ) -> float:
        breakdown = fundamental_score.breakdown

        return sum(
            (
                breakdown.growth_max,
                breakdown.profitability_max,
                breakdown.balance_sheet_max,
                breakdown.cash_flow_max,
                breakdown.valuation_max,
                breakdown.shareholder_returns_max,
            )
        )