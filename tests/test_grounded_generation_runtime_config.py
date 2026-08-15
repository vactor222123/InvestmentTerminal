from pathlib import Path

from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    GROUNDED_GENERATION_DATABASE_ENV,
    MODEL_ENV,
    PROVIDER_BUDGET_CURRENCY_ENV,
    PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_MAX_OUTPUT_TOKENS_ENV,
    PROVIDER_MAX_TOTAL_COST_ENV,
    PROVIDER_MAX_TOTAL_TOKENS_ENV,
    PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_PRICING_CURRENCY_ENV,
    RUNTIME_DATA_ROOT_ENV,
    USAGE_COST_LEDGER_DATABASE_ENV,
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
        PROVIDER_BUDGET_CURRENCY_ENV: "EUR",
        PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV: "0.10",
        PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV: "0.20",
        PROVIDER_PRICING_CURRENCY_ENV: "EUR",
    }


def test_runtime_data_root_is_optional_for_backward_compatibility() -> None:
    config = GroundedAIServerRuntimeConfig.from_environment(
        environment()
    )

    assert config.runtime_data_root is None


def test_runtime_data_root_can_be_configured_without_relocating_paths() -> None:
    values = environment()
    values[RUNTIME_DATA_ROOT_ENV] = "data/knowledge"

    config = GroundedAIServerRuntimeConfig.from_environment(
        values
    )

    assert config.runtime_data_root == Path(
        "data/knowledge"
    )
    assert config.database == Path(
        "data/knowledge/knowledge.db"
    )
    assert config.usage_cost_ledger_database == Path(
        "data/knowledge/provider_usage_cost.db"
    )


def test_grounded_generation_database_defaults_next_to_usage_ledger() -> None:
    config = GroundedAIServerRuntimeConfig.from_environment(
        environment()
    )

    assert config.grounded_generation_database == Path(
        "data/knowledge/grounded_generations.db"
    )


def test_grounded_generation_database_can_be_overridden() -> None:
    values = environment()
    values[GROUNDED_GENERATION_DATABASE_ENV] = (
        "data/generations/custom.db"
    )

    config = GroundedAIServerRuntimeConfig.from_environment(
        values
    )

    assert config.grounded_generation_database == Path(
        "data/generations/custom.db"
    )
