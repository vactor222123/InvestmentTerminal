"""
Repository for HistoricalSnapshot metadata in SQLite.
"""

import sqlite3
from datetime import datetime
from typing import Iterable

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


class HistoricalSnapshotRepository:
    """
    Persist and query immutable snapshot metadata in structured history.

    The repository does not read or rewrite archived JSON evidence. It stores
    only the normalized metadata needed for search, timelines, and imports.
    """

    def __init__(
        self,
        store: HistoricalSQLiteStore,
    ) -> None:
        if not isinstance(
            store,
            HistoricalSQLiteStore,
        ):
            raise TypeError(
                "store must be a HistoricalSQLiteStore"
            )

        self.store = store

    def add(
        self,
        snapshot: HistoricalSnapshot,
    ) -> HistoricalSnapshot:
        """Insert one snapshot and reject duplicate identity or path."""
        if not isinstance(
            snapshot,
            HistoricalSnapshot,
        ):
            raise TypeError(
                "snapshot must be a HistoricalSnapshot"
            )

        self.store.initialize()

        try:
            with self.store.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO snapshots (
                        snapshot_id,
                        package_id,
                        package_schema_version,
                        product_version,
                        generated_at,
                        archived_at,
                        relative_path,
                        checksum_sha256,
                        supersedes,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._snapshot_values(
                        snapshot
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Historical snapshot could not be inserted: "
                "snapshot_id, relative_path, or supersedes is invalid"
            ) from exc

        return snapshot

    def add_many(
        self,
        snapshots: Iterable[HistoricalSnapshot],
    ) -> tuple[HistoricalSnapshot, ...]:
        """
        Insert multiple snapshots atomically.

        If any record fails, no snapshot from this batch is committed.
        """
        normalized = tuple(
            snapshots
        )

        if any(
            not isinstance(
                snapshot,
                HistoricalSnapshot,
            )
            for snapshot in normalized
        ):
            raise TypeError(
                "snapshots must contain only HistoricalSnapshot values"
            )

        self.store.initialize()

        try:
            with self.store.connect() as connection:
                connection.executemany(
                    """
                    INSERT INTO snapshots (
                        snapshot_id,
                        package_id,
                        package_schema_version,
                        product_version,
                        generated_at,
                        archived_at,
                        relative_path,
                        checksum_sha256,
                        supersedes,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(
                        self._snapshot_values(
                            snapshot
                        )
                        for snapshot in normalized
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Historical snapshot batch could not be inserted"
            ) from exc

        return normalized

    def get(
        self,
        snapshot_id: str,
    ) -> HistoricalSnapshot | None:
        """Return one snapshot, or None when it is not present."""
        normalized = HistoricalSnapshot._normalize_uuid(
            snapshot_id,
            field_name="snapshot_id",
        )

        self.store.initialize()

        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM snapshots
                WHERE snapshot_id = ?
                """,
                (
                    normalized,
                ),
            ).fetchone()

        if row is None:
            return None

        return self._from_row(
            row
        )

    def require(
        self,
        snapshot_id: str,
    ) -> HistoricalSnapshot:
        """Return one snapshot or raise KeyError."""
        snapshot = self.get(
            snapshot_id
        )

        if snapshot is None:
            raise KeyError(
                f"No historical snapshot found for {snapshot_id}"
            )

        return snapshot

    def find_by_package_id(
        self,
        package_id: str,
    ) -> tuple[HistoricalSnapshot, ...]:
        normalized = HistoricalSnapshot._normalize_required_text(
            package_id,
            field_name="package_id",
        )

        self.store.initialize()

        with self.store.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM snapshots
                WHERE package_id = ?
                ORDER BY generated_at, archived_at, snapshot_id
                """,
                (
                    normalized,
                ),
            ).fetchall()

        return tuple(
            self._from_row(
                row
            )
            for row in rows
        )

    def find_generated_between(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> tuple[HistoricalSnapshot, ...]:
        self._validate_aware_datetime(
            start,
            field_name="start",
        )
        self._validate_aware_datetime(
            end,
            field_name="end",
        )

        if end < start:
            raise ValueError(
                "end must not be earlier than start"
            )

        self.store.initialize()

        with self.store.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM snapshots
                WHERE generated_at >= ?
                  AND generated_at <= ?
                ORDER BY generated_at, archived_at, snapshot_id
                """,
                (
                    start.isoformat(),
                    end.isoformat(),
                ),
            ).fetchall()

        return tuple(
            self._from_row(
                row
            )
            for row in rows
        )

    def latest(
        self,
    ) -> HistoricalSnapshot | None:
        self.store.initialize()

        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM snapshots
                ORDER BY generated_at DESC,
                         archived_at DESC,
                         snapshot_id DESC
                LIMIT 1
                """
            ).fetchone()

        if row is None:
            return None

        return self._from_row(
            row
        )

    def count(
        self,
    ) -> int:
        self.store.initialize()

        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM snapshots
                """
            ).fetchone()

        return int(
            row["count"]
        )

    @staticmethod
    def _snapshot_values(
        snapshot: HistoricalSnapshot,
    ) -> tuple[object, ...]:
        return (
            snapshot.snapshot_id,
            snapshot.package_id,
            snapshot.package_schema_version,
            snapshot.product_version,
            snapshot.generated_at.isoformat(),
            snapshot.archived_at.isoformat(),
            snapshot.relative_path,
            snapshot.checksum_sha256,
            snapshot.supersedes,
            snapshot.status,
        )

    @staticmethod
    def _from_row(
        row: sqlite3.Row,
    ) -> HistoricalSnapshot:
        return HistoricalSnapshot(
            snapshot_id=row["snapshot_id"],
            package_id=row["package_id"],
            package_schema_version=(
                row["package_schema_version"]
            ),
            product_version=row["product_version"],
            generated_at=datetime.fromisoformat(
                row["generated_at"]
            ),
            archived_at=datetime.fromisoformat(
                row["archived_at"]
            ),
            relative_path=row["relative_path"],
            checksum_sha256=row["checksum_sha256"],
            supersedes=row["supersedes"],
            status=row["status"],
        )

    @staticmethod
    def _validate_aware_datetime(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if not isinstance(
            value,
            datetime,
        ):
            raise TypeError(
                f"{field_name} must be a datetime"
            )

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                f"{field_name} must be timezone-aware"
            )
