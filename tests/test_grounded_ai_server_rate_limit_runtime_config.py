from decimal import Decimal

import pytest

from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    DEFAULT_RATE_LIMIT_CAPACITY,
    DEFAULT_RATE_LIMIT_REFILL_PER_SECOND,
    MODEL_ENV,
    RATE_LIMIT_CAPACITY_ENV,
    RATE_LIMIT_REFILL_PER_SECOND_ENV,
    GroundedAIServerRuntimeConfig,
)


def environment():
    return {
        DATABASE_ENV: "data/knowledge/knowledge.db",
        MODEL_ENV: "gpt-test",
        ALLOWED_MODELS_ENV: "gpt-test",
    }


def test_runtime_config_uses_rate_limit_defaults() -> None:
    config = GroundedAIServerRuntimeConfig.from_environment(
        environment()
    )

    assert (
        config.rate_limit_capacity
        == DEFAULT_RATE_LIMIT_CAPACITY
    )
    assert (
        config.rate_limit_refill_tokens_per_second
        == DEFAULT_RATE_LIMIT_REFILL_PER_SECOND
    )


def test_runtime_config_accepts_rate_limit_overrides() -> None:
    values = environment()
    values[RATE_LIMIT_CAPACITY_ENV] = "25"
    values[RATE_LIMIT_REFILL_PER_SECOND_ENV] = "2.5"

    config = GroundedAIServerRuntimeConfig.from_environment(
        values
    )

    assert config.rate_limit_capacity == 25
    assert (
        config.rate_limit_refill_tokens_per_second
        == Decimal("2.5")
    )


@pytest.mark.parametrize(
    ("name", "value"),
    [
        (RATE_LIMIT_CAPACITY_ENV, "0"),
        (RATE_LIMIT_CAPACITY_ENV, "-1"),
        (RATE_LIMIT_CAPACITY_ENV, "x"),
        (RATE_LIMIT_REFILL_PER_SECOND_ENV, "0"),
        (RATE_LIMIT_REFILL_PER_SECOND_ENV, "-1"),
        (RATE_LIMIT_REFILL_PER_SECOND_ENV, "NaN"),
        (RATE_LIMIT_REFILL_PER_SECOND_ENV, "x"),
    ],
)
def test_runtime_config_rejects_invalid_rate_limit_values(
    name,
    value,
) -> None:
    values = environment()
    values[name] = value

    with pytest.raises(
        ValueError,
    ):
        GroundedAIServerRuntimeConfig.from_environment(
            values
        )
