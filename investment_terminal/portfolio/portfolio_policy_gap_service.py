"""
Calculate strategic portfolio allocation gaps.
"""

from investment_terminal.portfolio.current_portfolio_models import (
    PortfolioPolicy,
)
from investment_terminal.portfolio.portfolio_policy_gap_models import (
    PortfolioPolicyGapItem,
    PortfolioPolicyGapResult,
)
from investment_terminal.portfolio.portfolio_snapshot_models import (
    PortfolioSnapshot,
)


class PortfolioPolicyGapService:
    """
    Compare the current whole-portfolio allocation with policy targets.

    Tactical total combines long-term individual stocks and position
    trades. A later contribution planner can decide how new tactical
    capital should be divided between those two strategies.
    """

    def calculate(
        self,
        *,
        snapshot: PortfolioSnapshot,
        policy: PortfolioPolicy,
    ) -> PortfolioPolicyGapResult:
        if not isinstance(
            snapshot,
            PortfolioSnapshot,
        ):
            raise TypeError(
                "snapshot must be a PortfolioSnapshot"
            )

        if not isinstance(
            policy,
            PortfolioPolicy,
        ):
            raise TypeError(
                "policy must be a PortfolioPolicy"
            )

        tactical_amount = round(
            snapshot.strategy(
                "STOCK_LONG_TERM"
            ).amount
            + snapshot.strategy(
                "POSITION_TRADE"
            ).amount,
            2,
        )

        current = {
            "CORE_LONG_TERM": (
                snapshot.strategy(
                    "CORE_LONG_TERM"
                ).amount
            ),
            "TACTICAL_TOTAL": tactical_amount,
            "CASH_RESERVE": snapshot.cash_value,
        }
        targets = {
            "CORE_LONG_TERM": (
                policy.core_target_weight
            ),
            "TACTICAL_TOTAL": (
                policy.tactical_target_weight
            ),
            "CASH_RESERVE": (
                policy.cash_target_weight
            ),
        }

        return PortfolioPolicyGapResult(
            portfolio_name=snapshot.portfolio_name,
            base_currency=snapshot.base_currency,
            total_value=snapshot.total_value,
            items=tuple(
                self._build_item(
                    key=key,
                    current_amount=current[key],
                    target_weight=targets[key],
                    total_value=snapshot.total_value,
                )
                for key in (
                    "CORE_LONG_TERM",
                    "TACTICAL_TOTAL",
                    "CASH_RESERVE",
                )
            ),
        )

    @staticmethod
    def _build_item(
        *,
        key: str,
        current_amount: float,
        target_weight: float,
        total_value: float,
    ) -> PortfolioPolicyGapItem:
        current_weight = (
            current_amount / total_value
            if total_value > 0
            else 0.0
        )
        target_amount = (
            total_value * target_weight
        )
        gap_amount = (
            target_amount - current_amount
        )
        gap_weight = (
            target_weight - current_weight
        )

        return PortfolioPolicyGapItem(
            key=key,
            current_amount=round(
                current_amount,
                2,
            ),
            current_weight=round(
                current_weight,
                8,
            ),
            target_amount=round(
                target_amount,
                2,
            ),
            target_weight=round(
                target_weight,
                8,
            ),
            gap_amount=round(
                gap_amount,
                2,
            ),
            gap_weight=round(
                gap_weight,
                8,
            ),
        )