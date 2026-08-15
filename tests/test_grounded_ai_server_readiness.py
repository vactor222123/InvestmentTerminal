import sqlite3
from pathlib import Path

from investment_terminal.ai.generation_sqlite_store import (
    GroundedGenerationSQLiteStore,
)
from investment_terminal.ai.providers.composition import (
    DEFAULT_OPENAI_API_KEY_ENV,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_store import (
    GroundedProviderUsageCostLedgerSQLiteStore,
)
from investment_terminal.server.readiness import (
    GroundedAIServerReadinessService,
)
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    MODEL_ENV,
    PROVIDER_BUDGET_CURRENCY_ENV,
    PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_MAX_OUTPUT_TOKENS_ENV,
    PROVIDER_MAX_TOTAL_COST_ENV,
    PROVIDER_MAX_TOTAL_TOKENS_ENV,
    PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_PRICING_CURRENCY_ENV,
    USAGE_COST_LEDGER_DATABASE_ENV,
    GroundedAIServerRuntimeConfig,
)


def config_for(
    database: Path,
):
    return GroundedAIServerRuntimeConfig.from_environment(
        {
            DATABASE_ENV: str(database),
            USAGE_COST_LEDGER_DATABASE_ENV: str(
                database.with_name("provider_usage_cost.db")
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
    )


def ledger_database_for(
    database: Path,
) -> Path:
    return database.with_name(
        "provider_usage_cost.db"
    )


def generation_database_for(
    database: Path,
) -> Path:
    return database.with_name(
        "grounded_generations.db"
    )


def initialize_ledger(
    database: Path,
) -> None:
    GroundedProviderUsageCostLedgerSQLiteStore(
        ledger_database_for(database)
    ).initialize()


def initialize_generations(
    database: Path,
) -> None:
    GroundedGenerationSQLiteStore(
        generation_database_for(database)
    ).initialize()


def prepare_databases(
    database: Path,
) -> None:
    database.write_bytes(b"")
    initialize_ledger(database)
    initialize_generations(database)


def assessment_for(
    database: Path,
    *,
    credentials: bool = True,
):
    environment = {}
    if credentials:
        environment[
            DEFAULT_OPENAI_API_KEY_ENV
        ] = "secret"

    return GroundedAIServerReadinessService(
        config=config_for(database),
        environment=environment,
    ).check()


def test_readiness_is_ready_with_all_local_prerequisites(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    prepare_databases(database)

    assessment = assessment_for(database)

    assert assessment.ready
    assert assessment.to_dict() == {
        "status": "READY",
        "checks": {
            "knowledge_database": "READY",
            "provider_usage_cost_database": "READY",
            "grounded_generation_database": "READY",
            "provider_credentials": "READY",
        },
    }


def test_readiness_fails_if_grounded_generation_database_is_missing(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"")
    initialize_ledger(database)

    assessment = assessment_for(database)

    assert not assessment.ready
    assert (
        assessment.checks["grounded_generation_database"]
        == "NOT_READY"
    )
    assert not generation_database_for(database).exists()


def test_readiness_does_not_create_missing_grounded_generation_database(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"")
    initialize_ledger(database)

    assessment_for(database)

    assert not generation_database_for(database).exists()


def test_readiness_fails_for_uninitialized_grounded_generation_database(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"")
    initialize_ledger(database)
    generation_database_for(database).write_bytes(b"")

    assessment = assessment_for(database)

    assert not assessment.ready
    assert (
        assessment.checks["grounded_generation_database"]
        == "NOT_READY"
    )


def test_readiness_fails_for_wrong_grounded_generation_schema_version(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    prepare_databases(database)

    generation_database = generation_database_for(database)
    with sqlite3.connect(generation_database) as connection:
        connection.execute(
            """
            UPDATE grounded_generation_schema_metadata
            SET value = '999'
            WHERE key = 'schema_version'
            """
        )

    assessment = assessment_for(database)

    assert not assessment.ready
    assert (
        assessment.checks["grounded_generation_database"]
        == "NOT_READY"
    )


def test_readiness_fails_for_corrupt_grounded_generation_database(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"")
    initialize_ledger(database)
    generation_database_for(database).write_bytes(
        b"not-a-sqlite-database"
    )

    assessment = assessment_for(database)

    assert not assessment.ready
    assert (
        assessment.checks["grounded_generation_database"]
        == "NOT_READY"
    )


def test_readiness_fails_without_credentials(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    prepare_databases(database)

    assessment = assessment_for(
        database,
        credentials=False,
    )

    assert not assessment.ready
    assert assessment.checks["provider_credentials"] == "NOT_READY"


def test_readiness_fails_if_knowledge_database_disappears(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    initialize_ledger(database)
    initialize_generations(database)

    assessment = assessment_for(database)

    assert not assessment.ready
    assert assessment.checks["knowledge_database"] == "NOT_READY"


def test_readiness_fails_if_usage_cost_database_is_missing(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"")
    initialize_generations(database)

    assessment = assessment_for(database)

    assert not assessment.ready
    assert (
        assessment.checks["provider_usage_cost_database"]
        == "NOT_READY"
    )


def test_readiness_fails_for_wrong_usage_cost_schema_version(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    prepare_databases(database)

    ledger_database = ledger_database_for(database)
    with sqlite3.connect(ledger_database) as connection:
        connection.execute(
            """
            UPDATE provider_usage_cost_schema_metadata
            SET value = '999'
            WHERE key = 'schema_version'
            """
        )

    assessment = assessment_for(database)

    assert not assessment.ready
    assert (
        assessment.checks["provider_usage_cost_database"]
        == "NOT_READY"
    )
