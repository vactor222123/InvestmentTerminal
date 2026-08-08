"""
SQLite repository for HistoricalSnapshot metadata.
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
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class HistoricalSnapshotRepository:
    """
    Persist and query normalized historical snapshot metadata.

    The immutable archived Review Package remains the source of truth.
    This repository stores only the structured metadata required for search,
    timeline construction, and later package imports.
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
                    self._values(
                        snapshot
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Historical snapshot already exists or "
                "contains an invalid reference"
            ) from exc

        return snapshot

    def add_many(
        self,
        snapshots: Iterable[HistoricalSnapshot],
    ) -> tuple[HistoricalSnapshot, ...]:
        items = tuple(
            snapshots
        )

        if any(
            not isinstance(
                snapshot,
                HistoricalSnapshot,
            )
            for snapshot in items
        ):
            raise TypeError(
                "snapshots must contain only HistoricalSnapshot values"
            )

        if not items:
            return ()

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
                        self._values(
                            snapshot
                        )
                        for snapshot in items
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Historical snapshot batch could not be inserted"
            ) from exc

        return items

    def get(
        self,
        snapshot_id: str,
    ) -> HistoricalSnapshot | None:
        normalized_id = HistoricalSnapshot._normalize_uuid(
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
                    normalized_id,
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
        snapshot = self.get(
            snapshot_id
        )

        if snapshot is None:
            raise KeyError(
                f"No historical snapshot found for {snapshot_id}"
            )

        return snapshot

    def exists(
        self,
        snapshot_id: str,
    ) -> bool:
        return self.get(
            snapshot_id
        ) is not None

    def list_all(
        self,
    ) -> tuple[HistoricalSnapshot, ...]:
        self.store.initialize()

        with self.store.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM snapshots
                ORDER BY generated_at, archived_at, snapshot_id
                """
            ).fetchall()

        return tuple(
            self._from_row(
                row
            )
            for row in rows
        )

    def has_detail_import(
        self,
        snapshot_id: str,
    ) -> bool:
        normalized_id = HistoricalSnapshot._normalize_uuid(
            snapshot_id,
            field_name="snapshot_id",
        )

        self.store.initialize()

        with self.store.connect() as connection:
            for table in (
                "portfolio_summary",
                "holdings",
                "recommendations",
                "deployment",
                "timeline_events",
            ):
                row = connection.execute(
                    f"""
                    SELECT 1
                    FROM {table}
                    WHERE snapshot_id = ?
                    LIMIT 1
                    """,
                    (
                        normalized_id,
                    ),
                ).fetchone()

                if row is not None:
                    return True

        return False

    def has_complete_detail_import(
        self,
        snapshot_id: str,
    ) -> bool:
        """
        Return whether legacy structured rows form a complete import projection.

        This method exists for reconciliation of pre-import-state databases.
        Normal workflow completion is determined by HistoricalImportState.
        """
        normalized_id = HistoricalSnapshot._normalize_uuid(
            snapshot_id,
            field_name="snapshot_id",
        )

        self.store.initialize()

        with self.store.connect() as connection:
            summary_count = self._count_rows(
                connection,
                "portfolio_summary",
                normalized_id,
            )
            if summary_count != 1:
                return False

            holdings_count = self._count_rows(
                connection,
                "holdings",
                normalized_id,
            )
            recommendations_count = self._count_rows(
                connection,
                "recommendations",
                normalized_id,
            )
            deployment_count = self._count_rows(
                connection,
                "deployment",
                normalized_id,
            )

            event_counts = {
                row["event_type"]: int(
                    row["event_count"]
                )
                for row in connection.execute(
                    """
                    SELECT event_type, COUNT(*) AS event_count
                    FROM timeline_events
                    WHERE snapshot_id = ?
                    GROUP BY event_type
                    """,
                    (
                        normalized_id,
                    ),
                ).fetchall()
            }

        expected = {
            "SNAPSHOT_ARCHIVED": 1,
            "PORTFOLIO_SUMMARY_RECORDED": 1,
        }

        if holdings_count:
            expected[
                "HOLDING_RECORDED"
            ] = holdings_count

        if recommendations_count:
            expected[
                "RECOMMENDATION_RECORDED"
            ] = recommendations_count

        if deployment_count:
            expected[
                "DEPLOYMENT_RECORDED"
            ] = deployment_count

        return event_counts == expected

    def find_by_package_id(
        self,
        package_id: str,
    ) -> tuple[HistoricalSnapshot, ...]:
        normalized = normalize_required_text(
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
        validate_aware_datetime(
            start,
            field_name="start",
        )
        validate_aware_datetime(
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

    def previous_before(
        self,
        snapshot_id: str,
    ) -> HistoricalSnapshot | None:
        target = self.require(
            snapshot_id
        )

        self.store.initialize()

        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM snapshots
                WHERE generated_at < ?
                   OR (
                        generated_at = ?
                    AND archived_at < ?
                   )
                   OR (
                        generated_at = ?
                    AND archived_at = ?
                    AND snapshot_id < ?
                   )
                ORDER BY generated_at DESC,
                         archived_at DESC,
                         snapshot_id DESC
                LIMIT 1
                """,
                (
                    target.generated_at.isoformat(),
                    target.generated_at.isoformat(),
                    target.archived_at.isoformat(),
                    target.generated_at.isoformat(),
                    target.archived_at.isoformat(),
                    target.snapshot_id,
                ),
            ).fetchone()

        if row is None:
            return None

        return self._from_row(
            row
        )

    def next_after(
        self,
        snapshot_id: str,
    ) -> HistoricalSnapshot | None:
        target = self.require(
            snapshot_id
        )

        self.store.initialize()

        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM snapshots
                WHERE generated_at > ?
                   OR (
                        generated_at = ?
                    AND archived_at > ?
                   )
                   OR (
                        generated_at = ?
                    AND archived_at = ?
                    AND snapshot_id > ?
                   )
                ORDER BY generated_at,
                         archived_at,
                         snapshot_id
                LIMIT 1
                """,
                (
                    target.generated_at.isoformat(),
                    target.generated_at.isoformat(),
                    target.archived_at.isoformat(),
                    target.generated_at.isoformat(),
                    target.archived_at.isoformat(),
                    target.snapshot_id,
                ),
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
                SELECT COUNT(*) AS snapshot_count
                FROM snapshots
                """
            ).fetchone()

        return int(
            row["snapshot_count"]
        )

    @staticmethod
    def _count_rows(
        connection: sqlite3.Connection,
        table: str,
        snapshot_id: str,
    ) -> int:
        row = connection.execute(
            f"""
            SELECT COUNT(*) AS row_count
            FROM {table}
            WHERE snapshot_id = ?
            """,
            (
                snapshot_id,
            ),
        ).fetchone()

        return int(
            row["row_count"]
        )

    @staticmethod
    def _values(
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
