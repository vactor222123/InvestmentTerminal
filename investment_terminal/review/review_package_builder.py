"""
Builder for the unified investment review package.
"""

from datetime import datetime, timezone
from typing import Any

from investment_terminal.review.review_package_models import (
    InvestmentReviewPackage,
    ReviewPackageSection,
)


class InvestmentReviewPackageBuilder:
    """Build one unified package from already calculated components."""

    SCHEMA_VERSION = "1.0"

    def build(
        self,
        *,
        portfolio_name: str,
        data_freshness: dict[str, Any],
        market_analysis: dict[str, Any],
        portfolio: dict[str, Any],
        stock_analysis: dict[str, Any],
        etf_analysis: dict[str, Any],
        watchlist: dict[str, Any],
        opportunities: dict[str, Any],
        machine_recommendations: dict[str, Any],
        external_context: dict[str, Any] | None = None,
        generated_at: datetime | None = None,
        warnings: tuple[str, ...] = (),
    ) -> InvestmentReviewPackage:
        sections = (
            ReviewPackageSection(
                name="data_freshness",
                payload=data_freshness,
            ),
            ReviewPackageSection(
                name="market_analysis",
                payload=market_analysis,
            ),
            ReviewPackageSection(
                name="portfolio",
                payload=portfolio,
            ),
            ReviewPackageSection(
                name="stock_analysis",
                payload=stock_analysis,
            ),
            ReviewPackageSection(
                name="etf_analysis",
                payload=etf_analysis,
            ),
            ReviewPackageSection(
                name="watchlist",
                payload=watchlist,
            ),
            ReviewPackageSection(
                name="opportunities",
                payload=opportunities,
            ),
            ReviewPackageSection(
                name="machine_recommendations",
                payload=machine_recommendations,
            ),
            ReviewPackageSection(
                name="external_context",
                payload=(
                    external_context
                    if external_context is not None
                    else {
                        "status": "NOT_CONNECTED",
                        "item_count": 0,
                        "items": [],
                    }
                ),
            ),
        )

        return InvestmentReviewPackage(
            schema_version=self.SCHEMA_VERSION,
            generated_at=(
                generated_at
                if generated_at is not None
                else datetime.now(timezone.utc)
            ),
            portfolio_name=portfolio_name,
            sections=sections,
            warnings=warnings,
        )
