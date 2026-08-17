from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.portfolio_strategy_rules import (
    PORTFOLIO_STRATEGIES,
    PortfolioStrategyRule,
    PortfolioStrategyRuleSet,
    StrategyRuleCondition,
)


def condition(strategy: str) -> StrategyRuleCondition:
    return StrategyRuleCondition(
        condition_id=f"{strategy.lower()}-review",
        phase="RISK",
        metric="portfolio_weight",
        operator="LTE",
        threshold=0.25,
        unit="fraction",
        missing_data_action="REVIEW",
    )


def rule(strategy: str, days: int = 30) -> PortfolioStrategyRule:
    return PortfolioStrategyRule(strategy, days, (condition(strategy),))


def rule_set() -> PortfolioStrategyRuleSet:
    return PortfolioStrategyRuleSet(
        "personal-strategy-rules",
        1,
        datetime(2026, 8, 17, tzinfo=timezone.utc),
        tuple(rule(strategy) for strategy in PORTFOLIO_STRATEGIES),
    )


def test_rule_set_requires_all_four_explicit_strategies() -> None:
    result = rule_set()
    assert tuple(item.strategy for item in result.rules) == PORTFOLIO_STRATEGIES
    assert result.rule("position_trade").strategy == "POSITION_TRADE"
    assert result.to_dict()["execution_authorized"] is False


def test_condition_normalizes_stable_vocabulary_and_serializes_threshold() -> None:
    result = condition("CORE_LONG_TERM")
    assert result.phase == "RISK"
    assert result.operator == "LTE"
    assert result.unit == "FRACTION"
    assert result.to_dict()["threshold"] == 0.25


@pytest.mark.parametrize("value", [0, -1, True, 30.0])
def test_review_interval_must_be_positive_integer(value: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        PortfolioStrategyRule(
            "CORE_LONG_TERM", value, (condition("CORE_LONG_TERM"),)  # type: ignore[arg-type]
        )


def test_rule_rejects_missing_conditions() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        PortfolioStrategyRule("CASH_RESERVE", 7, ())


def test_rule_rejects_duplicate_condition_identity() -> None:
    repeated = condition("CORE_LONG_TERM")
    with pytest.raises(ValueError, match="unique condition_id"):
        PortfolioStrategyRule("CORE_LONG_TERM", 30, (repeated, repeated))


def test_rule_set_rejects_missing_or_misordered_strategy() -> None:
    rules = tuple(rule(strategy) for strategy in reversed(PORTFOLIO_STRATEGIES))
    with pytest.raises(ValueError, match="canonical order"):
        PortfolioStrategyRuleSet(
            "rules", 1, datetime(2026, 8, 17, tzinfo=timezone.utc), rules
        )


def test_rule_set_requires_timezone_aware_effective_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        PortfolioStrategyRuleSet(
            "rules",
            1,
            datetime(2026, 8, 17),
            tuple(rule(strategy) for strategy in PORTFOLIO_STRATEGIES),
        )


def test_condition_rejects_non_finite_threshold() -> None:
    with pytest.raises(ValueError, match="finite number"):
        StrategyRuleCondition(
            "risk",
            "RISK",
            "portfolio_weight",
            "LTE",
            float("nan"),
            "fraction",
            "FAIL",
        )
