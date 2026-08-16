"""Direct typed stock-analysis to review-package composition boundary."""

from investment_terminal.analysis.current_state_market_analysis import (
    CurrentStateEquityAnalysisResult,
)
from investment_terminal.review.portfolio_analysis_review_adapter import (
    PortfolioAnalysisReviewAdapter,
)


def build_review_package_from_current_state_analysis(
    analysis: CurrentStateEquityAnalysisResult,
):
    """Build a review package without JSON serialization round-trip.

    The existing adapter remains the single transformation authority.
    """
    return PortfolioAnalysisReviewAdapter().adapt(analysis)
