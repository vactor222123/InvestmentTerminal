"""All-or-nothing backup sets for runtime-managed SQLite persistence."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from investment_terminal.persistence.sqlite_backup import (
    SQLiteBackupResult,
    backup_sqlite_database,
)
from investment_terminal.persistence.sqlite_inventory import (
    GROUNDED_GENERATION_SQLITE,
    KNOWLEDGE_SQLITE,
    PROVIDER_USAGE_COST_SQLITE,
    SQLitePersistenceBoundary,
)
from investment_terminal.utils.atomic_write import (
    sync_directory,
    write_json_atomic,
)


BACKUP_SET_SCHEMA_VERSION = 1
BACKUP_SET_IDENTITY = "RUNTIME_SQLITE_BACKUP_SET@1"

_RUNTIME_BOUNDARIES: tuple[SQLitePersistenceBoundary, ...] = (
    KNOWLEDGE_SQLITE,
    PROVIDER_USAGE_COST_SQLITE,
    GROUNDED_GENERATION_SQLITE,
)

_BACKUP_FILENAMES = {
    KNOWLEDGE_SQLITE.identity: "knowledge.db",
    PROVIDER_USAGE_COST_SQLITE.identity: "provider_usage_cost.db",
    GROUNDED_GENERATION_SQLITE.identity: "grounded_generations.db",
}


@dataclass(frozen=True, slots=True)
class RuntimeSQLiteBackupSources:
    knowledge_database: Path
    usage_cost_ledger_database: Path
    grounded_generation_database: Path

    def path_for(
        self,
        boundary_identity: str,
    ) -> Path:
        if boundary_identity == KNOWLEDGE_SQLITE.identity:
            return self.knowledge_database
        if boundary_identity == PROVIDER_USAGE_COST_SQLITE.identity:
            return self.usage_cost_ledger_database
        if boundary_identity == GROUNDED_GENERATION_SQLITE.identity:
            return self.grounded_generation_database
        raise KeyError(
            f"unsupported runtime backup boundary: {boundary_identity}"
        )


@dataclass(frozen=True, slots=True)
class RuntimeSQLiteBackupSet:
    backup_set_id: str
    created_at: datetime
    directory: Path
    metadata_path: Path
    backups: tuple[SQLiteBackupResult, ...]


class RuntimeSQLiteBackupService:
    """Create one complete runtime SQLite backup set or publish nothing."""

    def __init__(
        self,
        *,
        backup_root: str | Path,
        sources: RuntimeSQLiteBackupSources,
        clock: Callable[[], datetime],
    ) -> None:
        self._backup_root = _normalize_directory_path(
            backup_root,
            field_name="backup_root",
        )
        if not isinstance(
            sources,
            RuntimeSQLiteBackupSources,
        ):
            raise TypeError(
                "sources must be a RuntimeSQLiteBackupSources"
            )
        if not callable(clock):
            raise TypeError(
                "clock must be callable"
            )

        self._sources = sources
        self._clock = clock

    def create_backup_set(self) -> RuntimeSQLiteBackupSet:
        created_at = _require_aware_datetime(
            self._clock()
        )
        backup_set_id = _backup_set_id(
            created_at
        )

        backup_root = self._backup_root.resolve(
            strict=False
        )
        backup_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        final_directory = (
            backup_root
            / backup_set_id
        )
        if final_directory.exists():
            raise FileExistsError(
                final_directory
            )

        staging_directory = (
            backup_root
            / f".{backup_set_id}.staging"
        )
        if staging_directory.exists():
            raise FileExistsError(
                staging_directory
            )

        staging_directory.mkdir()

        backup_results: list[SQLiteBackupResult] = []

        try:
            for boundary in _RUNTIME_BOUNDARIES:
                destination = (
                    staging_directory
                    / _BACKUP_FILENAMES[
                        boundary.identity
                    ]
                )
                backup_results.append(
                    backup_sqlite_database(
                        boundary_identity=boundary.identity,
                        source_path=self._sources.path_for(
                            boundary.identity
                        ),
                        destination_path=destination,
                    )
                )

            metadata_path = (
                staging_directory
                / "metadata.json"
            )
            write_json_atomic(
                metadata_path,
                _metadata_payload(
                    backup_set_id=backup_set_id,
                    created_at=created_at,
                    backup_results=tuple(
                        backup_results
                    ),
                ),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )

            os.replace(
                staging_directory,
                final_directory,
            )
            sync_directory(
                backup_root
            )
        except BaseException:
            _remove_staging_directory(
                staging_directory
            )
            raise

        final_results = tuple(
            SQLiteBackupResult(
                boundary_identity=result.boundary_identity,
                source_path=result.source_path,
                destination_path=(
                    final_directory
                    / result.destination_path.name
                ),
                size_bytes=result.size_bytes,
            )
            for result in backup_results
        )

        return RuntimeSQLiteBackupSet(
            backup_set_id=backup_set_id,
            created_at=created_at,
            directory=final_directory,
            metadata_path=(
                final_directory
                / "metadata.json"
            ),
            backups=final_results,
        )


def _metadata_payload(
    *,
    backup_set_id: str,
    created_at: datetime,
    backup_results: tuple[SQLiteBackupResult, ...],
) -> dict[str, object]:
    by_identity = {
        result.boundary_identity: result
        for result in backup_results
    }

    databases: list[dict[str, object]] = []

    for boundary in _RUNTIME_BOUNDARIES:
        result = by_identity[
            boundary.identity
        ]
        databases.append(
            {
                "boundary_identity": boundary.identity,
                "owner": boundary.owner,
                "authority_class": boundary.authority_class.value,
                "backup_requirement": boundary.backup_requirement.value,
                "source_path": str(
                    result.source_path
                ),
                "backup_file": result.destination_path.name,
                "size_bytes": result.size_bytes,
            }
        )

    return {
        "schema_version": BACKUP_SET_SCHEMA_VERSION,
        "identity": BACKUP_SET_IDENTITY,
        "backup_set_id": backup_set_id,
        "created_at": created_at.isoformat(),
        "databases": databases,
    }


def _backup_set_id(
    created_at: datetime,
) -> str:
    utc_value = created_at.astimezone(
        timezone.utc
    )
    return (
        "runtime-sqlite-"
        + utc_value.strftime(
            "%Y%m%dT%H%M%S.%fZ"
        )
    )


def _normalize_directory_path(
    path: str | Path,
    *,
    field_name: str,
) -> Path:
    if isinstance(path, Path):
        candidate = path
    elif isinstance(path, str):
        if not path.strip():
            raise ValueError(
                f"{field_name} must be a non-empty path"
            )
        candidate = Path(path)
    else:
        raise TypeError(
            f"{field_name} must be a string or Path"
        )

    if candidate.name == ":memory:":
        raise ValueError(
            f"{field_name} must identify a filesystem directory"
        )

    return candidate


def _require_aware_datetime(
    value: datetime,
) -> datetime:
    if not isinstance(
        value,
        datetime,
    ):
        raise TypeError(
            "clock must return datetime"
        )
    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(
            "clock must return a timezone-aware datetime"
        )
    return value


def _remove_staging_directory(
    path: Path,
) -> None:
    if not path.exists():
        return

    shutil.rmtree(
        path,
        ignore_errors=True,
    )
