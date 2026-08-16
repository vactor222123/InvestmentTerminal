"""Fail-closed validation of runtime SQLite backup sets before restore."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

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
    BACKUP_SET_IDENTITY,
    BACKUP_SET_SCHEMA_VERSION,
)
from investment_terminal.persistence.sqlite_inventory import (
    GROUNDED_GENERATION_SQLITE,
    KNOWLEDGE_SQLITE,
    PROVIDER_USAGE_COST_SQLITE,
    SQLitePersistenceBoundary,
)


@dataclass(frozen=True, slots=True)
class ValidatedRuntimeSQLiteRestoreDatabase:
    boundary_identity: str
    backup_path: Path
    schema_version: int
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ValidatedRuntimeSQLiteRestoreCandidate:
    backup_set_id: str
    created_at: datetime
    directory: Path
    databases: tuple[ValidatedRuntimeSQLiteRestoreDatabase, ...]


@dataclass(frozen=True, slots=True)
class _ExpectedRuntimeDatabase:
    boundary: SQLitePersistenceBoundary
    filename: str
    metadata_table: str
    schema_version: int
    required_tables: frozenset[str]


_EXPECTED_DATABASES: tuple[_ExpectedRuntimeDatabase, ...] = (
    _ExpectedRuntimeDatabase(
        boundary=KNOWLEDGE_SQLITE,
        filename="knowledge.db",
        metadata_table="knowledge_schema_metadata",
        schema_version=KnowledgeSQLiteStore.SCHEMA_VERSION,
        required_tables=frozenset(
            {
                "knowledge_schema_metadata",
                "knowledge_records",
                "knowledge_evidence",
            }
        ),
    ),
    _ExpectedRuntimeDatabase(
        boundary=PROVIDER_USAGE_COST_SQLITE,
        filename="provider_usage_cost.db",
        metadata_table="provider_usage_cost_schema_metadata",
        schema_version=GroundedProviderUsageCostLedgerSQLiteStore.SCHEMA_VERSION,
        required_tables=frozenset(
            {
                "provider_usage_cost_schema_metadata",
                "provider_usage_cost_ledger",
            }
        ),
    ),
    _ExpectedRuntimeDatabase(
        boundary=GROUNDED_GENERATION_SQLITE,
        filename="grounded_generations.db",
        metadata_table="grounded_generation_schema_metadata",
        schema_version=GroundedGenerationSQLiteStore.SCHEMA_VERSION,
        required_tables=frozenset(
            {
                "grounded_generation_schema_metadata",
                "grounded_generations",
            }
        ),
    ),
)


def validate_runtime_sqlite_restore_candidate(
    backup_set_directory: str | Path,
) -> ValidatedRuntimeSQLiteRestoreCandidate:
    directory = _normalize_directory(
        backup_set_directory
    )

    metadata_path = (
        directory
        / "metadata.json"
    )
    metadata = _read_metadata(
        metadata_path
    )

    backup_set_id = _required_string(
        metadata,
        "backup_set_id",
    )
    if backup_set_id != directory.name:
        raise ValueError(
            "backup_set_id must match backup set directory name"
        )

    if metadata.get("schema_version") != BACKUP_SET_SCHEMA_VERSION:
        raise ValueError(
            "unsupported backup set schema_version"
        )
    if metadata.get("identity") != BACKUP_SET_IDENTITY:
        raise ValueError(
            "unexpected backup set identity"
        )

    created_at = _parse_aware_datetime(
        _required_string(
            metadata,
            "created_at",
        )
    )

    raw_databases = metadata.get(
        "databases"
    )
    if not isinstance(
        raw_databases,
        list,
    ):
        raise ValueError(
            "databases must be a list"
        )
    if len(raw_databases) != len(
        _EXPECTED_DATABASES
    ):
        raise ValueError(
            "backup set must contain exactly three runtime databases"
        )

    expected_by_identity = {
        expected.boundary.identity: expected
        for expected in _EXPECTED_DATABASES
    }

    seen: set[str] = set()
    validated: list[ValidatedRuntimeSQLiteRestoreDatabase] = []

    for item in raw_databases:
        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                "each databases entry must be an object"
            )

        boundary_identity = _required_string(
            item,
            "boundary_identity",
        )
        if boundary_identity in seen:
            raise ValueError(
                f"duplicate boundary_identity: {boundary_identity}"
            )
        seen.add(
            boundary_identity
        )

        try:
            expected = expected_by_identity[
                boundary_identity
            ]
        except KeyError as exc:
            raise ValueError(
                f"unexpected runtime backup boundary: {boundary_identity}"
            ) from exc

        _validate_inventory_metadata(
            item=item,
            expected=expected,
        )

        backup_file = _required_string(
            item,
            "backup_file",
        )
        if (
            Path(backup_file).name != backup_file
            or backup_file != expected.filename
        ):
            raise ValueError(
                f"unexpected backup_file for {boundary_identity}"
            )

        backup_path = (
            directory
            / backup_file
        )
        if not backup_path.exists():
            raise FileNotFoundError(
                backup_path
            )
        if not backup_path.is_file():
            raise ValueError(
                f"backup artifact must be a file: {backup_file}"
            )

        expected_size = item.get(
            "size_bytes"
        )
        if (
            not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or expected_size < 0
        ):
            raise ValueError(
                f"invalid size_bytes for {boundary_identity}"
            )
        actual_size = backup_path.stat().st_size
        if actual_size != expected_size:
            raise ValueError(
                f"size_bytes mismatch for {boundary_identity}"
            )

        _validate_sqlite_database(
            path=backup_path,
            expected=expected,
        )

        validated.append(
            ValidatedRuntimeSQLiteRestoreDatabase(
                boundary_identity=boundary_identity,
                backup_path=backup_path.resolve(),
                schema_version=expected.schema_version,
                size_bytes=actual_size,
            )
        )

    if seen != set(
        expected_by_identity
    ):
        raise ValueError(
            "backup set runtime boundary membership is incomplete"
        )

    _reject_extra_artifacts(
        directory
    )

    ordered = tuple(
        next(
            item
            for item in validated
            if item.boundary_identity
            == expected.boundary.identity
        )
        for expected in _EXPECTED_DATABASES
    )

    return ValidatedRuntimeSQLiteRestoreCandidate(
        backup_set_id=backup_set_id,
        created_at=created_at,
        directory=directory,
        databases=ordered,
    )


def _normalize_directory(
    value: str | Path,
) -> Path:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str):
        if not value.strip():
            raise ValueError(
                "backup_set_directory must be a non-empty path"
            )
        candidate = Path(
            value
        )
    else:
        raise TypeError(
            "backup_set_directory must be a string or Path"
        )

    candidate = candidate.resolve()
    if not candidate.exists():
        raise FileNotFoundError(
            candidate
        )
    if not candidate.is_dir():
        raise ValueError(
            "backup_set_directory must identify a directory"
        )
    return candidate


def _read_metadata(
    path: Path,
) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            path
        )
    if not path.is_file():
        raise ValueError(
            "metadata.json must be a file"
        )

    try:
        parsed = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError(
            "metadata.json must contain valid UTF-8 JSON"
        ) from exc

    if not isinstance(
        parsed,
        dict,
    ):
        raise ValueError(
            "metadata.json root must be an object"
        )
    return parsed


def _required_string(
    mapping: dict[str, Any],
    name: str,
) -> str:
    value = mapping.get(
        name
    )
    if not isinstance(
        value,
        str,
    ) or not value:
        raise ValueError(
            f"{name} must be a non-empty string"
        )
    return value


def _parse_aware_datetime(
    value: str,
) -> datetime:
    try:
        parsed = datetime.fromisoformat(
            value
        )
    except ValueError as exc:
        raise ValueError(
            "created_at must be an ISO 8601 datetime"
        ) from exc

    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
    ):
        raise ValueError(
            "created_at must be timezone-aware"
        )
    return parsed


def _validate_inventory_metadata(
    *,
    item: dict[str, Any],
    expected: _ExpectedRuntimeDatabase,
) -> None:
    boundary = expected.boundary

    if item.get("owner") != boundary.owner:
        raise ValueError(
            f"owner mismatch for {boundary.identity}"
        )
    if (
        item.get("authority_class")
        != boundary.authority_class.value
    ):
        raise ValueError(
            f"authority_class mismatch for {boundary.identity}"
        )
    if (
        item.get("backup_requirement")
        != boundary.backup_requirement.value
    ):
        raise ValueError(
            f"backup_requirement mismatch for {boundary.identity}"
        )

    _required_string(
        item,
        "source_path",
    )


def _validate_sqlite_database(
    *,
    path: Path,
    expected: _ExpectedRuntimeDatabase,
) -> None:
    connection: sqlite3.Connection | None = None

    try:
        connection = sqlite3.connect(
            path.resolve().as_uri()
            + "?mode=ro&immutable=1",
            uri=True,
        )

        quick_check = tuple(
            str(row[0])
            for row in connection.execute(
                "PRAGMA quick_check"
            ).fetchall()
        )
        if quick_check != (
            "ok",
        ):
            raise sqlite3.DatabaseError(
                "SQLite restore candidate failed PRAGMA quick_check"
            )

        table_names = frozenset(
            str(row[0])
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        )
        if not expected.required_tables.issubset(
            table_names
        ):
            missing = sorted(
                expected.required_tables
                - table_names
            )
            raise ValueError(
                f"missing required tables for "
                f"{expected.boundary.identity}: {missing}"
            )

        try:
            row = connection.execute(
                f"""
                SELECT value
                FROM {expected.metadata_table}
                WHERE key = 'schema_version'
                """
            ).fetchone()
        except sqlite3.OperationalError as exc:
            raise ValueError(
                f"missing schema metadata for "
                f"{expected.boundary.identity}"
            ) from exc

        if row is None:
            raise ValueError(
                f"missing schema_version for "
                f"{expected.boundary.identity}"
            )

        try:
            schema_version = int(
                row[0]
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                f"invalid schema_version for "
                f"{expected.boundary.identity}"
            ) from exc

        if schema_version != expected.schema_version:
            raise ValueError(
                f"incompatible schema_version for "
                f"{expected.boundary.identity}: "
                f"{schema_version} != {expected.schema_version}"
            )
    except sqlite3.DatabaseError:
        raise
    finally:
        if connection is not None:
            connection.close()


def _reject_extra_artifacts(
    directory: Path,
) -> None:
    expected_names = {
        "metadata.json",
        *(
            expected.filename
            for expected in _EXPECTED_DATABASES
        ),
    }
    actual_names = {
        path.name
        for path in directory.iterdir()
        if not _is_sqlite_sidecar_artifact(
            path.name
        )
    }
    extra = sorted(
        actual_names
        - expected_names
    )
    if extra:
        raise ValueError(
            f"unexpected backup set artifacts: {extra}"
        )


def _is_sqlite_sidecar_artifact(
    name: str,
) -> bool:
    """Recognize SQLite-managed WAL/SHM sidecars without accepting arbitrary files."""
    if name.endswith(
        (
            "-wal",
            "-shm",
        )
    ):
        base_name = name[:-4]
        if base_name in {
            expected.filename
            for expected in _EXPECTED_DATABASES
        }:
            return True

        return (
            base_name.startswith(".")
            and ".tmp.db" in base_name
            and any(
                base_name.startswith(
                    f".{expected.filename}."
                )
                for expected in _EXPECTED_DATABASES
            )
        )

    return False
