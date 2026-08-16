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
from investment_terminal.knowledge.sqlite_store import KnowledgeSQLiteStore
from investment_terminal.persistence.runtime_backup_service import (
    RuntimeSQLiteBackupService,
    RuntimeSQLiteBackupSources,
)
from investment_terminal.persistence.runtime_restore_activation import (
    RuntimeSQLiteRestoreTargets,
    activate_runtime_sqlite_restore,
)


NOW = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)


def initialized(path: Path, kind: str) -> None:
    if kind == "knowledge":
        KnowledgeSQLiteStore(path).initialize()
    elif kind == "ledger":
        GroundedProviderUsageCostLedgerSQLiteStore(path).initialize()
    else:
        GroundedGenerationSQLiteStore(path).initialize()


def make_sources(root: Path) -> RuntimeSQLiteBackupSources:
    paths = {
        "knowledge": root / "knowledge.db",
        "ledger": root / "provider_usage_cost.db",
        "generation": root / "grounded_generations.db",
    }
    for kind, path in paths.items():
        initialized(path, kind)
    return RuntimeSQLiteBackupSources(
        knowledge_database=paths["knowledge"],
        usage_cost_ledger_database=paths["ledger"],
        grounded_generation_database=paths["generation"],
    )


def targets(root: Path) -> RuntimeSQLiteRestoreTargets:
    return RuntimeSQLiteRestoreTargets(
        knowledge_database=root / "knowledge.db",
        usage_cost_ledger_database=root / "provider_usage_cost.db",
        grounded_generation_database=root / "grounded_generations.db",
    )


def test_restore_activates_validated_backup_set(tmp_path: Path) -> None:
    source = make_sources(tmp_path / "source")
    backup = RuntimeSQLiteBackupService(
        backup_root=tmp_path / "backups",
        sources=source,
        clock=lambda: NOW,
    ).create_backup_set()

    live = make_sources(tmp_path / "live")

    result = activate_runtime_sqlite_restore(
        backup_set_directory=backup.directory,
        targets=targets(tmp_path / "live"),
    )

    assert result.backup_set_id == backup.backup_set_id
    assert len(result.restored_paths) == 3


def test_restore_rejects_same_backup_and_target_file(tmp_path: Path) -> None:
    source = make_sources(tmp_path / "source")
    backup = RuntimeSQLiteBackupService(
        backup_root=tmp_path / "backups",
        sources=source,
        clock=lambda: NOW,
    ).create_backup_set()

    with pytest.raises(ValueError, match="differ"):
        activate_runtime_sqlite_restore(
            backup_set_directory=backup.directory,
            targets=RuntimeSQLiteRestoreTargets(
                knowledge_database=backup.directory / "knowledge.db",
                usage_cost_ledger_database=tmp_path / "x.db",
                grounded_generation_database=tmp_path / "y.db",
            ),
        )


def test_partial_activation_failure_rolls_back_previous_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = make_sources(tmp_path / "source")
    backup = RuntimeSQLiteBackupService(
        backup_root=tmp_path / "backups",
        sources=source,
        clock=lambda: NOW,
    ).create_backup_set()

    live_root = tmp_path / "live"
    live = make_sources(live_root)
    before = {
        path: path.read_bytes()
        for path in (
            live.knowledge_database,
            live.usage_cost_ledger_database,
            live.grounded_generation_database,
        )
    }

    import investment_terminal.persistence.runtime_restore_activation as module

    real_replace = module.os.replace
    calls = 0

    def fail_second(source_path, destination_path):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise PermissionError("simulated locked target")
        return real_replace(source_path, destination_path)

    monkeypatch.setattr(module.os, "replace", fail_second)

    with pytest.raises(PermissionError, match="locked target"):
        activate_runtime_sqlite_restore(
            backup_set_directory=backup.directory,
            targets=targets(live_root),
        )

    assert live.knowledge_database.exists()
    assert live.usage_cost_ledger_database.exists()
    assert live.grounded_generation_database.exists()


def test_restore_fails_closed_when_live_database_is_still_busy(
    tmp_path: Path,
) -> None:
    source = make_sources(tmp_path / "source")
    backup = RuntimeSQLiteBackupService(
        backup_root=tmp_path / "backups",
        sources=source,
        clock=lambda: NOW,
    ).create_backup_set()

    live_root = tmp_path / "live"
    live = make_sources(live_root)

    blocker = sqlite3.connect(
        live.knowledge_database
    )
    try:
        blocker.execute(
            "BEGIN IMMEDIATE"
        )

        with pytest.raises(
            (
                sqlite3.OperationalError,
                RuntimeError,
            )
        ):
            activate_runtime_sqlite_restore(
                backup_set_directory=backup.directory,
                targets=targets(live_root),
            )
    finally:
        blocker.rollback()
        blocker.close()
