"""Deterministic, non-executable portfolio rebalancing evidence."""

from dataclasses import dataclass
from math import isclose
from typing import Any

from investment_terminal.portfolio.portfolio_policy_gap_models import (
    PortfolioPolicyGapItem,
    PortfolioPolicyGapResult,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_finite_number,
)

REBALANCING_ACTIONS = ("INCREASE", "REDUCE", "HOLD")


@dataclass(frozen=True, slots=True)
class PortfolioRebalancingItem:
    """One strategic-bucket deviation and its non-executable adjustment evidence."""

    key: str
    current_amount: float
    current_weight: float
    target_amount: float
    target_weight: float
    gap_amount: float
    gap_weight: float
    action: str
    suggested_adjustment_amount: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "key",
            normalize_required_text(self.key, field_name="key", uppercase=True),
        )
        for field_name in (
            "current_amount",
            "current_weight",
            "target_amount",
            "target_weight",
            "gap_amount",
            "gap_weight",
            "suggested_adjustment_amount",
        ):
            object.__setattr__(
                self,
                field_name,
                validate_finite_number(
                    getattr(self, field_name), field_name=field_name
                ),
            )
        if self.current_amount < 0 or self.target_amount < 0:
            raise ValueError("current_amount and target_amount must be non-negative")
        if not 0 <= self.current_weight <= 1 or not 0 <= self.target_weight <= 1:
            raise ValueError("current_weight and target_weight must be between 0 and 1")
        if self.suggested_adjustment_amount < 0:
            raise ValueError("suggested_adjustment_amount must be non-negative")
        if not isclose(
            self.gap_amount,
            self.target_amount - self.current_amount,
            rel_tol=0,
            abs_tol=0.01,
        ):
            raise ValueError("gap_amount must match target_amount minus current_amount")
        if not isclose(
            self.gap_weight,
            self.target_weight - self.current_weight,
            rel_tol=0,
            abs_tol=1e-8,
        ):
            raise ValueError("gap_weight must match target_weight minus current_weight")
        action = normalize_required_text(
            self.action, field_name="action", uppercase=True
        )
        if action not in REBALANCING_ACTIONS:
            raise ValueError("action must be one of: " + ", ".join(REBALANCING_ACTIONS))
        object.__setattr__(self, "action", action)
        if action == "INCREASE" and self.gap_weight <= 0:
            raise ValueError("INCREASE requires a positive gap_weight")
        if action == "REDUCE" and self.gap_weight >= 0:
            raise ValueError("REDUCE requires a negative gap_weight")
        if action == "HOLD" and self.suggested_adjustment_amount != 0:
            raise ValueError("HOLD requires zero suggested adjustment")
        if action != "HOLD" and self.suggested_adjustment_amount <= 0:
            raise ValueError("INCREASE and REDUCE require a positive adjustment")
        if action != "HOLD" and not isclose(
            self.suggested_adjustment_amount,
            abs(self.gap_amount),
            rel_tol=0,
            abs_tol=0.01,
        ):
            raise ValueError("suggested adjustment must match the absolute gap amount")

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "current_amount": self.current_amount,
            "current_weight": self.current_weight,
            "target_amount": self.target_amount,
            "target_weight": self.target_weight,
            "gap_amount": self.gap_amount,
            "gap_weight": self.gap_weight,
            "action": self.action,
            "suggested_adjustment_amount": self.suggested_adjustment_amount,
        }


@dataclass(frozen=True, slots=True)
class PortfolioRebalancingEvidence:
    """Strategic rebalancing evidence that never authorizes trade execution."""

    portfolio_name: str
    base_currency: str
    total_value: float
    tolerance_weight: float
    items: tuple[PortfolioRebalancingItem, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "portfolio_name",
            normalize_required_text(self.portfolio_name, field_name="portfolio_name"),
        )
        object.__setattr__(
            self,
            "base_currency",
            normalize_required_text(
                self.base_currency, field_name="base_currency", uppercase=True
            ),
        )
        total = validate_finite_number(self.total_value, field_name="total_value")
        tolerance = validate_finite_number(
            self.tolerance_weight, field_name="tolerance_weight"
        )
        if total < 0:
            raise ValueError("total_value must be non-negative")
        if not 0 <= tolerance <= 1:
            raise ValueError("tolerance_weight must be between 0 and 1")
        object.__setattr__(self, "total_value", total)
        object.__setattr__(self, "tolerance_weight", tolerance)
        if not isinstance(self.items, tuple):
            raise TypeError("items must be a tuple")
        if any(not isinstance(item, PortfolioRebalancingItem) for item in self.items):
            raise TypeError("items must contain only PortfolioRebalancingItem objects")
        keys = tuple(item.key for item in self.items)
        if keys != PortfolioPolicyGapResult.REQUIRED_KEYS:
            raise ValueError(
                "items must contain the required strategic buckets in order"
            )
        for item in self.items:
            outside = abs(item.gap_weight) > tolerance and not isclose(
                abs(item.gap_weight), tolerance, rel_tol=0, abs_tol=1e-12
            )
            if (item.action == "HOLD") == outside:
                raise ValueError("item action must match tolerance_weight")

    @property
    def total_increase_amount(self) -> float:
        return round(
            sum(
                item.suggested_adjustment_amount
                for item in self.items
                if item.action == "INCREASE"
            ),
            2,
        )

    @property
    def total_reduce_amount(self) -> float:
        return round(
            sum(
                item.suggested_adjustment_amount
                for item in self.items
                if item.action == "REDUCE"
            ),
            2,
        )

    @property
    def transferable_amount(self) -> float:
        return min(self.total_increase_amount, self.total_reduce_amount)

    @property
    def requires_review(self) -> bool:
        return any(item.action != "HOLD" for item in self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_name": self.portfolio_name,
            "base_currency": self.base_currency,
            "total_value": self.total_value,
            "tolerance_weight": self.tolerance_weight,
            "requires_review": self.requires_review,
            "total_increase_amount": self.total_increase_amount,
            "total_reduce_amount": self.total_reduce_amount,
            "transferable_amount": self.transferable_amount,
            "execution_authorized": False,
            "items": [item.to_dict() for item in self.items],
        }


class PortfolioRebalancingEvidenceBuilder:
    """Build strategic adjustment evidence from the canonical policy gaps."""

    @staticmethod
    def build(
        policy_gap: PortfolioPolicyGapResult, *, tolerance_weight: float
    ) -> PortfolioRebalancingEvidence:
        if not isinstance(policy_gap, PortfolioPolicyGapResult):
            raise TypeError("policy_gap must be a PortfolioPolicyGapResult")
        tolerance = validate_finite_number(
            tolerance_weight, field_name="tolerance_weight"
        )
        if not 0 <= tolerance <= 1:
            raise ValueError("tolerance_weight must be between 0 and 1")
        return PortfolioRebalancingEvidence(
            portfolio_name=policy_gap.portfolio_name,
            base_currency=policy_gap.base_currency,
            total_value=policy_gap.total_value,
            tolerance_weight=tolerance,
            items=tuple(
                PortfolioRebalancingEvidenceBuilder._build_item(item, tolerance)
                for item in policy_gap.items
            ),
        )

    @staticmethod
    def _build_item(
        item: PortfolioPolicyGapItem, tolerance: float
    ) -> PortfolioRebalancingItem:
        if item.gap_weight > tolerance and not isclose(
            item.gap_weight, tolerance, rel_tol=0, abs_tol=1e-12
        ):
            action = "INCREASE"
            adjustment = max(item.gap_amount, 0.0)
        elif item.gap_weight < -tolerance and not isclose(
            item.gap_weight, -tolerance, rel_tol=0, abs_tol=1e-12
        ):
            action = "REDUCE"
            adjustment = max(-item.gap_amount, 0.0)
        else:
            action = "HOLD"
            adjustment = 0.0
        return PortfolioRebalancingItem(
            key=item.key,
            current_amount=item.current_amount,
            current_weight=item.current_weight,
            target_amount=item.target_amount,
            target_weight=item.target_weight,
            gap_amount=item.gap_amount,
            gap_weight=item.gap_weight,
            action=action,
            suggested_adjustment_amount=round(adjustment, 2),
        )
