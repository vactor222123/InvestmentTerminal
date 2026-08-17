from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.portfolio_strategy_rule_evaluation import (
    PortfolioStrategyRuleEvaluator,
    StrategyMetricValue,
)
from investment_terminal.portfolio.portfolio_strategy_rules import (
    PORTFOLIO_STRATEGIES,
    PortfolioStrategyRule,
    PortfolioStrategyRuleSet,
    StrategyRuleCondition,
)

NOW = datetime(2026, 8, 17, tzinfo=timezone.utc)


def rules(missing: str = "REVIEW") -> PortfolioStrategyRuleSet:
    return PortfolioStrategyRuleSet(
        "rules",
        2,
        NOW,
        tuple(
            PortfolioStrategyRule(
                strategy,
                30,
                (
                    StrategyRuleCondition(
                        f"{strategy}-weight",
                        "RISK",
                        "portfolio_weight",
                        "LTE",
                        0.25,
                        "FRACTION",
                        missing,
                    ),
                ),
            )
            for strategy in PORTFOLIO_STRATEGIES
        ),
    )


def metric(strategy: str, value: float, unit: str = "FRACTION") -> StrategyMetricValue:
    return StrategyMetricValue(
        strategy, "portfolio_weight", value, unit, f"snapshot:{strategy}"
    )


def test_evaluates_all_strategies_and_preserves_trace() -> None:
    values = tuple(
        sorted(
            (metric(strategy, 0.20) for strategy in PORTFOLIO_STRATEGIES),
            key=lambda x: (x.strategy, x.metric),
        )
    )
    result = PortfolioStrategyRuleEvaluator.evaluate(rules(), values, evaluated_at=NOW)
    assert result.status == "PASS"
    assert result.strategies[0].conditions[0].evidence_id == "snapshot:CORE_LONG_TERM"
    assert result.to_dict()["execution_authorized"] is False


def test_failed_condition_fails_whole_evidence() -> None:
    values = tuple(
        sorted(
            (
                metric(strategy, 0.30 if strategy == "POSITION_TRADE" else 0.20)
                for strategy in PORTFOLIO_STRATEGIES
            ),
            key=lambda x: (x.strategy, x.metric),
        )
    )
    result = PortfolioStrategyRuleEvaluator.evaluate(rules(), values, evaluated_at=NOW)
    assert result.status == "FAIL"
    assert result.strategies[2].conditions[0].reason == "CONDITION_NOT_MET"


@pytest.mark.parametrize(
    ("missing_action", "expected"), [("REVIEW", "REVIEW"), ("FAIL", "FAIL")]
)
def test_missing_metric_follows_explicit_rule_action(
    missing_action: str, expected: str
) -> None:
    result = PortfolioStrategyRuleEvaluator.evaluate(
        rules(missing_action), (), evaluated_at=NOW
    )
    assert result.status == expected
    assert result.strategies[0].conditions[0].observed_value is None


def test_unit_mismatch_fails_closed() -> None:
    result = PortfolioStrategyRuleEvaluator.evaluate(
        rules(), (metric("CASH_RESERVE", 0.1, "PERCENT"),), evaluated_at=NOW
    )
    assert result.status == "FAIL"
    assert result.strategies[3].conditions[0].reason == "UNIT_MISMATCH"


def test_rejects_duplicate_or_unordered_metrics() -> None:
    value = metric("CORE_LONG_TERM", 0.2)
    with pytest.raises(ValueError, match="unique and deterministically ordered"):
        PortfolioStrategyRuleEvaluator.evaluate(
            rules(), (value, value), evaluated_at=NOW
        )


def test_rejects_evaluation_before_rule_effective_time() -> None:
    with pytest.raises(ValueError, match="effective_at"):
        PortfolioStrategyRuleEvaluator.evaluate(
            rules(), (), evaluated_at=datetime(2026, 8, 16, tzinfo=timezone.utc)
        )
