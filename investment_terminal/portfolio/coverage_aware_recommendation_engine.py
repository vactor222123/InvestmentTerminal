"""
Coverage-aware recommendation engine.
"""

from dataclasses import replace
from datetime import datetime

from investment_terminal.market.analysis_coverage_policy import (
    AnalysisCoveragePolicy,
)
from investment_terminal.portfolio.ranking_models import (
    RankingResult,
)
from investment_terminal.portfolio.recommendation_engine import (
    RecommendationEngine,
)
from investment_terminal.portfolio.recommendation_models import (
    CandidateRecommendation,
    PortfolioRecommendationResult,
)


class CoverageAwareRecommendationEngine(
    RecommendationEngine
):
    """
    Apply analytical-coverage safety caps after normal recommendations.

    Candidates remain visible in the market ranking. Reduced analytical
    coverage can cap their recommendation and thereby prevent automatic
    allocation until the missing specialized framework is implemented.
    """

    COVERAGE_CAUTION = (
        "Automatic allocation is disabled because the "
        "specialized analytical framework is incomplete."
    )

    def __init__(
        self,
        coverage_policy: AnalysisCoveragePolicy | None = None,
    ) -> None:
        self.coverage_policy = (
            coverage_policy
            if coverage_policy is not None
            else AnalysisCoveragePolicy()
        )

    def recommend(
        self,
        ranking: RankingResult,
        generated_at: datetime | None = None,
    ) -> PortfolioRecommendationResult:
        base_result = super().recommend(
            ranking=ranking,
            generated_at=generated_at,
        )

        recommendations = tuple(
            self._apply_coverage_control(
                recommendation
            )
            for recommendation
            in base_result.recommendations
        )

        return replace(
            base_result,
            recommendations=recommendations,
        )

    def _apply_coverage_control(
        self,
        recommendation: CandidateRecommendation,
    ) -> CandidateRecommendation:
        assessment = (
            self.coverage_policy
            .assess_risk_factors(
                recommendation
                .candidate
                .decision
                .risk_factors
            )
        )

        cap = assessment.recommendation_cap

        if cap is None:
            return recommendation

        capped_label = self._weaker_of(
            recommendation.recommendation,
            cap,
        )

        cautions = list(
            recommendation.cautions
        )
        self._append_unique_caution(
            cautions,
            self.COVERAGE_CAUTION,
        )

        for reason in assessment.reasons:
            self._append_unique_caution(
                cautions,
                reason,
            )

        return replace(
            recommendation,
            recommendation=capped_label,
            cautions=tuple(cautions),
        )