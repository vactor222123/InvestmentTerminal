from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from investment_terminal.ai.providers.usage_ledger import (
    GroundedProviderUsageCostLedgerRecord,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_repository import (
    SQLiteGroundedProviderUsageCostLedgerRepository,
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
    DEFAULT_OPENAI_API_KEY_ENV,
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


def runtime_environment(
    *,
    knowledge_database: Path,
    ledger_database: Path,
) -> dict[str, str]:
    return {
        DATABASE_ENV: str(knowledge_database),
        USAGE_COST_LEDGER_DATABASE_ENV: str(ledger_database),
        MODEL_ENV: "gpt-test",
        ALLOWED_MODELS_ENV: "gpt-test",
        PROVIDER_MAX_OUTPUT_TOKENS_ENV: "32",
        PROVIDER_MAX_TOTAL_TOKENS_ENV: "128",
        PROVIDER_MAX_TOTAL_COST_ENV: "1.50",
        PROVIDER_BUDGET_CURRENCY_ENV: "EUR",
        PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV: "0.10",
        PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV: "0.20",
        PROVIDER_PRICING_CURRENCY_ENV: "EUR",
        DEFAULT_OPENAI_API_KEY_ENV: "provider-secret",
    }


def record(
    request_id: str,
    *,
    minute: int,
    input_tokens: int,
    output_tokens: int,
    input_cost: str,
    output_cost: str,
) -> GroundedProviderUsageCostLedgerRecord:
    return GroundedProviderUsageCostLedgerRecord(
        request_id=request_id,
        provider_identity="OPENAI",
        model_identity="gpt-test",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        currency="EUR",
        input_cost=Decimal(input_cost),
        output_cost=Decimal(output_cost),
        total_cost=(
            Decimal(input_cost)
            + Decimal(output_cost)
        ),
        recorded_at=datetime(
            2026,
            8,
            15,
            12,
            minute,
            tzinfo=timezone.utc,
        ),
    )


def test_operational_usage_cost_ledger_end_to_end(
    tmp_path: Path,
) -> None:
    knowledge_database = (
        tmp_path
        / "knowledge.db"
    )
    knowledge_database.write_bytes(
        b"knowledge-placeholder"
    )
    ledger_database = (
        tmp_path
        / "provider_usage_cost.db"
    )

    environment = runtime_environment(
        knowledge_database=knowledge_database,
        ledger_database=ledger_database,
    )
    config = (
        GroundedAIServerRuntimeConfig
        .from_environment(
            environment
        )
    )

    assert (
        config.usage_cost_ledger_database
        == ledger_database
    )

    store = GroundedProviderUsageCostLedgerSQLiteStore(
        config.usage_cost_ledger_database
    )
    store.initialize()

    readiness = GroundedAIServerReadinessService(
        config=config,
        environment=environment,
    ).check()

    assert readiness.ready
    assert readiness.checks[
        "provider_usage_cost_database"
    ] == "READY"

    repository = (
        SQLiteGroundedProviderUsageCostLedgerRepository(
            store
        )
    )

    repository.add(
        record(
            "request-001",
            minute=0,
            input_tokens=100,
            output_tokens=40,
            input_cost="0.1000000000000000001",
            output_cost="0.2000000000000000002",
        )
    )
    repository.add(
        record(
            "request-002",
            minute=1,
            input_tokens=200,
            output_tokens=60,
            input_cost="0.3000000000000000003",
            output_cost="0.4000000000000000004",
        )
    )
    repository.add(
        record(
            "request-003",
            minute=2,
            input_tokens=50,
            output_tokens=10,
            input_cost="0.5000000000000000005",
            output_cost="0.6000000000000000006",
        )
    )

    reopened = (
        SQLiteGroundedProviderUsageCostLedgerRepository(
            GroundedProviderUsageCostLedgerSQLiteStore(
                ledger_database
            )
        )
    )

    assert [
        item.request_id
        for item in reopened.list_recent(
            2
        )
    ] == [
        "request-003",
        "request-002",
    ]

    assert [
        item.request_id
        for item in reopened.list_between(
            datetime(
                2026,
                8,
                15,
                12,
                0,
                tzinfo=timezone.utc,
            ),
            datetime(
                2026,
                8,
                15,
                12,
                2,
                tzinfo=timezone.utc,
            ),
        )
    ] == [
        "request-001",
        "request-002",
    ]

    summary = reopened.summarize()

    assert summary.request_count == 3
    assert summary.currency == "EUR"
    assert summary.input_tokens == 350
    assert summary.output_tokens == 110
    assert summary.total_tokens == 460
    assert summary.input_cost == Decimal(
        "0.9000000000000000009"
    )
    assert summary.output_cost == Decimal(
        "1.2000000000000000012"
    )
    assert summary.total_cost == Decimal(
        "2.1000000000000000021"
    )

    final_readiness = (
        GroundedAIServerReadinessService(
            config=config,
            environment=environment,
        )
        .check()
    )

    assert final_readiness.ready


def test_corrupt_operational_ledger_fails_readiness_after_restart(
    tmp_path: Path,
) -> None:
    knowledge_database = (
        tmp_path
        / "knowledge.db"
    )
    knowledge_database.write_bytes(
        b"knowledge-placeholder"
    )
    ledger_database = (
        tmp_path
        / "provider_usage_cost.db"
    )

    environment = runtime_environment(
        knowledge_database=knowledge_database,
        ledger_database=ledger_database,
    )
    config = (
        GroundedAIServerRuntimeConfig
        .from_environment(
            environment
        )
    )

    store = GroundedProviderUsageCostLedgerSQLiteStore(
        ledger_database
    )
    store.initialize()

    assert GroundedAIServerReadinessService(
        config=config,
        environment=environment,
    ).check().ready

    connection = store.connect()
    try:
        connection.execute(
            "PRAGMA wal_checkpoint(TRUNCATE)"
        )
    finally:
        connection.close()

    for suffix in (
        "-wal",
        "-shm",
    ):
        sidecar = Path(
            f"{ledger_database}{suffix}"
        )
        if sidecar.exists():
            sidecar.unlink()

    ledger_database.write_bytes(
        b"corrupt-sqlite"
    )

    assessment = (
        GroundedAIServerReadinessService(
            config=config,
            environment=environment,
        )
        .check()
    )

    assert not assessment.ready
    assert assessment.checks[
        "provider_usage_cost_database"
    ] == "NOT_READY"
