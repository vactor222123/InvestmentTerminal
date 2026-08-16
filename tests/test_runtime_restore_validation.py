import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.ai.generation_sqlite_store import (
    GroundedGenerationSQLiteStore,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_store import (
    GroundedProviderUsageCostLedgerSQLiteStore,
)
from investment_terminal.knowledge.sqlite_store import (
    KnowledgeSQLiteStore,
)
from investment_terminal.persistence.runtime_backup_service import (
    RuntimeSQLiteBackupService,
    RuntimeSQLiteBackupSources,
)
from investment_terminal.persistence.runtime_restore_validation import (
    validate_runtime_sqlite_restore_candidate,
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


def initialized_sources(
    tmp_path: Path,
) -> RuntimeSQLiteBackupSources:
    knowledge = tmp_path / "live" / "knowledge.db"
    ledger = tmp_path / "live" / "provider_usage_cost.db"
    generations = tmp_path / "live" / "grounded_generations.db"

    KnowledgeSQLiteStore(
        knowledge
    ).initialize()
    GroundedProviderUsageCostLedgerSQLiteStore(
        ledger
    ).initialize()
    GroundedGenerationSQLiteStore(
        generations
    ).initialize()

    return RuntimeSQLiteBackupSources(
        knowledge_database=knowledge,
        usage_cost_ledger_database=ledger,
        grounded_generation_database=generations,
    )


def backup_set(
    tmp_path: Path,
) -> Path:
    result = RuntimeSQLiteBackupService(
        backup_root=tmp_path / "backups",
        sources=initialized_sources(
            tmp_path
        ),
        clock=lambda: CREATED_AT,
    ).create_backup_set()
    return result.directory


def metadata(
    directory: Path,
) -> dict[str, object]:
    return json.loads(
        (
            directory
            / "metadata.json"
        ).read_text(
            encoding="utf-8"
        )
    )


def write_metadata(
    directory: Path,
    value: dict[str, object],
) -> None:
    (
        directory
        / "metadata.json"
    ).write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_valid_complete_backup_set_is_accepted(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )

    candidate = validate_runtime_sqlite_restore_candidate(
        directory
    )

    assert candidate.backup_set_id == directory.name
    assert candidate.created_at == CREATED_AT
    assert [
        item.boundary_identity
        for item in candidate.databases
    ] == [
        "KNOWLEDGE_SQLITE@1",
        "PROVIDER_USAGE_COST_SQLITE@1",
        "GROUNDED_GENERATION_SQLITE@1",
    ]
    assert all(
        item.schema_version == 1
        for item in candidate.databases
    )


def test_validator_does_not_create_new_sidecar_artifacts(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    before = {
        path.name
        for path in directory.iterdir()
        if path.name.endswith(
            (
                "-wal",
                "-shm",
            )
        )
    }

    validate_runtime_sqlite_restore_candidate(
        directory
    )

    after = {
        path.name
        for path in directory.iterdir()
        if path.name.endswith(
            (
                "-wal",
                "-shm",
            )
        )
    }
    assert after == before


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 999),
        ("identity", "WRONG@1"),
    ],
)
def test_backup_set_identity_contract_fails_closed(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    directory = backup_set(
        tmp_path
    )
    value_map = metadata(
        directory
    )
    value_map[field] = value
    write_metadata(
        directory,
        value_map,
    )

    with pytest.raises(
        ValueError,
    ):
        validate_runtime_sqlite_restore_candidate(
            directory
        )


def test_directory_name_must_match_backup_set_id(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    value = metadata(
        directory
    )
    value["backup_set_id"] = "other-id"
    write_metadata(
        directory,
        value,
    )

    with pytest.raises(
        ValueError,
        match="directory name",
    ):
        validate_runtime_sqlite_restore_candidate(
            directory
        )


def test_missing_runtime_boundary_fails_closed(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    value = metadata(
        directory
    )
    value["databases"] = value["databases"][:-1]
    write_metadata(
        directory,
        value,
    )

    with pytest.raises(
        ValueError,
        match="exactly three",
    ):
        validate_runtime_sqlite_restore_candidate(
            directory
        )


def test_duplicate_boundary_fails_closed(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    value = metadata(
        directory
    )
    databases = value["databases"]
    databases[2] = dict(
        databases[0]
    )
    write_metadata(
        directory,
        value,
    )

    with pytest.raises(
        ValueError,
        match="duplicate boundary_identity",
    ):
        validate_runtime_sqlite_restore_candidate(
            directory
        )


def test_history_boundary_is_rejected(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    value = metadata(
        directory
    )
    databases = value["databases"]
    databases[0]["boundary_identity"] = "HISTORY_SQLITE@1"
    write_metadata(
        directory,
        value,
    )

    with pytest.raises(
        ValueError,
        match="unexpected runtime backup boundary",
    ):
        validate_runtime_sqlite_restore_candidate(
            directory
        )


def test_backup_filename_path_traversal_is_rejected(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    value = metadata(
        directory
    )
    value["databases"][0]["backup_file"] = "../knowledge.db"
    write_metadata(
        directory,
        value,
    )

    with pytest.raises(
        ValueError,
        match="unexpected backup_file",
    ):
        validate_runtime_sqlite_restore_candidate(
            directory
        )


def test_missing_backup_file_fails_closed(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    (
        directory
        / "knowledge.db"
    ).unlink()

    with pytest.raises(
        FileNotFoundError,
    ):
        validate_runtime_sqlite_restore_candidate(
            directory
        )


def test_sqlite_managed_sidecars_do_not_make_backup_set_invalid(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    (
        directory
        / "knowledge.db-wal"
    ).write_bytes(
        b""
    )
    (
        directory
        / "knowledge.db-shm"
    ).write_bytes(
        b""
    )

    candidate = validate_runtime_sqlite_restore_candidate(
        directory
    )

    assert candidate.backup_set_id == directory.name


def test_extra_artifact_fails_closed(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    (
        directory
        / "unexpected.txt"
    ).write_text(
        "unexpected",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="unexpected backup set artifacts",
    ):
        validate_runtime_sqlite_restore_candidate(
            directory
        )


def test_size_metadata_mismatch_fails_closed(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    value = metadata(
        directory
    )
    value["databases"][0]["size_bytes"] += 1
    write_metadata(
        directory,
        value,
    )

    with pytest.raises(
        ValueError,
        match="size_bytes mismatch",
    ):
        validate_runtime_sqlite_restore_candidate(
            directory
        )


def test_authority_metadata_mismatch_fails_closed(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    value = metadata(
        directory
    )
    value["databases"][0][
        "authority_class"
    ] = "DURABLE_OPERATIONAL_RECORD"
    write_metadata(
        directory,
        value,
    )

    with pytest.raises(
        ValueError,
        match="authority_class mismatch",
    ):
        validate_runtime_sqlite_restore_candidate(
            directory
        )


def test_corrupt_sqlite_fails_closed(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    knowledge = directory / "knowledge.db"
    original_size = knowledge.stat().st_size
    knowledge.write_bytes(
        b"x" * original_size
    )

    with pytest.raises(
        sqlite3.DatabaseError,
    ):
        validate_runtime_sqlite_restore_candidate(
            directory
        )


def test_incompatible_schema_version_fails_closed(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    database = (
        directory
        / "provider_usage_cost.db"
    )
    with sqlite3.connect(
        database
    ) as connection:
        connection.execute(
            "PRAGMA journal_mode = DELETE"
        )
        connection.execute(
            """
            UPDATE provider_usage_cost_schema_metadata
            SET value = '999'
            WHERE key = 'schema_version'
            """
        )
        connection.commit()

    value = metadata(
        directory
    )
    for item in value["databases"]:
        if (
            item["boundary_identity"]
            == "PROVIDER_USAGE_COST_SQLITE@1"
        ):
            item["size_bytes"] = database.stat().st_size
    write_metadata(
        directory,
        value,
    )

    with pytest.raises(
        ValueError,
        match="incompatible schema_version",
    ):
        validate_runtime_sqlite_restore_candidate(
            directory
        )


def test_wrong_database_mapped_to_boundary_fails_schema_validation(
    tmp_path: Path,
) -> None:
    directory = backup_set(
        tmp_path
    )
    knowledge = directory / "knowledge.db"
    generations = directory / "grounded_generations.db"

    knowledge.write_bytes(
        generations.read_bytes()
    )

    value = metadata(
        directory
    )
    for item in value["databases"]:
        if item["boundary_identity"] == "KNOWLEDGE_SQLITE@1":
            item["size_bytes"] = knowledge.stat().st_size
    write_metadata(
        directory,
        value,
    )

    with pytest.raises(
        ValueError,
        match="missing required tables",
    ):
        validate_runtime_sqlite_restore_candidate(
            directory
        )


def test_validation_never_mutates_live_database_paths(
    tmp_path: Path,
) -> None:
    runtime_sources = initialized_sources(
        tmp_path
    )

    directory = RuntimeSQLiteBackupService(
        backup_root=tmp_path / "backups",
        sources=runtime_sources,
        clock=lambda: CREATED_AT,
    ).create_backup_set().directory

    # Snapshot live databases only after backup creation. This test owns the
    # validator contract, not SQLite/WAL/checkpoint side effects that may occur
    # while the backup service reads the live databases.
    live_before_validation = {
        path: path.read_bytes()
        for path in (
            runtime_sources.knowledge_database,
            runtime_sources.usage_cost_ledger_database,
            runtime_sources.grounded_generation_database,
        )
    }

    validate_runtime_sqlite_restore_candidate(
        directory
    )

    assert {
        path: path.read_bytes()
        for path in live_before_validation
    } == live_before_validation
