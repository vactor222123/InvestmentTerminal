from decimal import Decimal
from pathlib import Path

import pytest

from investment_terminal.ai.providers.composition import (
    DEFAULT_OPENAI_API_KEY_ENV,
)
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    API_KEY_ENV_NAME_ENV,
    DATABASE_ENV,
    MAX_RETRIES_ENV,
    MODEL_ENV,
    PROVIDER_BUDGET_CURRENCY_ENV,
    PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_MAX_OUTPUT_TOKENS_ENV,
    PROVIDER_MAX_TOTAL_COST_ENV,
    PROVIDER_MAX_TOTAL_TOKENS_ENV,
    PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_PRICING_CURRENCY_ENV,
    TIMEOUT_ENV,
    GroundedAIServerRuntimeConfig,
)


def env():
    return {
        DATABASE_ENV: "data/knowledge/knowledge.db",
        MODEL_ENV: "gpt-test",
        ALLOWED_MODELS_ENV: "gpt-test,gpt-other",
        PROVIDER_MAX_OUTPUT_TOKENS_ENV: "32",
        PROVIDER_MAX_TOTAL_TOKENS_ENV: "128",
        PROVIDER_MAX_TOTAL_COST_ENV: "1.50",
        PROVIDER_BUDGET_CURRENCY_ENV: "usd",
        PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV: "0.10",
        PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV: "0.20",
        PROVIDER_PRICING_CURRENCY_ENV: "USD",
    }


def test_runtime_config_parses_required_environment():
    config = GroundedAIServerRuntimeConfig.from_environment(env())

    assert config.database == Path("data/knowledge/knowledge.db")
    assert config.model_identity == "gpt-test"
    assert config.allowed_models == ("gpt-test", "gpt-other")
    assert config.timeout_seconds == 30
    assert config.max_retries == 2
    assert config.api_key_environment_variable == DEFAULT_OPENAI_API_KEY_ENV

    assert config.provider_max_output_tokens == 32
    assert config.provider_max_total_tokens == 128
    assert config.provider_max_total_cost == Decimal("1.50")
    assert config.provider_budget_currency == "USD"
    assert config.provider_input_cost_per_million_tokens == Decimal("0.10")
    assert config.provider_output_cost_per_million_tokens == Decimal("0.20")
    assert config.provider_pricing_currency == "USD"

    assert config.governance_policy().assess(
        provider_identity="OPENAI",
        model_identity="gpt-test",
    ).allowed

    pricing = config.pricing_policy().require_entry(
        provider_identity="OPENAI",
        model_identity="gpt-test",
    )
    assert pricing.input_cost_per_million_tokens == Decimal("0.10")
    assert pricing.output_cost_per_million_tokens == Decimal("0.20")
    assert pricing.currency == "USD"

    budget = config.budget_policy()
    assert budget.max_output_tokens == 32
    assert budget.max_total_tokens == 128
    assert budget.max_total_cost == Decimal("1.50")
    assert budget.currency == "USD"


def test_runtime_config_requires_model_to_be_allowlisted():
    values = env()
    values[MODEL_ENV] = "gpt-not-allowed"

    with pytest.raises(ValueError, match="explicitly present"):
        GroundedAIServerRuntimeConfig.from_environment(values)


def test_runtime_config_requires_core_and_economic_values():
    for name in (
        DATABASE_ENV,
        MODEL_ENV,
        ALLOWED_MODELS_ENV,
        PROVIDER_MAX_OUTPUT_TOKENS_ENV,
        PROVIDER_MAX_TOTAL_TOKENS_ENV,
        PROVIDER_MAX_TOTAL_COST_ENV,
        PROVIDER_BUDGET_CURRENCY_ENV,
        PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
        PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
        PROVIDER_PRICING_CURRENCY_ENV,
    ):
        values = env()
        del values[name]

        with pytest.raises(ValueError, match="required environment variable"):
            GroundedAIServerRuntimeConfig.from_environment(values)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (PROVIDER_MAX_OUTPUT_TOKENS_ENV, "0", "positive integer"),
        (PROVIDER_MAX_TOTAL_TOKENS_ENV, "-1", "positive integer"),
        (PROVIDER_MAX_TOTAL_COST_ENV, "-0.01", "non-negative decimal"),
        (
            PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
            "nan",
            "non-negative decimal",
        ),
        (
            PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
            "-0.01",
            "non-negative decimal",
        ),
    ],
)
def test_runtime_config_rejects_invalid_economic_values(
    field,
    value,
    message,
):
    values = env()
    values[field] = value

    with pytest.raises(ValueError, match=message):
        GroundedAIServerRuntimeConfig.from_environment(values)


def test_runtime_config_requires_matching_budget_and_pricing_currency():
    values = env()
    values[PROVIDER_PRICING_CURRENCY_ENV] = "EUR"

    with pytest.raises(ValueError, match="must match"):
        GroundedAIServerRuntimeConfig.from_environment(values)


def test_runtime_config_parses_operational_overrides():
    values = env()
    values[TIMEOUT_ENV] = "12.5"
    values[MAX_RETRIES_ENV] = "4"
    values[API_KEY_ENV_NAME_ENV] = "CUSTOM_OPENAI_KEY"

    config = GroundedAIServerRuntimeConfig.from_environment(values)

    assert config.timeout_seconds == 12.5
    assert config.max_retries == 4
    assert config.api_key_environment_variable == "CUSTOM_OPENAI_KEY"
