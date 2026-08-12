from pathlib import Path

from investment_terminal.ai.providers.composition import (
    DEFAULT_OPENAI_API_KEY_ENV,
)
from investment_terminal.server.readiness import (
    GroundedAIServerReadinessService,
)
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    MODEL_ENV,
    GroundedAIServerRuntimeConfig,
)


def config_for(
    database: Path,
):
    return GroundedAIServerRuntimeConfig.from_environment(
        {
            DATABASE_ENV: str(database),
            MODEL_ENV: "gpt-test",
            ALLOWED_MODELS_ENV: "gpt-test",
        }
    )


def test_readiness_is_ready_with_database_and_credentials(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"")

    assessment = GroundedAIServerReadinessService(
        config=config_for(database),
        environment={
            DEFAULT_OPENAI_API_KEY_ENV: "secret",
        },
    ).check()

    assert assessment.ready
    assert assessment.to_dict() == {
        "status": "READY",
        "checks": {
            "knowledge_database": "READY",
            "provider_credentials": "READY",
        },
    }


def test_readiness_fails_without_credentials(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"")

    assessment = GroundedAIServerReadinessService(
        config=config_for(database),
        environment={},
    ).check()

    assert not assessment.ready
    assert (
        assessment.checks["provider_credentials"]
        == "NOT_READY"
    )


def test_readiness_fails_if_database_disappears(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"

    assessment = GroundedAIServerReadinessService(
        config=config_for(database),
        environment={
            DEFAULT_OPENAI_API_KEY_ENV: "secret",
        },
    ).check()

    assert not assessment.ready
    assert (
        assessment.checks["knowledge_database"]
        == "NOT_READY"
    )
