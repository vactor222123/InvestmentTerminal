import os
import sqlite3
from pathlib import Path

import pytest

from investment_terminal.persistence.sqlite_backup import (
    backup_sqlite_database,
)


BOUNDARY = "PROVIDER_USAGE_COST_SQLITE@1"


def create_wal_database(
    path: Path,
) -> sqlite3.Connection:
    connection = sqlite3.connect(
        path
    )
    connection.execute(
        "PRAGMA journal_mode = WAL"
    )
    connection.execute(
        "PRAGMA wal_autocheckpoint = 0"
    )
    connection.execute(
        """
        CREATE TABLE records (
            id INTEGER PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def read_values(
    path: Path,
) -> list[str]:
    with sqlite3.connect(
        path
    ) as connection:
        return [
            row[0]
            for row in connection.execute(
                "SELECT value FROM records ORDER BY id"
            ).fetchall()
        ]


def test_backup_captures_committed_wal_content(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.db"
    destination = tmp_path / "backup.db"

    writer = create_wal_database(
        source
    )
    try:
        writer.execute(
            "INSERT INTO records (value) VALUES (?)",
            ("first",),
        )
        writer.commit()
        writer.execute(
            "INSERT INTO records (value) VALUES (?)",
            ("second",),
        )
        writer.commit()

        wal = Path(
            f"{source}-wal"
        )
        assert wal.exists()
        assert wal.stat().st_size > 0

        result = backup_sqlite_database(
            boundary_identity=BOUNDARY,
            source_path=source,
            destination_path=destination,
        )
    finally:
        writer.close()

    assert result.destination_path == destination.resolve()
    assert result.boundary_identity == BOUNDARY
    assert result.size_bytes > 0
    assert read_values(
        destination
    ) == [
        "first",
        "second",
    ]


def test_backup_is_independent_of_live_wal_sidecars(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.db"
    destination = tmp_path / "backup.db"

    writer = create_wal_database(
        source
    )
    try:
        writer.execute(
            "INSERT INTO records (value) VALUES ('durable')"
        )
        writer.commit()

        backup_sqlite_database(
            boundary_identity=BOUNDARY,
            source_path=source,
            destination_path=destination,
        )
    finally:
        writer.close()

    assert not Path(
        f"{destination}-wal"
    ).exists()
    assert not Path(
        f"{destination}-shm"
    ).exists()
    assert read_values(
        destination
    ) == [
        "durable",
    ]


def test_existing_destination_requires_explicit_overwrite(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.db"
    destination = tmp_path / "backup.db"

    writer = create_wal_database(
        source
    )
    writer.close()
    destination.write_bytes(
        b"existing"
    )

    with pytest.raises(
        FileExistsError,
    ):
        backup_sqlite_database(
            boundary_identity=BOUNDARY,
            source_path=source,
            destination_path=destination,
        )

    assert destination.read_bytes() == b"existing"


def test_explicit_overwrite_atomically_replaces_destination(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.db"
    destination = tmp_path / "backup.db"

    writer = create_wal_database(
        source
    )
    writer.execute(
        "INSERT INTO records (value) VALUES ('replacement')"
    )
    writer.commit()
    writer.close()

    destination.write_bytes(
        b"old"
    )

    backup_sqlite_database(
        boundary_identity=BOUNDARY,
        source_path=source,
        destination_path=destination,
        overwrite=True,
    )

    assert read_values(
        destination
    ) == [
        "replacement",
    ]


def test_validation_failure_removes_temporary_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.db"
    destination = tmp_path / "backup.db"

    writer = create_wal_database(
        source
    )
    writer.close()

    def fail_validation(
        path: Path,
    ) -> None:
        raise sqlite3.DatabaseError(
            "validation failed"
        )

    monkeypatch.setattr(
        "investment_terminal.persistence.sqlite_backup._validate_backup",
        fail_validation,
    )

    with pytest.raises(
        sqlite3.DatabaseError,
        match="validation failed",
    ):
        backup_sqlite_database(
            boundary_identity=BOUNDARY,
            source_path=source,
            destination_path=destination,
        )

    assert not destination.exists()
    assert list(
        tmp_path.glob(
            ".backup.db.*.tmp.db"
        )
    ) == []


def test_replace_failure_preserves_existing_destination_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.db"
    destination = tmp_path / "backup.db"

    writer = create_wal_database(
        source
    )
    writer.close()
    destination.write_bytes(
        b"old"
    )

    def fail_replace(
        source_path: object,
        destination_path: object,
    ) -> None:
        raise PermissionError(
            "destination locked"
        )

    monkeypatch.setattr(
        "investment_terminal.persistence.sqlite_backup.os.replace",
        fail_replace,
    )

    with pytest.raises(
        PermissionError,
        match="destination locked",
    ):
        backup_sqlite_database(
            boundary_identity=BOUNDARY,
            source_path=source,
            destination_path=destination,
            overwrite=True,
        )

    assert destination.read_bytes() == b"old"
    assert list(
        tmp_path.glob(
            ".backup.db.*.tmp.db"
        )
    ) == []


def test_sqlite_connections_are_closed_before_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.db"
    destination = tmp_path / "backup.db"

    writer = create_wal_database(
        source
    )
    writer.close()

    real_connect = sqlite3.connect
    created: list["TrackedConnection"] = []

    class TrackedConnection(sqlite3.Connection):
        closed_for_test = False

        def close(self) -> None:
            self.closed_for_test = True
            super().close()

    def tracked_connect(
        *args: object,
        **kwargs: object,
    ) -> sqlite3.Connection:
        kwargs["factory"] = TrackedConnection
        connection = real_connect(
            *args,
            **kwargs,
        )
        created.append(
            connection
        )
        return connection

    real_replace = os.replace

    def assert_closed_then_replace(
        source_path: object,
        destination_path: object,
    ) -> None:
        assert created
        assert all(
            connection.closed_for_test
            for connection in created
        )
        real_replace(
            source_path,
            destination_path,
        )

    monkeypatch.setattr(
        "investment_terminal.persistence.sqlite_backup.sqlite3.connect",
        tracked_connect,
    )
    monkeypatch.setattr(
        "investment_terminal.persistence.sqlite_backup.os.replace",
        assert_closed_then_replace,
    )

    backup_sqlite_database(
        boundary_identity=BOUNDARY,
        source_path=source,
        destination_path=destination,
    )


def test_unknown_inventory_identity_fails_closed(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        KeyError,
    ):
        backup_sqlite_database(
            boundary_identity="UNKNOWN@1",
            source_path=tmp_path / "source.db",
            destination_path=tmp_path / "backup.db",
        )


@pytest.mark.parametrize(
    "field",
    [
        "source",
        "destination",
    ],
)
def test_memory_database_is_rejected(
    tmp_path: Path,
    field: str,
) -> None:
    source: str | Path = tmp_path / "source.db"
    destination: str | Path = tmp_path / "backup.db"

    if field == "source":
        source = ":memory:"
    else:
        writer = create_wal_database(
            Path(source)
        )
        writer.close()
        destination = ":memory:"

    with pytest.raises(
        ValueError,
        match="file-backed",
    ):
        backup_sqlite_database(
            boundary_identity=BOUNDARY,
            source_path=source,
            destination_path=destination,
        )


def test_source_and_destination_must_differ(
    tmp_path: Path,
) -> None:
    source = tmp_path / "same.db"
    writer = create_wal_database(
        source
    )
    writer.close()

    with pytest.raises(
        ValueError,
        match="different files",
    ):
        backup_sqlite_database(
            boundary_identity=BOUNDARY,
            source_path=source,
            destination_path=source,
        )


def test_non_sqlite_source_fails_and_does_not_publish(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.db"
    destination = tmp_path / "backup.db"
    source.write_bytes(
        b"not-sqlite"
    )

    with pytest.raises(
        sqlite3.DatabaseError,
    ):
        backup_sqlite_database(
            boundary_identity=BOUNDARY,
            source_path=source,
            destination_path=destination,
        )

    assert not destination.exists()
    assert list(
        tmp_path.glob(
            ".backup.db.*.tmp.db"
        )
    ) == []


def test_backup_file_sync_uses_windows_compatible_writable_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "backup.db"
    path.write_bytes(
        b"sqlite-backup"
    )
    observed_access: list[bool] = []
    real_fsync = os.fsync

    def assert_writable_descriptor(
        file_descriptor: int,
    ) -> None:
        # os.write(fd, b"") performs no content mutation, but Windows rejects
        # it for a read-only descriptor. This makes the regression test
        # platform-independent while exercising the access-mode contract.
        os.write(
            file_descriptor,
            b"",
        )
        observed_access.append(
            True
        )
        real_fsync(
            file_descriptor
        )

    monkeypatch.setattr(
        "investment_terminal.persistence.sqlite_backup.os.fsync",
        assert_writable_descriptor,
    )

    from investment_terminal.persistence.sqlite_backup import _sync_file

    before = path.read_bytes()
    _sync_file(
        path
    )

    assert observed_access == [
        True,
    ]
    assert path.read_bytes() == before
