from pathlib import Path

from investment_terminal.ai.providers.usage_ledger_sqlite_store import (
    GroundedProviderUsageCostLedgerSQLiteStore,
)


def sidecar(
    database: Path,
    suffix: str,
) -> Path:
    return Path(
        f"{database}{suffix}"
    )


def test_initialize_and_metadata_reads_release_sqlite_connections(
    tmp_path: Path,
) -> None:
    database = tmp_path / "provider_usage.db"
    store = GroundedProviderUsageCostLedgerSQLiteStore(
        database
    )

    store.initialize()
    assert store.schema_version() == 1
    assert (
        "provider_usage_cost_ledger"
        in store.table_names()
    )

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
        candidate = sidecar(
            database,
            suffix,
        )
        if candidate.exists():
            candidate.unlink()

    assert not sidecar(
        database,
        "-wal",
    ).exists()
    assert not sidecar(
        database,
        "-shm",
    ).exists()
