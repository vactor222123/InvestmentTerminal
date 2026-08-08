"""
SQLite repository for historical snapshot import state.
"""

import sqlite3
from datetime import datetime

from investment_terminal.history.historical_import_state_models import (
    HistoricalImportState,
)
from investment_terminal.history.historical_schema_migrations import (
    HISTORICAL_SCHEMA_TARGET_VERSION,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
)


class HistoricalImportStateRepository:
    """Persist and query explicit structured-import lifecycle state."""

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

    def get(
        self,
        snapshot_id: str,
    ) -> HistoricalImportState | None:
        """Return import state for one snapshot, or None when absent."""
        self._require_schema()

        normalized_id = HistoricalSnapshot._normalize_uuid(
            snapshot_id,
            field_name="snapshot_id",
        )

        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM historical_import_state
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
    ) -> HistoricalImportState:
        """Return import state for one snapshot or raise KeyError."""
        state = self.get(
            snapshot_id
        )

        if state is None:
            raise KeyError(
                f"No historical import state found for {snapshot_id}"
            )

        return state

    def initialize_metadata(
        self,
        snapshot: HistoricalSnapshot,
        *,
        at: datetime,
    ) -> HistoricalImportState:
        """Create METADATA_ONLY state for an already registered snapshot."""
        if not isinstance(
            snapshot,
            HistoricalSnapshot,
        ):
            raise TypeError(
                "snapshot must be a HistoricalSnapshot"
            )

        self._require_schema()

        validate_aware_datetime(
            at,
            field_name="at",
        )

        state = HistoricalImportState(
            snapshot_id=snapshot.snapshot_id,
            status="METADATA_ONLY",
            metadata_synchronized_at=at,
            updated_at=at,
        )

        try:
            with self.store.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO historical_import_state (
                        snapshot_id,
                        status,
                        metadata_synchronized_at,
                        package_verified_at,
                        details_imported_at,
                        timeline_built_at,
                        importer_version,
                        failure_reason,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._values(
                        state
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Historical import state already exists or "
                "references an unknown snapshot"
            ) from exc

        return state

    def mark_verified(
        self,
        snapshot_id: str,
        *,
        at: datetime,
    ) -> HistoricalImportState:
        """Transition METADATA_ONLY or FAILED state to VERIFIED."""
        return self._transition(
            snapshot_id,
            status="VERIFIED",
            at=at,
        )

    def mark_importing(
        self,
        snapshot_id: str,
        *,
        at: datetime,
        importer_version: str | None = None,
    ) -> HistoricalImportState:
        """Transition VERIFIED state to IMPORTING."""
        normalized_version = normalize_optional_text(
            importer_version,
            field_name="importer_version",
        )
        return self._transition(
            snapshot_id,
            status="IMPORTING",
            at=at,
            importer_version=normalized_version,
        )

    def mark_imported(
        self,
        snapshot_id: str,
        *,
        at: datetime,
    ) -> HistoricalImportState:
        """Transition IMPORTING state to IMPORTED."""
        return self._transition(
            snapshot_id,
            status="IMPORTED",
            at=at,
        )

    def mark_failed(
        self,
        snapshot_id: str,
        *,
        reason: str,
        at: datetime,
    ) -> HistoricalImportState:
        """Transition a non-completed import state to FAILED."""
        normalized_reason = normalize_required_text(
            reason,
            field_name="reason",
        )
        return self._transition(
            snapshot_id,
            status="FAILED",
            at=at,
            failure_reason=normalized_reason,
        )

    def _transition(
        self,
        snapshot_id: str,
        *,
        status: str,
        at: datetime,
        importer_version: str | None = None,
        failure_reason: str | None = None,
    ) -> HistoricalImportState:
        validate_aware_datetime(
            at,
            field_name="at",
        )

        current = self.require(
            snapshot_id
        )
        next_status = current.require_transition_to(
            status
        )

        if at < current.updated_at:
            raise ValueError(
                "at must not be earlier than the current updated_at"
            )

        package_verified_at = current.package_verified_at
        details_imported_at = current.details_imported_at
        timeline_built_at = current.timeline_built_at
        next_importer_version = current.importer_version

        if next_status == "VERIFIED":
            package_verified_at = at
            failure_reason = None
        elif next_status == "IMPORTING":
            if importer_version is not None:
                next_importer_version = importer_version
        elif next_status == "IMPORTED":
            details_imported_at = at
            timeline_built_at = at

        state = HistoricalImportState(
            snapshot_id=current.snapshot_id,
            status=next_status,
            metadata_synchronized_at=(
                current.metadata_synchronized_at
            ),
            package_verified_at=package_verified_at,
            details_imported_at=details_imported_at,
            timeline_built_at=timeline_built_at,
            importer_version=next_importer_version,
            failure_reason=failure_reason,
            updated_at=at,
        )

        with self.store.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE historical_import_state
                SET status = ?,
                    package_verified_at = ?,
                    details_imported_at = ?,
                    timeline_built_at = ?,
                    importer_version = ?,
                    failure_reason = ?,
                    updated_at = ?
                WHERE snapshot_id = ?
                  AND status = ?
                """,
                (
                    state.status,
                    self._serialize_datetime(
                        state.package_verified_at
                    ),
                    self._serialize_datetime(
                        state.details_imported_at
                    ),
                    self._serialize_datetime(
                        state.timeline_built_at
                    ),
                    state.importer_version,
                    state.failure_reason,
                    state.updated_at.isoformat(),
                    state.snapshot_id,
                    current.status,
                ),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Historical import state changed concurrently"
                )

        return state


    def _require_schema(
        self,
    ) -> None:
        version = self.store.schema_version()

        if version != HISTORICAL_SCHEMA_TARGET_VERSION:
            raise RuntimeError(
                "Historical import state repository requires "
                f"History schema version {HISTORICAL_SCHEMA_TARGET_VERSION}"
            )

    @staticmethod
    def _values(
        state: HistoricalImportState,
    ) -> tuple[object, ...]:
        return (
            state.snapshot_id,
            state.status,
            state.metadata_synchronized_at.isoformat(),
            HistoricalImportStateRepository._serialize_datetime(
                state.package_verified_at
            ),
            HistoricalImportStateRepository._serialize_datetime(
                state.details_imported_at
            ),
            HistoricalImportStateRepository._serialize_datetime(
                state.timeline_built_at
            ),
            state.importer_version,
            state.failure_reason,
            state.updated_at.isoformat(),
        )

    @staticmethod
    def _serialize_datetime(
        value: datetime | None,
    ) -> str | None:
        if value is None:
            return None

        return value.isoformat()

    @staticmethod
    def _parse_optional_datetime(
        value: object,
        *,
        field_name: str,
    ) -> datetime | None:
        if value is None:
            return None

        if not isinstance(
            value,
            str,
        ):
            raise ValueError(
                f"{field_name} must contain an ISO datetime"
            )

        try:
            return datetime.fromisoformat(
                value
            )
        except ValueError as exc:
            raise ValueError(
                f"{field_name} must contain an ISO datetime"
            ) from exc

    @classmethod
    def _from_row(
        cls,
        row: sqlite3.Row,
    ) -> HistoricalImportState:
        return HistoricalImportState(
            snapshot_id=row["snapshot_id"],
            status=row["status"],
            metadata_synchronized_at=datetime.fromisoformat(
                row["metadata_synchronized_at"]
            ),
            package_verified_at=cls._parse_optional_datetime(
                row["package_verified_at"],
                field_name="package_verified_at",
            ),
            details_imported_at=cls._parse_optional_datetime(
                row["details_imported_at"],
                field_name="details_imported_at",
            ),
            timeline_built_at=cls._parse_optional_datetime(
                row["timeline_built_at"],
                field_name="timeline_built_at",
            ),
            importer_version=row["importer_version"],
            failure_reason=row["failure_reason"],
            updated_at=datetime.fromisoformat(
                row["updated_at"]
            ),
        )
