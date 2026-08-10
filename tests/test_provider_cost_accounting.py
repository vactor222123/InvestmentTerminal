from decimal import Decimal

import pytest

from investment_terminal.ai.model_adapter import GroundedProviderUsage
from investment_terminal.ai.providers.pricing import (
    GroundedProviderCost,
    GroundedProviderPricingEntry,
    GroundedProviderPricingPolicy,
)


def entry():
    return GroundedProviderPricingEntry(
        provider_identity="OPENAI",
        model_identity="gpt-test",
        currency="USD",
        input_cost_per_million_tokens=Decimal("2.50"),
        output_cost_per_million_tokens=Decimal("10.00"),
    )


def policy():
    return GroundedProviderPricingPolicy(
        entries=(entry(),)
    )


def test_pricing_entry_is_explicit_and_serializable() -> None:
    assert entry().to_dict() == {
        "provider_identity": "OPENAI",
        "model_identity": "gpt-test",
        "currency": "USD",
        "input_cost_per_million_tokens": "2.50",
        "output_cost_per_million_tokens": "10.00",
    }


def test_cost_estimation_is_deterministic_decimal_math() -> None:
    cost = policy().estimate_cost(
        provider_identity="openai",
        model_identity="gpt-test",
        usage=GroundedProviderUsage(
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
        ),
    )

    assert cost == GroundedProviderCost(
        provider_identity="OPENAI",
        model_identity="gpt-test",
        currency="USD",
        input_cost=Decimal("0.002500"),
        output_cost=Decimal("0.005000"),
        total_cost=Decimal("0.007500"),
    )


def test_unknown_model_fails_closed() -> None:
    with pytest.raises(
        LookupError,
        match="pricing is not configured",
    ):
        policy().estimate_cost(
            provider_identity="OPENAI",
            model_identity="unknown",
            usage=GroundedProviderUsage(
                input_tokens=1,
                output_tokens=1,
                total_tokens=2,
            ),
        )


def test_empty_pricing_policy_fails_closed() -> None:
    with pytest.raises(LookupError):
        GroundedProviderPricingPolicy(
            entries=()
        ).require_entry(
            provider_identity="OPENAI",
            model_identity="gpt-test",
        )


def test_duplicate_pricing_entry_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must be unique",
    ):
        GroundedProviderPricingPolicy(
            entries=(
                entry(),
                entry(),
            )
        )


def test_negative_or_non_finite_price_is_rejected() -> None:
    with pytest.raises(ValueError):
        GroundedProviderPricingEntry(
            provider_identity="OPENAI",
            model_identity="gpt-test",
            currency="USD",
            input_cost_per_million_tokens=Decimal("-1"),
            output_cost_per_million_tokens=Decimal("1"),
        )

    with pytest.raises(ValueError):
        GroundedProviderPricingEntry(
            provider_identity="OPENAI",
            model_identity="gpt-test",
            currency="USD",
            input_cost_per_million_tokens=Decimal("NaN"),
            output_cost_per_million_tokens=Decimal("1"),
        )


def test_pricing_contract_contains_no_hardcoded_provider_catalog() -> None:
    import investment_terminal.ai.providers.pricing as module

    assert not hasattr(module, "OPENAI_PRICING")
    assert not hasattr(module, "DEFAULT_PRICING")
    assert not hasattr(module, "MODEL_PRICES")


def test_cost_serialization_is_string_decimal_not_float() -> None:
    data = policy().estimate_cost(
        provider_identity="OPENAI",
        model_identity="gpt-test",
        usage=GroundedProviderUsage(
            input_tokens=3,
            output_tokens=2,
            total_tokens=5,
        ),
    ).to_dict()

    assert isinstance(data["input_cost"], str)
    assert isinstance(data["output_cost"], str)
    assert isinstance(data["total_cost"], str)
