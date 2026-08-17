"""Deterministic evaluation evidence for portfolio strategy rules."""

from dataclasses import dataclass
from datetime import datetime
from operator import eq, ge, gt, le, lt
from typing import Any, Callable

from investment_terminal.portfolio.portfolio_strategy_rules import (
    PORTFOLIO_STRATEGIES,
    PortfolioStrategyRuleSet,
    StrategyRuleCondition,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
)


@dataclass(frozen=True, slots=True)
class StrategyMetricValue:
    strategy: str
    metric: str
    value: float
    unit: str
    evidence_id: str

    def __post_init__(self) -> None:
        strategy = normalize_required_text(
            self.strategy, field_name="strategy", uppercase=True
        )
        if strategy not in PORTFOLIO_STRATEGIES:
            raise ValueError("strategy is not supported")
        object.__setattr__(self, "strategy", strategy)
        for name, uppercase in (
            ("metric", False),
            ("unit", True),
            ("evidence_id", False),
        ):
            object.__setattr__(
                self,
                name,
                normalize_required_text(
                    getattr(self, name), field_name=name, uppercase=uppercase
                ),
            )
        object.__setattr__(
            self, "value", validate_finite_number(self.value, field_name="value")
        )


@dataclass(frozen=True, slots=True)
class StrategyConditionEvaluation:
    strategy: str
    condition_id: str
    phase: str
    metric: str
    operator: str
    threshold: float
    unit: str
    observed_value: float | None
    evidence_id: str | None
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class StrategyRuleEvaluation:
    strategy: str
    status: str
    conditions: tuple[StrategyConditionEvaluation, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "status": self.status,
            "conditions": [item.to_dict() for item in self.conditions],
        }


@dataclass(frozen=True, slots=True)
class PortfolioStrategyRuleEvaluationEvidence:
    rule_set_id: str
    rule_set_version: int
    evaluated_at: datetime
    strategies: tuple[StrategyRuleEvaluation, ...]

    def __post_init__(self) -> None:
        validate_aware_datetime(self.evaluated_at, field_name="evaluated_at")
        if tuple(item.strategy for item in self.strategies) != PORTFOLIO_STRATEGIES:
            raise ValueError("strategies must use canonical order")

    @property
    def status(self) -> str:
        statuses = {item.status for item in self.strategies}
        return (
            "FAIL"
            if "FAIL" in statuses
            else "REVIEW" if "REVIEW" in statuses else "PASS"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_set_id": self.rule_set_id,
            "rule_set_version": self.rule_set_version,
            "evaluated_at": self.evaluated_at.isoformat(),
            "status": self.status,
            "execution_authorized": False,
            "strategies": [item.to_dict() for item in self.strategies],
        }


class PortfolioStrategyRuleEvaluator:
    _OPERATORS: dict[str, Callable[[float, float], bool]] = {
        "LT": lt,
        "LTE": le,
        "EQ": eq,
        "GTE": ge,
        "GT": gt,
    }

    @classmethod
    def evaluate(
        cls,
        rule_set: PortfolioStrategyRuleSet,
        metrics: tuple[StrategyMetricValue, ...],
        *,
        evaluated_at: datetime
    ) -> PortfolioStrategyRuleEvaluationEvidence:
        if not isinstance(rule_set, PortfolioStrategyRuleSet):
            raise TypeError("rule_set must be a PortfolioStrategyRuleSet")
        validate_aware_datetime(evaluated_at, field_name="evaluated_at")
        if evaluated_at < rule_set.effective_at:
            raise ValueError(
                "evaluated_at must not be earlier than rule_set effective_at"
            )
        if not isinstance(metrics, tuple) or any(
            not isinstance(item, StrategyMetricValue) for item in metrics
        ):
            raise TypeError("metrics must be a tuple of StrategyMetricValue objects")
        keys = tuple((item.strategy, item.metric) for item in metrics)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("metrics must be unique and deterministically ordered")
        indexed = {(item.strategy, item.metric): item for item in metrics}
        strategies = []
        for rule in rule_set.rules:
            results = tuple(
                cls._condition(
                    rule.strategy,
                    condition,
                    indexed.get((rule.strategy, condition.metric)),
                )
                for condition in rule.conditions
            )
            statuses = {item.status for item in results}
            status = (
                "FAIL"
                if "FAIL" in statuses
                else "REVIEW" if "REVIEW" in statuses else "PASS"
            )
            strategies.append(StrategyRuleEvaluation(rule.strategy, status, results))
        return PortfolioStrategyRuleEvaluationEvidence(
            rule_set.rule_set_id, rule_set.version, evaluated_at, tuple(strategies)
        )

    @classmethod
    def _condition(
        cls,
        strategy: str,
        condition: StrategyRuleCondition,
        metric: StrategyMetricValue | None,
    ) -> StrategyConditionEvaluation:
        if metric is None:
            status = condition.missing_data_action
            return StrategyConditionEvaluation(
                strategy,
                condition.condition_id,
                condition.phase,
                condition.metric,
                condition.operator,
                condition.threshold,
                condition.unit,
                None,
                None,
                status,
                "METRIC_MISSING",
            )
        if metric.unit != condition.unit:
            return StrategyConditionEvaluation(
                strategy,
                condition.condition_id,
                condition.phase,
                condition.metric,
                condition.operator,
                condition.threshold,
                condition.unit,
                metric.value,
                metric.evidence_id,
                "FAIL",
                "UNIT_MISMATCH",
            )
        passed = cls._OPERATORS[condition.operator](metric.value, condition.threshold)
        return StrategyConditionEvaluation(
            strategy,
            condition.condition_id,
            condition.phase,
            condition.metric,
            condition.operator,
            condition.threshold,
            condition.unit,
            metric.value,
            metric.evidence_id,
            "PASS" if passed else "FAIL",
            "CONDITION_MET" if passed else "CONDITION_NOT_MET",
        )
