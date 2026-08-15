import sqlite3
from pathlib import Path

import pytest

from investment_terminal.ai.providers.usage_ledger_sqlite_store import (
    GroundedProviderUsageCostLedgerSQLiteStore,
)


def test_store_requires_supported_database_suffix(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="database_path",
    ):
        GroundedProviderUsageCostLedgerSQLiteStore(
            tmp_path / "ledger.txt"
        )


def test_initialize_creates_parent_and_schema(
    tmp_path: Path,
) -> None:
    database = (
        tmp_path
        / "nested"
        / "provider_usage.db"
    )
    store = GroundedProviderUsageCostLedgerSQLiteStore(
        database
    )

    assert store.initialize() == database
    assert database.exists()
    assert store.schema_version() == 1
    assert store.table_names() == (
        "provider_usage_cost_ledger",
        "provider_usage_cost_schema_metadata",
    )


def test_initialize_is_idempotent(
    tmp_path: Path,
) -> None:
    store = GroundedProviderUsageCostLedgerSQLiteStore(
        tmp_path / "provider_usage.db"
    )

    store.initialize()
    store.initialize()

    assert store.schema_version() == 1


def test_schema_version_is_none_before_initialization(
    tmp_path: Path,
) -> None:
    store = GroundedProviderUsageCostLedgerSQLiteStore(
        tmp_path / "provider_usage.db"
    )

    assert store.schema_version() is None


def test_transaction_commits(
    tmp_path: Path,
) -> None:
    store = GroundedProviderUsageCostLedgerSQLiteStore(
        tmp_path / "provider_usage.db"
    )

    with store.transaction() as connection:
        connection.execute(
            """
            INSERT INTO provider_usage_cost_ledger (
                request_id,
                provider_identity,
                model_identity,
                input_tokens,
                output_tokens,
                total_tokens,
                currency,
                input_cost,
                output_cost,
                total_cost,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "request-001",
                "OPENAI",
                "gpt-test",
                10,
                5,
                15,
                "EUR",
                "0.001",
                "0.002",
                "0.003",
                "2026-08-15T12:00:00+00:00",
            ),
        )

    with store.connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM provider_usage_cost_ledger"
        ).fetchone()[0]

    assert count == 1


def test_transaction_rolls_back(
    tmp_path: Path,
) -> None:
    store = GroundedProviderUsageCostLedgerSQLiteStore(
        tmp_path / "provider_usage.db"
    )

    with pytest.raises(RuntimeError):
        with store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO provider_usage_cost_ledger (
                    request_id,
                    provider_identity,
                    model_identity,
                    input_tokens,
                    output_tokens,
                    total_tokens,
                    currency,
                    input_cost,
                    output_cost,
                    total_cost,
                    recorded_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "request-001",
                    "OPENAI",
                    "gpt-test",
                    10,
                    5,
                    15,
                    "EUR",
                    "0.001",
                    "0.002",
                    "0.003",
                    "2026-08-15T12:00:00+00:00",
                ),
            )
            raise RuntimeError("interrupt")

    with store.connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM provider_usage_cost_ledger"
        ).fetchone()[0]

    assert count == 0


def test_schema_rejects_inconsistent_token_total(
    tmp_path: Path,
) -> None:
    store = GroundedProviderUsageCostLedgerSQLiteStore(
        tmp_path / "provider_usage.db"
    )
    store.initialize()

    with pytest.raises(sqlite3.IntegrityError):
        with store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO provider_usage_cost_ledger (
                    request_id,
                    provider_identity,
                    model_identity,
                    input_tokens,
                    output_tokens,
                    total_tokens,
                    currency,
                    input_cost,
                    output_cost,
                    total_cost,
                    recorded_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "request-001",
                    "OPENAI",
                    "gpt-test",
                    10,
                    5,
                    16,
                    "EUR",
                    "0.001",
                    "0.002",
                    "0.003",
                    "2026-08-15T12:00:00+00:00",
                ),
            )
