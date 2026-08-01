"""
Deterministic investment thesis generator.
"""

from datetime import datetime, timezone

from investment_terminal.portfolio.recommendation_models import (
    CandidateRecommendation,
    PortfolioRecommendationResult,
)
from investment_terminal.portfolio.thesis_models import (
    InvestmentThesis,
    PortfolioThesisResult,
)


class InvestmentThesisGenerator:
    """
    Generate human-readable investment theses from recommendations.

    Generated actions are analytical guidance labels. They are not
    personalized financial advice or automatic trading instructions.
    """

    SCHEMA_VERSION = "1.0"

    def generate(
        self,
        recommendation_result: PortfolioRecommendationResult,
        generated_at: datetime | None = None,
    ) -> PortfolioThesisResult:
        """
        Generate one thesis for every portfolio recommendation.
        """
        if not isinstance(
            recommendation_result,
            PortfolioRecommendationResult,
        ):
            raise TypeError(
                "recommendation_result must be a "
                "PortfolioRecommendationResult"
            )

        thesis_time = self._resolve_generated_at(
            generated_at
        )

        theses = tuple(
            self._generate_thesis(recommendation)
            for recommendation
            in recommendation_result.recommendations
        )

        return PortfolioThesisResult(
            schema_version=self.SCHEMA_VERSION,
            generated_at=thesis_time,
            theses=theses,
        )

    def _generate_thesis(
        self,
        recommendation: CandidateRecommendation,
    ) -> InvestmentThesis:
        return InvestmentThesis(
            recommendation=recommendation,
            headline=self._build_headline(
                recommendation
            ),
            thesis=self._build_thesis(
                recommendation
            ),
            strengths=self._build_strengths(
                recommendation
            ),
            risks=self._build_risks(
                recommendation
            ),
            action=self._build_action(
                recommendation
            ),
        )

    @staticmethod
    def _build_headline(
        recommendation: CandidateRecommendation,
    ) -> str:
        symbol = recommendation.symbol
        label = recommendation.recommendation

        headlines = {
            "STRONG_BUY": (
                f"{symbol} presents one of the strongest "
                "investment profiles in the analyzed universe."
            ),
            "BUY": (
                f"{symbol} presents a strong investment profile "
                "with favorable supporting conditions."
            ),
            "ACCUMULATE": (
                f"{symbol} presents a favorable long-term profile, "
                "but position building should remain gradual."
            ),
            "HOLD": (
                f"{symbol} presents a balanced investment profile "
                "without a strong immediate entry signal."
            ),
            "WATCH": (
                f"{symbol} requires further monitoring before "
                "a stronger investment case is established."
            ),
            "AVOID": (
                f"{symbol} currently presents an unfavorable "
                "risk-reward profile."
            ),
        }

        return headlines[label]

    @staticmethod
    def _build_thesis(
        recommendation: CandidateRecommendation,
    ) -> str:
        candidate = recommendation.candidate
        decision = candidate.decision
        quality = decision.quality

        opening = (
            f"{recommendation.symbol} ranks "
            f"#{recommendation.rank} in the analyzed universe "
            f"with an overall score of "
            f"{recommendation.overall_score:.2f}/100."
        )

        business_context = (
            f" Business quality is "
            f"{quality.business_quality.lower()}, "
            f"financial health is "
            f"{quality.financial_health.lower()}, "
            f"and growth is "
            f"{quality.growth.lower()}."
        )

        market_context = (
            f" Valuation is "
            f"{quality.valuation.lower()}, "
            f"while the technical condition is "
            f"{quality.technical_condition.lower()}."
        )

        conclusion = (
            f" The resulting analytical recommendation is "
            f"{recommendation.recommendation.replace('_', ' ')}, "
            f"with a {quality.risk_level.lower()} current "
            f"risk level and a confidence score of "
            f"{recommendation.confidence_score:.2f}/100."
        )

        return (
            opening
            + business_context
            + market_context
            + conclusion
        )

    @staticmethod
    def _build_strengths(
        recommendation: CandidateRecommendation,
    ) -> tuple[str, ...]:
        strengths = list(
            recommendation.rationale
        )

        decision = recommendation.candidate.decision

        for positive_factor in decision.positive_factors:
            InvestmentThesisGenerator._append_unique(
                strengths,
                positive_factor,
            )

        if not strengths:
            strengths.append(
                "The candidate has sufficient analytical "
                "support for continued monitoring."
            )

        return tuple(strengths)

    @staticmethod
    def _build_risks(
        recommendation: CandidateRecommendation,
    ) -> tuple[str, ...]:
        risks = list(
            recommendation.cautions
        )

        decision = recommendation.candidate.decision

        for risk_factor in decision.risk_factors:
            InvestmentThesisGenerator._append_unique(
                risks,
                risk_factor,
            )

        return tuple(risks)

    @staticmethod
    def _build_action(
        recommendation: CandidateRecommendation,
    ) -> str:
        label = recommendation.recommendation
        technical_condition = (
            recommendation
            .candidate
            .decision
            .quality
            .technical_condition
        )
        risk_level = recommendation.risk_level

        if label == "STRONG_BUY":
            if technical_condition == "POSITIVE BUT EXTENDED":
                return (
                    "Consider staged position accumulation rather "
                    "than immediate full allocation, while waiting "
                    "for a more favorable technical entry."
                )

            return (
                "Consider the candidate for prioritized staged "
                "position accumulation, subject to portfolio "
                "allocation and risk limits."
            )

        if label == "BUY":
            if risk_level == "MEDIUM":
                return (
                    "Consider gradual position accumulation with "
                    "smaller entries and continued risk monitoring."
                )

            return (
                "Consider gradual position accumulation while "
                "monitoring valuation and technical conditions."
            )

        if label == "ACCUMULATE":
            return (
                "Consider building the position gradually through "
                "multiple entries while waiting for improved "
                "valuation or technical conditions."
            )

        if label == "HOLD":
            return (
                "Maintain an existing position or keep the candidate "
                "on the active watchlist until the investment case "
                "strengthens."
            )

        if label == "WATCH":
            return (
                "Do not prioritize a new position yet; monitor the "
                "candidate for improving scores, risk, valuation, "
                "or technical conditions."
            )

        return (
            "Avoid initiating a new position until the analytical "
            "profile improves materially."
        )

    @staticmethod
    def _append_unique(
        values: list[str],
        value: str,
    ) -> None:
        normalized_value = (
            value.strip().casefold()
        )

        existing_values = {
            existing.strip().casefold()
            for existing in values
        }

        if normalized_value not in existing_values:
            values.append(
                value.strip()
            )

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