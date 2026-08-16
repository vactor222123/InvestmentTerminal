"""Canonical current-state market analysis orchestration entry point."""

from investment_terminal.analysis.current_state_market_analysis import (
    CurrentStateEquityAnalysisResult,
)
from investment_terminal.review.stock_analysis_composition import (
    build_review_package_from_current_state_analysis,
)


def build_current_state_review_package(
    analysis: CurrentStateEquityAnalysisResult,
):
    """Compose deterministic analysis into a review package.

    Provider refresh, ranking, scoring, recommendations, and allocation remain
    owned by the existing portfolio_ranking pipeline.
    """
    return build_review_package_from_current_state_analysis(
        analysis
    )
