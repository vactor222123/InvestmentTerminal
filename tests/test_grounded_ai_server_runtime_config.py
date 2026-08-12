import pytest
from pathlib import Path

from investment_terminal.ai.providers.composition import (
    DEFAULT_OPENAI_API_KEY_ENV,
)
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    API_KEY_ENV_NAME_ENV,
    DATABASE_ENV,
    MAX_RETRIES_ENV,
    MODEL_ENV,
    TIMEOUT_ENV,
    GroundedAIServerRuntimeConfig,
)


def env():
    return {
        DATABASE_ENV: "data/knowledge/knowledge.db",
        MODEL_ENV: "gpt-test",
        ALLOWED_MODELS_ENV: "gpt-test,gpt-other",
    }


def test_runtime_config_parses_required_environment():
    config = GroundedAIServerRuntimeConfig.from_environment(env())

    assert config.database == Path(
        "data/knowledge/knowledge.db"
    )
    assert config.model_identity == "gpt-test"
    assert config.allowed_models == (
        "gpt-test",
        "gpt-other",
    )
    assert config.timeout_seconds == 30
    assert config.max_retries == 2
    assert (
        config.api_key_environment_variable
        == DEFAULT_OPENAI_API_KEY_ENV
    )

    assert config.governance_policy().assess(
        provider_identity="OPENAI",
        model_identity="gpt-test",
    ).allowed


def test_runtime_config_requires_model_to_be_allowlisted():
    values = env()
    values[MODEL_ENV] = "gpt-not-allowed"

    with pytest.raises(
        ValueError,
        match="explicitly present",
    ):
        GroundedAIServerRuntimeConfig.from_environment(
            values
        )


def test_runtime_config_requires_core_values():
    for name in (
        DATABASE_ENV,
        MODEL_ENV,
        ALLOWED_MODELS_ENV,
    ):
        values = env()
        del values[name]

        with pytest.raises(
            ValueError,
            match="required environment variable",
        ):
            GroundedAIServerRuntimeConfig.from_environment(
                values
            )


def test_runtime_config_parses_operational_overrides():
    values = env()
    values[TIMEOUT_ENV] = "12.5"
    values[MAX_RETRIES_ENV] = "4"
    values[API_KEY_ENV_NAME_ENV] = "CUSTOM_OPENAI_KEY"

    config = GroundedAIServerRuntimeConfig.from_environment(
        values
    )

    assert config.timeout_seconds == 12.5
    assert config.max_retries == 4
    assert (
        config.api_key_environment_variable
        == "CUSTOM_OPENAI_KEY"
    )
