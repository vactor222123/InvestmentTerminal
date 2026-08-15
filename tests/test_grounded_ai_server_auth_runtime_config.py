from pathlib import Path

from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    DEFAULT_SERVER_API_KEY_ENV,
    MODEL_ENV,
    PROVIDER_BUDGET_CURRENCY_ENV,
    PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_MAX_OUTPUT_TOKENS_ENV,
    PROVIDER_MAX_TOTAL_COST_ENV,
    PROVIDER_MAX_TOTAL_TOKENS_ENV,
    PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_PRICING_CURRENCY_ENV,
    SERVER_API_KEY_ENV_NAME_ENV,
    GroundedAIServerRuntimeConfig,
)


def base_environment() -> dict[str, str]:
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


def test_runtime_config_uses_canonical_server_api_key_env_default() -> None:
    config = GroundedAIServerRuntimeConfig.from_environment(
        base_environment()
    )
    assert (
        config.server_api_key_environment_variable
        == DEFAULT_SERVER_API_KEY_ENV
    )


def test_runtime_config_accepts_custom_server_api_key_env_name() -> None:
    values = base_environment()
    values[SERVER_API_KEY_ENV_NAME_ENV] = "CUSTOM_SERVER_KEY"

    config = GroundedAIServerRuntimeConfig.from_environment(values)
    assert config.server_api_key_environment_variable == "CUSTOM_SERVER_KEY"
