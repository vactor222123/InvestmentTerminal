"""Consistent, validated and atomically published SQLite backups."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from contextlib import suppress

from investment_terminal.persistence.sqlite_inventory import (
    SQLitePersistenceBoundary,
    require_sqlite_persistence_boundary,
)
from investment_terminal.utils.atomic_write import (
    sync_directory,
)


_SQLITE_SUFFIXES = frozenset(
    {
        ".db",
        ".sqlite",
        ".sqlite3",
    }
)


@dataclass(frozen=True, slots=True)
class SQLiteBackupResult:
    """Result of one successfully published SQLite backup."""

    boundary_identity: str
    source_path: Path
    destination_path: Path
    size_bytes: int


def backup_sqlite_database(
    *,
    boundary_identity: str,
    source_path: str | Path,
    destination_path: str | Path,
    overwrite: bool = False,
) -> SQLiteBackupResult:
    """
    Create one consistent file-backed SQLite backup.

    Policy identity is validated against the repository-owned persistence
    inventory. The live database is copied through SQLite's backup API rather
    than by copying the database file, so committed WAL content is included in
    the resulting consistent snapshot.
    """
    boundary = require_sqlite_persistence_boundary(
        boundary_identity
    )
    source = _normalize_sqlite_file_path(
        source_path,
        field_name="source_path",
    )
    destination = _normalize_sqlite_file_path(
        destination_path,
        field_name="destination_path",
    )

    if not isinstance(
        overwrite,
        bool,
    ):
        raise TypeError(
            "overwrite must be a bool"
        )

    source = source.resolve()
    destination = destination.resolve(
        strict=False
    )

    if source == destination:
        raise ValueError(
            "source_path and destination_path must identify different files"
        )

    if not source.exists():
        raise FileNotFoundError(
            source
        )
    if not source.is_file():
        raise ValueError(
            "source_path must identify an existing file-backed SQLite database"
        )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    if destination.exists():
        if not destination.is_file():
            raise ValueError(
                "destination_path must identify a file"
            )
        if not overwrite:
            raise FileExistsError(
                destination
            )

    temporary_path = _new_temporary_database_path(
        destination
    )

    try:
        _backup_to_temporary_database(
            source=source,
            temporary=temporary_path,
        )
        _validate_backup(
            temporary_path
        )
        _sync_file(
            temporary_path
        )

        # Re-check immediately before publication to protect the ordinary
        # no-overwrite contract. Callers needing replacement must opt in.
        if destination.exists() and not overwrite:
            raise FileExistsError(
                destination
            )

        os.replace(
            temporary_path,
            destination,
        )
        temporary_path = None
        sync_directory(
            destination.parent
        )
    except BaseException:
        _remove_temporary_file(
            temporary_path
        )
        raise

    return SQLiteBackupResult(
        boundary_identity=boundary.identity,
        source_path=source,
        destination_path=destination,
        size_bytes=destination.stat().st_size,
    )


def _normalize_sqlite_file_path(
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
            f"{field_name} must be file-backed; :memory: is not supported"
        )
    if (
        not candidate.name
        or candidate.suffix.lower()
        not in _SQLITE_SUFFIXES
    ):
        raise ValueError(
            f"{field_name} must use .db, .sqlite, or .sqlite3"
        )

    return candidate


def _new_temporary_database_path(
    destination: Path,
) -> Path:
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp.db",
    )
    os.close(
        file_descriptor
    )
    return Path(
        temporary_name
    )


def _backup_to_temporary_database(
    *,
    source: Path,
    temporary: Path,
) -> None:
    source_connection: sqlite3.Connection | None = None
    destination_connection: sqlite3.Connection | None = None

    try:
        source_connection = sqlite3.connect(
            _read_only_sqlite_uri(
                source
            ),
            uri=True,
        )
        destination_connection = sqlite3.connect(
            temporary
        )
        source_connection.backup(
            destination_connection
        )
        destination_connection.commit()
    finally:
        # Close both handles before validation/publication. This ordering is
        # required for reliable os.replace behavior on Windows.
        if destination_connection is not None:
            destination_connection.close()
        if source_connection is not None:
            source_connection.close()


def _validate_backup(
    path: Path,
) -> None:
    connection: sqlite3.Connection | None = None

    try:
        connection = sqlite3.connect(
            _read_only_sqlite_uri(
                path
            ),
            uri=True,
        )
        rows = connection.execute(
            "PRAGMA quick_check"
        ).fetchall()
    finally:
        if connection is not None:
            connection.close()

    results = tuple(
        str(row[0])
        for row in rows
    )
    if results != (
        "ok",
    ):
        raise sqlite3.DatabaseError(
            "SQLite backup failed PRAGMA quick_check: "
            + "; ".join(results)
        )


def _read_only_sqlite_uri(
    path: Path,
) -> str:
    return (
        path.resolve().as_uri()
        + "?mode=ro"
    )


def _sync_file(
    path: Path,
) -> None:
    # Windows' CRT _commit(), which backs os.fsync(), requires a descriptor
    # opened with write access. The backup is already complete and all SQLite
    # handles are closed at this point; r+b grants the required descriptor
    # access without modifying file contents.
    with path.open(
        "r+b",
    ) as backup_file:
        os.fsync(
            backup_file.fileno()
        )


def _remove_temporary_file(
    temporary_path: Path | None,
) -> None:
    if temporary_path is None:
        return

    with suppress(
        OSError,
    ):
        temporary_path.unlink()
