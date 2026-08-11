from decimal import Decimal

import pytest

from investment_terminal.ai.model_adapter import GroundedProviderUsage
from investment_terminal.ai.providers.guardrails import GroundedProviderBudgetPolicy
from investment_terminal.ai.providers.pricing import GroundedProviderCost


def test_pre_execution_output_limit_allows_within_budget() -> None:
    GroundedProviderBudgetPolicy(
        max_output_tokens=1000
    ).require_request_allowed(requested_max_output_tokens=1000)


def test_pre_execution_output_limit_fails_closed() -> None:
    with pytest.raises(PermissionError):
        GroundedProviderBudgetPolicy(
            max_output_tokens=1000
        ).require_request_allowed(requested_max_output_tokens=1001)


def test_observed_total_token_budget_is_post_execution_guard() -> None:
    with pytest.raises(PermissionError):
        GroundedProviderBudgetPolicy(
            max_total_tokens=1500
        ).require_observed_usage_allowed(
            usage=GroundedProviderUsage(
                input_tokens=1000,
                output_tokens=501,
                total_tokens=1501,
            )
        )


def test_observed_cost_budget_uses_matching_currency() -> None:
    GroundedProviderBudgetPolicy(
        max_total_cost=Decimal("0.010000"),
        currency="usd",
    ).require_observed_cost_allowed(
        cost=GroundedProviderCost(
            provider_identity="OPENAI",
            model_identity="gpt-test",
            currency="USD",
            input_cost=Decimal("0.002500"),
            output_cost=Decimal("0.005000"),
            total_cost=Decimal("0.007500"),
        )
    )


def test_observed_cost_over_budget_fails_closed() -> None:
    with pytest.raises(PermissionError):
        GroundedProviderBudgetPolicy(
            max_total_cost=Decimal("0.007000"),
            currency="USD",
        ).require_observed_cost_allowed(
            cost=GroundedProviderCost(
                provider_identity="OPENAI",
                model_identity="gpt-test",
                currency="USD",
                input_cost=Decimal("0.002500"),
                output_cost=Decimal("0.005000"),
                total_cost=Decimal("0.007500"),
            )
        )


def test_cost_budget_requires_currency() -> None:
    with pytest.raises(ValueError):
        GroundedProviderBudgetPolicy(max_total_cost=Decimal("1.00"))


def test_currency_without_cost_budget_is_rejected() -> None:
    with pytest.raises(ValueError):
        GroundedProviderBudgetPolicy(currency="USD")


def test_total_budget_does_not_claim_unknown_input_preflight() -> None:
    GroundedProviderBudgetPolicy(
        max_total_tokens=100
    ).require_request_allowed(requested_max_output_tokens=None)
