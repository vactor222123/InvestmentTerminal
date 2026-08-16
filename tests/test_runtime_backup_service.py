import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.persistence.runtime_backup_service import (
    BACKUP_SET_IDENTITY,
    BACKUP_SET_SCHEMA_VERSION,
    RuntimeSQLiteBackupService,
    RuntimeSQLiteBackupSources,
)


CREATED_AT = datetime(
    2026,
    8,
    16,
    12,
    34,
    56,
    123456,
    tzinfo=timezone.utc,
)


def create_database(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    connection = sqlite3.connect(
        path
    )
    try:
        connection.execute(
            "PRAGMA journal_mode = WAL"
        )
        connection.execute(
            "CREATE TABLE records (value TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO records (value) VALUES (?)",
            (value,),
        )
        connection.commit()
    finally:
        connection.close()


def sources(
    tmp_path: Path,
) -> RuntimeSQLiteBackupSources:
    knowledge = tmp_path / "live" / "knowledge.db"
    ledger = tmp_path / "live" / "provider_usage_cost.db"
    generations = tmp_path / "live" / "grounded_generations.db"

    create_database(
        knowledge,
        "knowledge",
    )
    create_database(
        ledger,
        "ledger",
    )
    create_database(
        generations,
        "generation",
    )

    return RuntimeSQLiteBackupSources(
        knowledge_database=knowledge,
        usage_cost_ledger_database=ledger,
        grounded_generation_database=generations,
    )


def test_backup_set_has_deterministic_identity_and_complete_runtime_scope(
    tmp_path: Path,
) -> None:
    service = RuntimeSQLiteBackupService(
        backup_root=tmp_path / "backups",
        sources=sources(
            tmp_path
        ),
        clock=lambda: CREATED_AT,
    )

    result = service.create_backup_set()

    assert result.backup_set_id == (
        "runtime-sqlite-20260816T123456.123456Z"
    )
    assert result.directory.name == result.backup_set_id
    assert result.metadata_path == (
        result.directory
        / "metadata.json"
    )
    assert [
        backup.destination_path.name
        for backup in result.backups
    ] == [
        "knowledge.db",
        "provider_usage_cost.db",
        "grounded_generations.db",
    ]
    assert len(
        result.backups
    ) == 3


def test_metadata_is_deterministic_and_preserves_authority_classification(
    tmp_path: Path,
) -> None:
    service = RuntimeSQLiteBackupService(
        backup_root=tmp_path / "backups",
        sources=sources(
            tmp_path
        ),
        clock=lambda: CREATED_AT,
    )

    result = service.create_backup_set()
    metadata = json.loads(
        result.metadata_path.read_text(
            encoding="utf-8"
        )
    )

    assert metadata[
        "schema_version"
    ] == BACKUP_SET_SCHEMA_VERSION
    assert metadata[
        "identity"
    ] == BACKUP_SET_IDENTITY
    assert metadata[
        "backup_set_id"
    ] == result.backup_set_id
    assert metadata[
        "created_at"
    ] == CREATED_AT.isoformat()

    identities = [
        item["boundary_identity"]
        for item in metadata["databases"]
    ]
    assert identities == [
        "KNOWLEDGE_SQLITE@1",
        "PROVIDER_USAGE_COST_SQLITE@1",
        "GROUNDED_GENERATION_SQLITE@1",
    ]
    assert "HISTORY_SQLITE@1" not in identities

    assert [
        item["authority_class"]
        for item in metadata["databases"]
    ] == [
        "REBUILDABLE_DERIVED_STATE",
        "DURABLE_OPERATIONAL_RECORD",
        "DURABLE_GENERATED_EVIDENCE",
    ]


def test_backup_set_contains_readable_snapshots(
    tmp_path: Path,
) -> None:
    service = RuntimeSQLiteBackupService(
        backup_root=tmp_path / "backups",
        sources=sources(
            tmp_path
        ),
        clock=lambda: CREATED_AT,
    )

    result = service.create_backup_set()

    values: list[str] = []
    for backup in result.backups:
        with sqlite3.connect(
            backup.destination_path
        ) as connection:
            values.append(
                connection.execute(
                    "SELECT value FROM records"
                ).fetchone()[0]
            )

    assert values == [
        "knowledge",
        "ledger",
        "generation",
    ]


def test_partial_failure_publishes_no_backup_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backup_root = tmp_path / "backups"
    runtime_sources = sources(
        tmp_path
    )

    real_backup = (
        __import__(
            "investment_terminal.persistence.runtime_backup_service",
            fromlist=["backup_sqlite_database"],
        )
        .backup_sqlite_database
    )
    calls = 0

    def fail_second_backup(
        **kwargs: object,
    ):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError(
                "simulated backup failure"
            )
        return real_backup(
            **kwargs
        )

    monkeypatch.setattr(
        "investment_terminal.persistence.runtime_backup_service."
        "backup_sqlite_database",
        fail_second_backup,
    )

    service = RuntimeSQLiteBackupService(
        backup_root=backup_root,
        sources=runtime_sources,
        clock=lambda: CREATED_AT,
    )

    with pytest.raises(
        OSError,
        match="simulated backup failure",
    ):
        service.create_backup_set()

    assert list(
        backup_root.iterdir()
    ) == []


def test_existing_final_backup_set_is_not_overwritten(
    tmp_path: Path,
) -> None:
    backup_root = tmp_path / "backups"
    service = RuntimeSQLiteBackupService(
        backup_root=backup_root,
        sources=sources(
            tmp_path
        ),
        clock=lambda: CREATED_AT,
    )

    first = service.create_backup_set()

    with pytest.raises(
        FileExistsError,
    ):
        service.create_backup_set()

    assert first.metadata_path.exists()


def test_naive_clock_fails_closed_before_publication(
    tmp_path: Path,
) -> None:
    backup_root = tmp_path / "backups"
    service = RuntimeSQLiteBackupService(
        backup_root=backup_root,
        sources=sources(
            tmp_path
        ),
        clock=lambda: datetime(
            2026,
            8,
            16,
            12,
            0,
            0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        service.create_backup_set()

    assert not backup_root.exists()


def test_metadata_failure_publishes_no_backup_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backup_root = tmp_path / "backups"
    service = RuntimeSQLiteBackupService(
        backup_root=backup_root,
        sources=sources(
            tmp_path
        ),
        clock=lambda: CREATED_AT,
    )

    def fail_metadata(
        *args: object,
        **kwargs: object,
    ) -> Path:
        raise OSError(
            "metadata write failed"
        )

    monkeypatch.setattr(
        "investment_terminal.persistence.runtime_backup_service."
        "write_json_atomic",
        fail_metadata,
    )

    with pytest.raises(
        OSError,
        match="metadata write failed",
    ):
        service.create_backup_set()

    assert list(
        backup_root.iterdir()
    ) == []


def test_service_requires_runtime_sources_type(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        TypeError,
        match="RuntimeSQLiteBackupSources",
    ):
        RuntimeSQLiteBackupService(
            backup_root=tmp_path / "backups",
            sources=object(),  # type: ignore[arg-type]
            clock=lambda: CREATED_AT,
        )
