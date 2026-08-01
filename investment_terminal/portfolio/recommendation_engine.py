"""
Deterministic contextual recommendation engine.
"""

from datetime import datetime, timezone

from investment_terminal.portfolio.ranking_models import (
    RankingCandidate,
    RankingResult,
)
from investment_terminal.portfolio.recommendation_models import (
    CandidateRecommendation,
    PortfolioRecommendationResult,
)


class RecommendationEngine:
    """
    Convert a ranked universe into contextual recommendations.

    Recommendations are analytical screening labels. They are not
    personalized financial advice or automatic trading instructions.
    """

    SCHEMA_VERSION = "1.0"

    LABELS = (
        "STRONG_BUY",
        "BUY",
        "ACCUMULATE",
        "HOLD",
        "WATCH",
        "AVOID",
    )

    def recommend(
        self,
        ranking: RankingResult,
        generated_at: datetime | None = None,
    ) -> PortfolioRecommendationResult:
        """
        Produce one recommendation for every ranked candidate.
        """
        if not isinstance(ranking, RankingResult):
            raise TypeError(
                "ranking must be a RankingResult"
            )

        recommendation_time = self._resolve_generated_at(
            generated_at
        )

        recommendations = tuple(
            self._recommend_candidate(candidate)
            for candidate in ranking.candidates
        )

        return PortfolioRecommendationResult(
            schema_version=self.SCHEMA_VERSION,
            generated_at=recommendation_time,
            recommendations=recommendations,
        )

    def _recommend_candidate(
        self,
        candidate: RankingCandidate,
    ) -> CandidateRecommendation:
        decision = candidate.decision

        label = self._base_label(
            candidate.overall_score
        )

        label = self._apply_confidence_adjustment(
            label=label,
            confidence=candidate.confidence_score,
        )

        label = self._apply_risk_adjustment(
            label=label,
            risk_level=candidate.risk_level,
        )

        label = self._apply_valuation_adjustment(
            label=label,
            valuation=decision.quality.valuation,
        )

        label = self._apply_technical_adjustment(
            label=label,
            technical_condition=(
                decision.quality.technical_condition
            ),
        )

        rationale = self._build_rationale(
            candidate
        )
        cautions = self._build_cautions(
            candidate
        )

        return CandidateRecommendation(
            candidate=candidate,
            recommendation=label,
            rationale=rationale,
            cautions=cautions,
        )

    @staticmethod
    def _base_label(
        overall_score: float,
    ) -> str:
        if overall_score >= 85.0:
            return "STRONG_BUY"

        if overall_score >= 75.0:
            return "BUY"

        if overall_score >= 65.0:
            return "ACCUMULATE"

        if overall_score >= 50.0:
            return "HOLD"

        if overall_score >= 35.0:
            return "WATCH"

        return "AVOID"

    def _apply_confidence_adjustment(
        self,
        label: str,
        confidence: float,
    ) -> str:
        if confidence < 60.0:
            return "AVOID"

        if confidence < 75.0:
            return self._weaker_of(
                label,
                "WATCH",
            )

        if confidence < 85.0:
            return self._downgrade(
                label,
                steps=1,
            )

        return label

    def _apply_risk_adjustment(
        self,
        label: str,
        risk_level: str,
    ) -> str:
        normalized = risk_level.strip().upper()

        if normalized == "HIGH":
            return self._downgrade(
                label,
                steps=2,
            )

        if (
            normalized == "MEDIUM"
            and label == "STRONG_BUY"
        ):
            return self._downgrade(
                label,
                steps=1,
            )

        return label

    def _apply_valuation_adjustment(
        self,
        label: str,
        valuation: str,
    ) -> str:
        normalized = valuation.strip().upper()

        if normalized == "EXPENSIVE":
            return self._downgrade(
                label,
                steps=1,
            )

        return label

    def _apply_technical_adjustment(
        self,
        label: str,
        technical_condition: str,
    ) -> str:
        normalized = (
            technical_condition
            .strip()
            .upper()
        )

        if (
            normalized == "POSITIVE BUT EXTENDED"
            and label in {
                "STRONG_BUY",
                "BUY",
            }
        ):
            return self._downgrade(
                label,
                steps=1,
            )

        return label

    @staticmethod
    def _build_rationale(
        candidate: RankingCandidate,
    ) -> tuple[str, ...]:
        decision = candidate.decision
        rationale: list[str] = []

        if candidate.rank == 1:
            rationale.append(
                "This is the highest-ranked candidate "
                "in the analyzed universe."
            )
        else:
            rationale.append(
                f"This candidate ranks "
                f"#{candidate.rank} in the analyzed universe."
            )

        if candidate.overall_score >= 80.0:
            rationale.append(
                "The combined investment score is excellent."
            )
        elif candidate.overall_score >= 65.0:
            rationale.append(
                "The combined investment score is strong."
            )
        elif candidate.overall_score >= 50.0:
            rationale.append(
                "The combined investment score is balanced."
            )
        else:
            rationale.append(
                "The combined investment score is weak."
            )

        if (
            decision.quality.business_quality
            == "EXCELLENT"
        ):
            rationale.append(
                "Business quality is excellent."
            )
        elif (
            decision.quality.business_quality
            == "STRONG"
        ):
            rationale.append(
                "Business quality is strong."
            )

        if decision.quality.growth in {
            "VERY STRONG",
            "STRONG",
        }:
            rationale.append(
                f"Growth is "
                f"{decision.quality.growth.lower()}."
            )

        if decision.quality.valuation in {
            "ATTRACTIVE",
            "FAIR",
        }:
            rationale.append(
                f"Valuation is "
                f"{decision.quality.valuation.lower()}."
            )

        if decision.quality.financial_health == "STRONG":
            rationale.append(
                "Financial health is strong."
            )

        if candidate.confidence_score >= 90.0:
            rationale.append(
                "The recommendation is supported by "
                "high-quality data."
            )

        return tuple(rationale)

    @staticmethod
    def _build_cautions(
        candidate: RankingCandidate,
    ) -> tuple[str, ...]:
        decision = candidate.decision
        cautions: list[str] = []

        if candidate.risk_level == "HIGH":
            cautions.append(
                "The current risk level is high."
            )
        elif candidate.risk_level == "MEDIUM":
            cautions.append(
                "The current risk level is medium."
            )

        if decision.quality.valuation == "EXPENSIVE":
            cautions.append(
                "Valuation is expensive."
            )
        elif decision.quality.valuation == "ELEVATED":
            cautions.append(
                "Valuation is elevated."
            )

        if (
            decision.quality.technical_condition
            == "POSITIVE BUT EXTENDED"
        ):
            cautions.append(
                "Technical conditions are positive "
                "but extended."
            )
        elif decision.quality.technical_condition in {
            "WEAK",
            "VERY_WEAK",
        }:
            cautions.append(
                "Technical conditions are weak."
            )

        if candidate.confidence_score < 85.0:
            cautions.append(
                "Data confidence is below the preferred level."
            )

        if decision.missing_data:
            cautions.append(
                "Some analytical data is unavailable."
            )

        for risk_factor in decision.risk_factors:
            if risk_factor not in cautions:
                cautions.append(risk_factor)

        return tuple(cautions)

    def _downgrade(
        self,
        label: str,
        steps: int,
    ) -> str:
        current_index = self.LABELS.index(
            label
        )
        target_index = min(
            current_index + steps,
            len(self.LABELS) - 1,
        )

        return self.LABELS[target_index]

    def _weaker_of(
        self,
        first: str,
        second: str,
    ) -> str:
        first_index = self.LABELS.index(
            first
        )
        second_index = self.LABELS.index(
            second
        )

        return self.LABELS[
            max(
                first_index,
                second_index,
            )
        ]

    @staticmethod
    def _resolve_generated_at(
        generated_at: datetime | None,
    ) -> datetime:
        if generated_at is None:
            return datetime.now(
                timezone.utc
            )

        if not isinstance(
            generated_at,
            datetime,
        ):
            raise TypeError(
                "generated_at must be a datetime"
            )

        return generated_at