import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.cli.ingest_history_knowledge import (
    main,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_schema_migrations import (
    HISTORICAL_SCHEMA_MIGRATIONS,
    HISTORICAL_SCHEMA_TARGET_VERSION,
    HistoricalSchemaMigrator,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.knowledge.sqlite_repository import (
    SQLiteKnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_store import (
    KnowledgeSQLiteStore,
)


SNAPSHOT_A = "11111111-1111-4111-8111-111111111111"
SNAPSHOT_B = "22222222-2222-4222-8222-222222222222"


def dt(day: int, hour: int = 0) -> datetime:
    return datetime(
        2026,
        8,
        day,
        hour,
        0,
        tzinfo=timezone.utc,
    )


def snapshot(
    snapshot_id: str,
    *,
    generated_at: datetime,
    archived_at: datetime,
) -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=snapshot_id,
        package_id=f"pkg-{snapshot_id[:4]}",
        package_schema_version="1",
        product_version="27.0",
        generated_at=generated_at,
        archived_at=archived_at,
        relative_path=f"{snapshot_id}.json",
        checksum_sha256=snapshot_id[0] * 64,
    )


def build_history_database(
    path: Path,
) -> None:
    store = HistoricalSQLiteStore(path)
    store.initialize()
    HistoricalSchemaMigrator(
        store=store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()

    snapshots = HistoricalSnapshotRepository(store)
    states = HistoricalImportStateRepository(store)

    verified = snapshot(
        SNAPSHOT_A,
        generated_at=dt(1),
        archived_at=dt(2),
    )
    metadata_only = snapshot(
        SNAPSHOT_B,
        generated_at=dt(3),
        archived_at=dt(4),
    )

    snapshots.add(verified)
    snapshots.add(metadata_only)

    states.initialize_metadata(
        verified,
        at=dt(5),
    )
    states.mark_verified(
        verified.snapshot_id,
        at=dt(6),
    )

    states.initialize_metadata(
        metadata_only,
        at=dt(5),
    )


def common_args(
    history_database: Path,
    knowledge_database: Path,
) -> list[str]:
    return [
        "--history-database",
        str(history_database),
        "--knowledge-database",
        str(knowledge_database),
        "--subject",
        "portfolio",
        "--generated-at",
        dt(20).isoformat(),
    ]


def test_cli_composes_real_history_and_knowledge_sqlite(
    tmp_path: Path,
    capsys,
) -> None:
    history_database = tmp_path / "history.db"
    knowledge_database = tmp_path / "knowledge.db"
    build_history_database(history_database)

    main(
        common_args(
            history_database,
            knowledge_database,
        )
        + [
            "--all",
            "--version",
            "2",
            "--json",
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report["dry_run"] is False
    assert report["scope"] == "ALL"
    assert report["history_snapshots"] == 2
    assert report["knowledge_records"] == 1
    assert report["subject"] == "portfolio"
    assert report["version"] == 2
    assert report["records"][0]["knowledge_id"] == (
        f"HISTORICAL_SNAPSHOT_FACT:{SNAPSHOT_A}"
    )

    repository = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(
            knowledge_database
        )
    )
    records = repository.list_all()

    assert len(records) == 1
    assert records[0].knowledge_id == (
        f"HISTORICAL_SNAPSHOT_FACT:{SNAPSHOT_A}"
    )
    assert records[0].version == 2
    assert records[0].subject_key == "portfolio"
    assert records[0].evidence[0].evidence_id == SNAPSHOT_A


def test_cli_reingestion_is_idempotent_with_real_sqlite(
    tmp_path: Path,
    capsys,
) -> None:
    history_database = tmp_path / "history.db"
    knowledge_database = tmp_path / "knowledge.db"
    build_history_database(history_database)

    argv = (
        common_args(
            history_database,
            knowledge_database,
        )
        + [
            "--all",
            "--version",
            "1",
            "--json",
        ]
    )

    main(argv)
    first_report = json.loads(
        capsys.readouterr().out
    )

    main(argv)
    second_report = json.loads(
        capsys.readouterr().out
    )

    assert second_report == first_report

    repository = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(
            knowledge_database
        )
    )
    assert len(repository.list_all()) == 1


def test_cli_explicit_snapshot_scope_ingests_only_selected_snapshot(
    tmp_path: Path,
    capsys,
) -> None:
    history_database = tmp_path / "history.db"
    knowledge_database = tmp_path / "knowledge.db"
    build_history_database(history_database)

    main(
        common_args(
            history_database,
            knowledge_database,
        )
        + [
            "--snapshot-id",
            SNAPSHOT_A,
            "--json",
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report["scope"] == "EXPLICIT"
    assert report["selected_snapshot_ids"] == [
        SNAPSHOT_A,
    ]
    assert report["history_snapshots"] == 1
    assert report["knowledge_records"] == 1


def test_cli_dry_run_does_not_create_target_knowledge_database(
    tmp_path: Path,
    capsys,
) -> None:
    history_database = tmp_path / "history.db"
    knowledge_database = tmp_path / "knowledge.db"
    build_history_database(history_database)

    main(
        common_args(
            history_database,
            knowledge_database,
        )
        + [
            "--snapshot-id",
            SNAPSHOT_A,
            "--dry-run",
            "--json",
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report["dry_run"] is True
    assert report["knowledge_records"] == 1
    assert report["records"][0]["knowledge_id"] == (
        f"HISTORICAL_SNAPSHOT_FACT:{SNAPSHOT_A}"
    )
    assert not knowledge_database.exists()


def test_cli_requires_explicit_scope(
    tmp_path: Path,
) -> None:
    history_database = tmp_path / "history.db"
    knowledge_database = tmp_path / "knowledge.db"
    build_history_database(history_database)

    with pytest.raises(SystemExit) as exc:
        main(
            common_args(
                history_database,
                knowledge_database,
            )
        )

    assert exc.value.code == 2
    assert not knowledge_database.exists()


def test_cli_rejects_duplicate_explicit_snapshot_ids(
    tmp_path: Path,
) -> None:
    history_database = tmp_path / "history.db"
    knowledge_database = tmp_path / "knowledge.db"
    build_history_database(history_database)

    with pytest.raises(SystemExit) as exc:
        main(
            common_args(
                history_database,
                knowledge_database,
            )
            + [
                "--snapshot-id",
                SNAPSHOT_A,
                "--snapshot-id",
                SNAPSHOT_A,
            ]
        )

    assert exc.value.code == 2
    assert not knowledge_database.exists()


def test_cli_fails_closed_when_history_state_is_missing(
    tmp_path: Path,
) -> None:
    history_database = tmp_path / "history.db"
    knowledge_database = tmp_path / "knowledge.db"

    store = HistoricalSQLiteStore(
        history_database
    )
    store.initialize()
    HistoricalSchemaMigrator(
        store=store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()

    HistoricalSnapshotRepository(store).add(
        snapshot(
            SNAPSHOT_A,
            generated_at=dt(1),
            archived_at=dt(2),
        )
    )

    with pytest.raises(SystemExit) as exc:
        main(
            common_args(
                history_database,
                knowledge_database,
            )
            + [
                "--snapshot-id",
                SNAPSHOT_A,
            ]
        )

    assert exc.value.code == 2
    assert not knowledge_database.exists()


def test_cli_requires_existing_history_database(
    tmp_path: Path,
) -> None:
    history_database = tmp_path / "missing.db"
    knowledge_database = tmp_path / "knowledge.db"

    with pytest.raises(SystemExit) as exc:
        main(
            common_args(
                history_database,
                knowledge_database,
            )
            + [
                "--all",
            ]
        )

    assert exc.value.code == 2
