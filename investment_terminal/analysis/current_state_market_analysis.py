"""Canonical current-state equity-analysis contract.

This module names the existing PortfolioExportPackage as the authoritative typed
result of one deterministic live equity-analysis run.

It deliberately does not add a second result model or duplicate analytical
state. The exporter package already owns the complete validated aggregate:
market freshness, ranking, recommendations, theses, allocation, and the shared
generation timestamp.
"""

from typing import Final, TypeAlias

from investment_terminal.exporters.portfolio_exporter import (
    PortfolioExportPackage,
)


CURRENT_STATE_EQUITY_ANALYSIS_IDENTITY: Final[str] = (
    "CURRENT_STATE_EQUITY_ANALYSIS@1"
)

CurrentStateEquityAnalysisResult: TypeAlias = PortfolioExportPackage


def require_current_state_equity_analysis_result(
    value: object,
) -> CurrentStateEquityAnalysisResult:
    """Return a validated canonical live-analysis result or fail closed."""
    if not isinstance(
        value,
        PortfolioExportPackage,
    ):
        raise TypeError(
            "value must be a PortfolioExportPackage"
        )

    if not value.market_data.all_ready:
        raise ValueError(
            "current-state equity analysis requires ready market data"
        )

    return value
