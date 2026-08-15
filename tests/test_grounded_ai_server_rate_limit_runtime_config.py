from decimal import Decimal

import pytest

from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    USAGE_COST_LEDGER_DATABASE_ENV,
    DEFAULT_RATE_LIMIT_CAPACITY,
    DEFAULT_RATE_LIMIT_REFILL_PER_SECOND,
    MODEL_ENV,
    PROVIDER_BUDGET_CURRENCY_ENV,
    PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_MAX_OUTPUT_TOKENS_ENV,
    PROVIDER_MAX_TOTAL_COST_ENV,
    PROVIDER_MAX_TOTAL_TOKENS_ENV,
    PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_PRICING_CURRENCY_ENV,
    RATE_LIMIT_CAPACITY_ENV,
    RATE_LIMIT_REFILL_PER_SECOND_ENV,
    GroundedAIServerRuntimeConfig,
)


def environment() -> dict[str, str]:
    return {
        DATABASE_ENV: "data/knowledge/knowledge.db",
        USAGE_COST_LEDGER_DATABASE_ENV: (
            "data/knowledge/provider_usage_cost.db"
        ),
        MODEL_ENV: "gpt-test",
        ALLOWED_MODELS_ENV: "gpt-test",
        PROVIDER_MAX_OUTPUT_TOKENS_ENV: "32",
        PROVIDER_MAX_TOTAL_TOKENS_ENV: "128",
        PROVIDER_MAX_TOTAL_COST_ENV: "1.50",
        PROVIDER_BUDGET_CURRENCY_ENV: "USD",
        PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV: "0.10",
        PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV: "0.20",
        PROVIDER_PRICING_CURRENCY_ENV: "USD",
    }


def test_runtime_config_uses_rate_limit_defaults() -> None:
    config = GroundedAIServerRuntimeConfig.from_environment(environment())

    assert config.rate_limit_capacity == DEFAULT_RATE_LIMIT_CAPACITY
    assert (
        config.rate_limit_refill_tokens_per_second
        == DEFAULT_RATE_LIMIT_REFILL_PER_SECOND
    )


def test_runtime_config_accepts_rate_limit_overrides() -> None:
    values = environment()
    values[RATE_LIMIT_CAPACITY_ENV] = "7"
    values[RATE_LIMIT_REFILL_PER_SECOND_ENV] = "0.25"

    config = GroundedAIServerRuntimeConfig.from_environment(values)

    assert config.rate_limit_capacity == 7
    assert (
        config.rate_limit_refill_tokens_per_second
        == Decimal("0.25")
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (RATE_LIMIT_CAPACITY_ENV, "0"),
        (RATE_LIMIT_CAPACITY_ENV, "-1"),
        (RATE_LIMIT_CAPACITY_ENV, "abc"),
        (RATE_LIMIT_REFILL_PER_SECOND_ENV, "0"),
        (RATE_LIMIT_REFILL_PER_SECOND_ENV, "-0.1"),
        (RATE_LIMIT_REFILL_PER_SECOND_ENV, "abc"),
    ],
)
def test_runtime_config_rejects_invalid_rate_limit_values(
    field: str,
    value: str,
) -> None:
    values = environment()
    values[field] = value

    with pytest.raises(ValueError, match="positive"):
        GroundedAIServerRuntimeConfig.from_environment(values)
