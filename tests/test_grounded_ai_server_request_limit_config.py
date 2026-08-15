import pytest

from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    DEFAULT_MAX_REQUEST_BODY_BYTES,
    MAX_REQUEST_BODY_BYTES_ENV,
    MODEL_ENV,
    PROVIDER_BUDGET_CURRENCY_ENV,
    PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_MAX_OUTPUT_TOKENS_ENV,
    PROVIDER_MAX_TOTAL_COST_ENV,
    PROVIDER_MAX_TOTAL_TOKENS_ENV,
    PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_PRICING_CURRENCY_ENV,
    GroundedAIServerRuntimeConfig,
)


def base_environment():
    return {
        DATABASE_ENV: "data/knowledge/knowledge.db",
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


def test_runtime_config_uses_default_request_body_limit() -> None:
    config = GroundedAIServerRuntimeConfig.from_environment(
        base_environment()
    )
    assert config.max_request_body_bytes == DEFAULT_MAX_REQUEST_BODY_BYTES


def test_runtime_config_accepts_request_body_limit_override() -> None:
    values = base_environment()
    values[MAX_REQUEST_BODY_BYTES_ENV] = "2048"

    config = GroundedAIServerRuntimeConfig.from_environment(values)
    assert config.max_request_body_bytes == 2048


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_runtime_config_rejects_invalid_request_body_limit(value) -> None:
    values = base_environment()
    values[MAX_REQUEST_BODY_BYTES_ENV] = value

    with pytest.raises(ValueError, match="positive integer"):
        GroundedAIServerRuntimeConfig.from_environment(values)
