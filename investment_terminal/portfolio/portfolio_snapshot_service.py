"""
Portfolio snapshot calculation service.
"""

from investment_terminal.portfolio.current_portfolio_models import (
    CurrentPortfolio,
    SUPPORTED_ASSET_TYPES,
    SUPPORTED_HOLDING_STRATEGIES,
    SUPPORTED_SLEEVES,
)
from investment_terminal.portfolio.portfolio_snapshot_models import (
    PortfolioBreakdownItem,
    PortfolioSnapshot,
)


class PortfolioSnapshotService:
    """
    Calculate current portfolio composition from cost-basis values.

    Market-value pricing will be added in a later sprint. Until then,
    quantity multiplied by average cost is used consistently.
    """

    def build(
        self,
        portfolio: CurrentPortfolio,
    ) -> PortfolioSnapshot:
        if not isinstance(
            portfolio,
            CurrentPortfolio,
        ):
            raise TypeError(
                "portfolio must be a CurrentPortfolio"
            )

        total_value = portfolio.total_cost_basis

        asset_amounts = {
            asset_type: 0.0
            for asset_type in SUPPORTED_ASSET_TYPES
        }
        sleeve_amounts = {
            sleeve: 0.0
            for sleeve in SUPPORTED_SLEEVES
        }
        strategy_amounts = {
            strategy: 0.0
            for strategy in SUPPORTED_HOLDING_STRATEGIES
        }

        for holding in portfolio.holdings:
            asset_amounts[
                holding.asset_type
            ] += holding.invested_cost
            sleeve_amounts[
                holding.sleeve
            ] += holding.invested_cost
            strategy_amounts[
                holding.strategy
            ] += holding.invested_cost

        asset_amounts["CASH"] = (
            portfolio.cash_balance
        )
        sleeve_amounts["RESERVE"] += (
            portfolio.cash_balance
        )

        return PortfolioSnapshot(
            portfolio_name=portfolio.name,
            base_currency=(
                portfolio.policy.base_currency
            ),
            total_value=total_value,
            invested_value=portfolio.invested_cost,
            cash_value=portfolio.cash_balance,
            monthly_contribution=(
                portfolio.policy.monthly_contribution
            ),
            asset_breakdown=tuple(
                self._build_item(
                    key=asset_type,
                    amount=round(
                        asset_amounts[
                            asset_type
                        ],
                        2,
                    ),
                    total_value=total_value,
                )
                for asset_type in SUPPORTED_ASSET_TYPES
            ),
            sleeve_breakdown=tuple(
                self._build_item(
                    key=sleeve,
                    amount=round(
                        sleeve_amounts[
                            sleeve
                        ],
                        2,
                    ),
                    total_value=total_value,
                )
                for sleeve in SUPPORTED_SLEEVES
            ),
            strategy_breakdown=(
                tuple(
                    self._build_item(
                        key=strategy,
                        amount=round(
                            strategy_amounts[
                                strategy
                            ],
                            2,
                        ),
                        total_value=total_value,
                    )
                    for strategy in SUPPORTED_HOLDING_STRATEGIES
                )
                + (
                    self._build_item(
                        key="CASH_RESERVE",
                        amount=round(
                            portfolio.cash_balance,
                            2,
                        ),
                        total_value=total_value,
                    ),
                )
            ),
        )

    @staticmethod
    def _build_item(
        *,
        key: str,
        amount: float,
        total_value: float,
    ) -> PortfolioBreakdownItem:
        weight = (
            amount / total_value
            if total_value > 0
            else 0.0
        )

        return PortfolioBreakdownItem(
            key=key,
            amount=amount,
            weight=round(
                weight,
                8,
            ),
        )