"""Versioned, strategy-specific portfolio rule contracts."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
)

PORTFOLIO_STRATEGIES = (
    "CORE_LONG_TERM",
    "STOCK_LONG_TERM",
    "POSITION_TRADE",
    "CASH_RESERVE",
)
STRATEGY_RULE_PHASES = ("ENTRY", "HOLD", "EXIT", "RISK")
STRATEGY_RULE_OPERATORS = ("LT", "LTE", "EQ", "GTE", "GT")
MISSING_DATA_ACTIONS = ("FAIL", "REVIEW")


@dataclass(frozen=True, slots=True)
class StrategyRuleCondition:
    """One explicit measurable condition in a strategy rule."""

    condition_id: str
    phase: str
    metric: str
    operator: str
    threshold: float
    unit: str
    missing_data_action: str

    def __post_init__(self) -> None:
        for field_name in ("condition_id", "metric"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name), field_name=field_name
                ),
            )
        for field_name, choices in (
            ("phase", STRATEGY_RULE_PHASES),
            ("operator", STRATEGY_RULE_OPERATORS),
            ("missing_data_action", MISSING_DATA_ACTIONS),
        ):
            normalized = normalize_required_text(
                getattr(self, field_name), field_name=field_name, uppercase=True
            )
            if normalized not in choices:
                raise ValueError(f"{field_name} must be one of: " + ", ".join(choices))
            object.__setattr__(self, field_name, normalized)
        object.__setattr__(
            self,
            "threshold",
            validate_finite_number(self.threshold, field_name="threshold"),
        )
        object.__setattr__(
            self,
            "unit",
            normalize_required_text(self.unit, field_name="unit", uppercase=True),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "phase": self.phase,
            "metric": self.metric,
            "operator": self.operator,
            "threshold": self.threshold,
            "unit": self.unit,
            "missing_data_action": self.missing_data_action,
        }


@dataclass(frozen=True, slots=True)
class PortfolioStrategyRule:
    """Explicit review cadence and conditions for one portfolio strategy."""

    strategy: str
    review_interval_days: int
    conditions: tuple[StrategyRuleCondition, ...]

    def __post_init__(self) -> None:
        strategy = normalize_required_text(
            self.strategy, field_name="strategy", uppercase=True
        )
        if strategy not in PORTFOLIO_STRATEGIES:
            raise ValueError(
                "strategy must be one of: " + ", ".join(PORTFOLIO_STRATEGIES)
            )
        object.__setattr__(self, "strategy", strategy)
        if (
            isinstance(self.review_interval_days, bool)
            or not isinstance(self.review_interval_days, int)
            or self.review_interval_days <= 0
        ):
            raise ValueError("review_interval_days must be a positive integer")
        if not isinstance(self.conditions, tuple):
            raise TypeError("conditions must be a tuple")
        if not self.conditions:
            raise ValueError("conditions must not be empty")
        if any(not isinstance(item, StrategyRuleCondition) for item in self.conditions):
            raise TypeError(
                "conditions must contain only StrategyRuleCondition objects"
            )
        keys = tuple((item.phase, item.condition_id) for item in self.conditions)
        if keys != tuple(sorted(keys)):
            raise ValueError("conditions must be deterministically ordered")
        condition_ids = tuple(item.condition_id for item in self.conditions)
        if len(condition_ids) != len(set(condition_ids)):
            raise ValueError("conditions must contain unique condition_id values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "review_interval_days": self.review_interval_days,
            "conditions": [item.to_dict() for item in self.conditions],
        }


@dataclass(frozen=True, slots=True)
class PortfolioStrategyRuleSet:
    """Complete immutable rule configuration for every portfolio strategy."""

    rule_set_id: str
    version: int
    effective_at: datetime
    rules: tuple[PortfolioStrategyRule, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rule_set_id",
            normalize_required_text(self.rule_set_id, field_name="rule_set_id"),
        )
        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or self.version <= 0
        ):
            raise ValueError("version must be a positive integer")
        validate_aware_datetime(self.effective_at, field_name="effective_at")
        if not isinstance(self.rules, tuple):
            raise TypeError("rules must be a tuple")
        if any(not isinstance(item, PortfolioStrategyRule) for item in self.rules):
            raise TypeError("rules must contain only PortfolioStrategyRule objects")
        strategies = tuple(item.strategy for item in self.rules)
        if strategies != PORTFOLIO_STRATEGIES:
            raise ValueError(
                "rules must contain every portfolio strategy in canonical order"
            )

    def rule(self, strategy: str) -> PortfolioStrategyRule:
        normalized = normalize_required_text(
            strategy, field_name="strategy", uppercase=True
        )
        for item in self.rules:
            if item.strategy == normalized:
                return item
        raise KeyError(f"No strategy rule found for {normalized}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_set_id": self.rule_set_id,
            "version": self.version,
            "effective_at": self.effective_at.isoformat(),
            "execution_authorized": False,
            "rules": [item.to_dict() for item in self.rules],
        }
