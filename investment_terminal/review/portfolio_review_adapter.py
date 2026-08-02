"""
Adapt portfolio snapshots, policy gaps, and market values for review export.
"""

from typing import Any

from investment_terminal.portfolio.portfolio_market_value_models import (
    PortfolioMarketValueResult,
)
from investment_terminal.portfolio.portfolio_policy_gap_models import (
    PortfolioPolicyGapResult,
)
from investment_terminal.portfolio.portfolio_snapshot_models import (
    PortfolioSnapshot,
)


class PortfolioReviewAdapter:
    """Build the unified portfolio section."""

    def adapt(
        self,
        *,
        snapshot: PortfolioSnapshot,
        market_value: PortfolioMarketValueResult | None,
        quotes_source: str | None,
        policy_gap: PortfolioPolicyGapResult | None = None,
    ) -> dict[str, Any]:
        if not isinstance(
            snapshot,
            PortfolioSnapshot,
        ):
            raise TypeError(
                "snapshot must be a PortfolioSnapshot"
            )

        if (
            market_value is not None
            and not isinstance(
                market_value,
                PortfolioMarketValueResult,
            )
        ):
            raise TypeError(
                "market_value must be a "
                "PortfolioMarketValueResult or None"
            )

        if (
            policy_gap is not None
            and not isinstance(
                policy_gap,
                PortfolioPolicyGapResult,
            )
        ):
            raise TypeError(
                "policy_gap must be a "
                "PortfolioPolicyGapResult or None"
            )

        payload: dict[str, Any] = {
            "status": (
                "MARKET_VALUE_CONNECTED"
                if market_value is not None
                else "COST_BASIS_ONLY"
            ),
            "cost_basis_snapshot": snapshot.to_dict(),
            "policy_gap": (
                policy_gap.to_dict()
                if policy_gap is not None
                else None
            ),
            "market_value": (
                market_value.to_dict()
                if market_value is not None
                else None
            ),
            "quotes_source": quotes_source,
        }

        if market_value is None:
            payload["message"] = (
                "Current market prices are not connected. "
                "Portfolio values use quantity multiplied by "
                "average cost."
            )

        return payload