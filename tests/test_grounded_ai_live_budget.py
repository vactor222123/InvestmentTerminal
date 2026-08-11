from decimal import Decimal

import pytest

from investment_terminal.ai.model_adapter import (
    GroundedModelResponse,
    GroundedProviderUsage,
)
from investment_terminal.ai.providers.guardrails import (
    GroundedProviderBudgetPolicy,
)
from investment_terminal.cli.grounded_ai_live import (
    _budget_policy,
    build_argument_parser,
)


def test_budget_flags_are_optional() -> None:
    options = build_argument_parser().parse_args(
        [
            "--live",
            "--request-id", "r1",
            "--query", "Question",
            "--model", "gpt-test",
        ]
    )
    assert options.max_output_tokens is None
    assert options.max_total_tokens is None
    assert options.max_total_cost is None
    assert options.budget_currency is None


def test_budget_policy_builds_from_cli_values() -> None:
    policy = _budget_policy(
        max_output_tokens=500,
        max_total_tokens=2000,
        max_total_cost=Decimal("0.02"),
        currency="usd",
    )
    assert policy == GroundedProviderBudgetPolicy(
        max_output_tokens=500,
        max_total_tokens=2000,
        max_total_cost=Decimal("0.02"),
        currency="USD",
    )


def test_cost_budget_without_currency_is_rejected() -> None:
    with pytest.raises(ValueError):
        _budget_policy(
            max_output_tokens=None,
            max_total_tokens=None,
            max_total_cost=Decimal("0.02"),
            currency=None,
        )


def test_currency_without_cost_budget_is_rejected() -> None:
    with pytest.raises(ValueError):
        _budget_policy(
            max_output_tokens=None,
            max_total_tokens=None,
            max_total_cost=None,
            currency="USD",
        )


def test_observed_usage_over_total_budget_fails_closed() -> None:
    policy = GroundedProviderBudgetPolicy(
        max_total_tokens=100
    )
    with pytest.raises(PermissionError):
        policy.require_observed_usage_allowed(
            usage=GroundedProviderUsage(
                input_tokens=80,
                output_tokens=21,
                total_tokens=101,
            )
        )


def test_observed_usage_within_budget_passes() -> None:
    policy = GroundedProviderBudgetPolicy(
        max_output_tokens=50,
        max_total_tokens=100,
    )
    policy.require_observed_usage_allowed(
        usage=GroundedProviderUsage(
            input_tokens=60,
            output_tokens=40,
            total_tokens=100,
        )
    )
