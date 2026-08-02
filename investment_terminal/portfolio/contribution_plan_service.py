"""
Build a contribution plan from strategic allocation gaps.
"""

from investment_terminal.portfolio.contribution_plan_models import (
    ContributionPlan,
    ContributionPlanItem,
)
from investment_terminal.portfolio.portfolio_policy_gap_models import (
    PortfolioPolicyGapResult,
)


class ContributionPlanner:
    """
    Allocate new capital toward positive strategic gaps.

    This planner intentionally works only at the strategic-bucket level.
    It does not yet select individual ETFs or stocks.
    """

    def plan(
        self,
        *,
        policy_gap: PortfolioPolicyGapResult,
        available_capital: float,
    ) -> ContributionPlan:
        ContributionPlanItem._validate_non_negative_number(
            available_capital,
            field_name="available_capital",
        )

        if available_capital == 0:
            return ContributionPlan(
                available_capital=0.0,
                deployable_capital=0.0,
                retained_cash=0.0,
                items=(),
                status="NO_CAPITAL",
            )

        positive_gaps = tuple(
            item
            for item in policy_gap.items
            if item.gap_amount > 0
        )

        if not positive_gaps:
            return ContributionPlan(
                available_capital=round(
                    available_capital,
                    2,
                ),
                deployable_capital=0.0,
                retained_cash=round(
                    available_capital,
                    2,
                ),
                items=(),
                status="HOLD_CASH",
            )

        total_positive_gap = sum(
            item.gap_amount
            for item in positive_gaps
        )
        deployable = min(
            available_capital,
            total_positive_gap,
        )
        retained_cash = (
            available_capital - deployable
        )

        raw_amounts = [
            deployable
            * item.gap_amount
            / total_positive_gap
            for item in positive_gaps
        ]
        rounded_amounts = [
            round(amount, 2)
            for amount in raw_amounts
        ]

        rounding_difference = round(
            deployable - sum(rounded_amounts),
            2,
        )

        if rounded_amounts:
            rounded_amounts[0] = round(
                rounded_amounts[0]
                + rounding_difference,
                2,
            )

        items = tuple(
            ContributionPlanItem(
                key=item.key,
                amount=amount,
                share=round(
                    amount / available_capital,
                    8,
                ),
                reason=(
                    f"{item.key} is underweight by "
                    f"{item.gap_amount:.2f} "
                    f"{policy_gap.base_currency}."
                ),
            )
            for item, amount in zip(
                positive_gaps,
                rounded_amounts,
                strict=True,
            )
            if amount > 0
        )

        return ContributionPlan(
            available_capital=round(
                available_capital,
                2,
            ),
            deployable_capital=round(
                deployable,
                2,
            ),
            retained_cash=round(
                retained_cash,
                2,
            ),
            items=items,
            status="ALLOCATE",
        )