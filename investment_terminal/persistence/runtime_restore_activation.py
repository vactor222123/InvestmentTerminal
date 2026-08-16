"""Offline activation of a validated runtime SQLite restore candidate."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from contextlib import suppress

from investment_terminal.persistence.runtime_restore_validation import (
    ValidatedRuntimeSQLiteRestoreCandidate,
    validate_runtime_sqlite_restore_candidate,
)
from investment_terminal.persistence.sqlite_backup import (
    backup_sqlite_database,
)
from investment_terminal.persistence.sqlite_inventory import (
    GROUNDED_GENERATION_SQLITE,
    KNOWLEDGE_SQLITE,
    PROVIDER_USAGE_COST_SQLITE,
)
from investment_terminal.utils.atomic_write import sync_directory


@dataclass(frozen=True, slots=True)
class RuntimeSQLiteRestoreTargets:
    knowledge_database: Path
    usage_cost_ledger_database: Path
    grounded_generation_database: Path

    def path_for(self, boundary_identity: str) -> Path:
        if boundary_identity == KNOWLEDGE_SQLITE.identity:
            return self.knowledge_database
        if boundary_identity == PROVIDER_USAGE_COST_SQLITE.identity:
            return self.usage_cost_ledger_database
        if boundary_identity == GROUNDED_GENERATION_SQLITE.identity:
            return self.grounded_generation_database
        raise KeyError(
            f"unsupported runtime restore boundary: {boundary_identity}"
        )


@dataclass(frozen=True, slots=True)
class RuntimeSQLiteRestoreResult:
    backup_set_id: str
    restored_paths: tuple[Path, ...]


def activate_runtime_sqlite_restore(
    *,
    backup_set_directory: str | Path,
    targets: RuntimeSQLiteRestoreTargets,
) -> RuntimeSQLiteRestoreResult:
    """
    Validate and activate one runtime backup set.

    This operation is designed for offline operator use. The caller must ensure
    that the production process is stopped before invocation.
    """
    if not isinstance(targets, RuntimeSQLiteRestoreTargets):
        raise TypeError("targets must be a RuntimeSQLiteRestoreTargets")

    candidate = validate_runtime_sqlite_restore_candidate(
        backup_set_directory
    )
    _validate_targets(candidate, targets)

    work_root = Path(
        tempfile.mkdtemp(prefix="investment-terminal-restore-")
    )
    rollback_dir = work_root / "rollback"
    staged_dir = work_root / "staged"
    rollback_dir.mkdir()
    staged_dir.mkdir()

    rollback_paths: dict[str, Path | None] = {}
    staged_paths: dict[str, Path] = {}
    replaced: list[str] = []

    try:
        for database in candidate.databases:
            target = targets.path_for(database.boundary_identity).resolve(
                strict=False
            )
            target.parent.mkdir(parents=True, exist_ok=True)

            rollback = None
            if target.exists():
                rollback = rollback_dir / target.name
                backup_sqlite_database(
                    boundary_identity=database.boundary_identity,
                    source_path=target,
                    destination_path=rollback,
                )
            rollback_paths[database.boundary_identity] = rollback

            staged = staged_dir / target.name
            backup_sqlite_database(
                boundary_identity=database.boundary_identity,
                source_path=database.backup_path,
                destination_path=staged,
            )
            staged_paths[database.boundary_identity] = staged

        for database in candidate.databases:
            identity = database.boundary_identity
            target = targets.path_for(identity).resolve(strict=False)

            if target.exists():
                _prepare_live_database_for_offline_replace(
                    target
                )
            _remove_sqlite_sidecars(target)
            os.replace(
                staged_paths[identity],
                target,
            )
            sync_directory(target.parent)
            replaced.append(identity)

    except BaseException:
        _rollback_replaced_databases(
            replaced=replaced,
            rollback_paths=rollback_paths,
            targets=targets,
        )
        raise
    finally:
        shutil.rmtree(work_root, ignore_errors=True)

    return RuntimeSQLiteRestoreResult(
        backup_set_id=candidate.backup_set_id,
        restored_paths=tuple(
            targets.path_for(database.boundary_identity).resolve()
            for database in candidate.databases
        ),
    )


def _validate_targets(
    candidate: ValidatedRuntimeSQLiteRestoreCandidate,
    targets: RuntimeSQLiteRestoreTargets,
) -> None:
    resolved: list[Path] = []
    for database in candidate.databases:
        target = targets.path_for(database.boundary_identity)
        if target.name == ":memory:":
            raise ValueError("restore targets must be file-backed")
        if target.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
            raise ValueError(
                "restore targets must use .db, .sqlite, or .sqlite3"
            )

        target_resolved = target.resolve(strict=False)
        if target_resolved == database.backup_path.resolve():
            raise ValueError(
                "restore target must differ from backup artifact"
            )
        resolved.append(target_resolved)

    if len(set(resolved)) != len(resolved):
        raise ValueError("runtime restore targets must be distinct")


def _prepare_live_database_for_offline_replace(
    database: Path,
) -> None:
    """
    Drain committed WAL state and release SQLite-owned sidecar handles.

    Restore activation is an offline-only workflow. A target that cannot be
    checkpointed and moved out of WAL mode is treated as still in use and the
    restore fails closed before replacing that database.
    """
    connection: sqlite3.Connection | None = None

    try:
        connection = sqlite3.connect(
            database
        )
        checkpoint = connection.execute(
            "PRAGMA wal_checkpoint(TRUNCATE)"
        ).fetchone()
        if (
            checkpoint is not None
            and len(checkpoint) >= 1
            and int(checkpoint[0]) != 0
        ):
            raise RuntimeError(
                f"live SQLite database is still busy: {database}"
            )

        journal_mode_row = connection.execute(
            "PRAGMA journal_mode = DELETE"
        ).fetchone()
        journal_mode = (
            str(journal_mode_row[0]).lower()
            if journal_mode_row is not None
            else ""
        )
        if journal_mode != "delete":
            raise RuntimeError(
                f"could not leave WAL mode for offline restore target: {database}"
            )
    finally:
        if connection is not None:
            connection.close()


def _remove_sqlite_sidecars(database: Path) -> None:
    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{database}{suffix}")
        if not sidecar.exists():
            continue
        sidecar.unlink()


def _rollback_replaced_databases(
    *,
    replaced: list[str],
    rollback_paths: dict[str, Path | None],
    targets: RuntimeSQLiteRestoreTargets,
) -> None:
    rollback_errors: list[BaseException] = []

    for identity in reversed(replaced):
        target = targets.path_for(identity).resolve(strict=False)
        rollback = rollback_paths[identity]
        try:
            if target.exists():
                _prepare_live_database_for_offline_replace(
                    target
                )
            _remove_sqlite_sidecars(target)
            if rollback is None:
                with suppress(FileNotFoundError):
                    target.unlink()
            else:
                os.replace(rollback, target)
                sync_directory(target.parent)
        except BaseException as exc:
            rollback_errors.append(exc)

    if rollback_errors:
        raise RuntimeError(
            "restore failed and rollback was incomplete"
        ) from rollback_errors[0]
