import pytest

from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    DEFAULT_MAX_REQUEST_BODY_BYTES,
    MAX_REQUEST_BODY_BYTES_ENV,
    MODEL_ENV,
    GroundedAIServerRuntimeConfig,
)


def base_environment():
    return {
        DATABASE_ENV: "data/knowledge/knowledge.db",
        MODEL_ENV: "gpt-test",
        ALLOWED_MODELS_ENV: "gpt-test",
    }


def test_runtime_config_uses_default_request_body_limit() -> None:
    config = GroundedAIServerRuntimeConfig.from_environment(
        base_environment()
    )

    assert (
        config.max_request_body_bytes
        == DEFAULT_MAX_REQUEST_BODY_BYTES
    )


def test_runtime_config_accepts_request_body_limit_override() -> None:
    values = base_environment()
    values[
        MAX_REQUEST_BODY_BYTES_ENV
    ] = "2048"

    config = GroundedAIServerRuntimeConfig.from_environment(
        values
    )

    assert config.max_request_body_bytes == 2048


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "-1",
        "abc",
    ],
)
def test_runtime_config_rejects_invalid_request_body_limit(
    value,
) -> None:
    values = base_environment()
    values[
        MAX_REQUEST_BODY_BYTES_ENV
    ] = value

    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        GroundedAIServerRuntimeConfig.from_environment(
            values
        )
