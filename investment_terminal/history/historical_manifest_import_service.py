"""
Import HistoricalSnapshot metadata from the append-only manifest into SQLite.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)


@dataclass(frozen=True, slots=True)
class ManifestImportResult:
    """Summary of one manifest-to-SQLite synchronization run."""

    manifest_records: int
    imported_records: int
    skipped_records: int

    def __post_init__(self) -> None:
        for field_name in (
            "manifest_records",
            "imported_records",
            "skipped_records",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if (
            self.imported_records
            + self.skipped_records
            != self.manifest_records
        ):
            raise ValueError(
                "imported_records plus skipped_records "
                "must equal manifest_records"
            )

    @property
    def changed(
        self,
    ) -> bool:
        return self.imported_records > 0

    def to_dict(
        self,
    ) -> dict[str, int | bool]:
        return {
            "manifest_records": self.manifest_records,
            "imported_records": self.imported_records,
            "skipped_records": self.skipped_records,
            "changed": self.changed,
        }


class HistoricalManifestImportService:
    """Synchronize manifest metadata and optional explicit import state."""

    def __init__(
        self,
        *,
        manifest: HistoricalSnapshotManifest,
        repository: HistoricalSnapshotRepository,
        state_repository: HistoricalImportStateRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(
            manifest,
            HistoricalSnapshotManifest,
        ):
            raise TypeError(
                "manifest must be a HistoricalSnapshotManifest"
            )

        if not isinstance(
            repository,
            HistoricalSnapshotRepository,
        ):
            raise TypeError(
                "repository must be a HistoricalSnapshotRepository"
            )

        if (
            state_repository is not None
            and not isinstance(
                state_repository,
                HistoricalImportStateRepository,
            )
        ):
            raise TypeError(
                "state_repository must be a HistoricalImportStateRepository"
            )

        self.manifest = manifest
        self.repository = repository
        self.state_repository = state_repository
        self._clock = clock or (
            lambda: datetime.now(
                timezone.utc
            )
        )

    def synchronize(
        self,
    ) -> ManifestImportResult:
        manifest_snapshots = self.manifest.load_all()

        pending = tuple(
            snapshot
            for snapshot in manifest_snapshots
            if not self.repository.exists(
                snapshot.snapshot_id
            )
        )

        self.repository.add_many(
            pending
        )

        if self.state_repository is not None:
            for snapshot in manifest_snapshots:
                if (
                    self.state_repository.get(
                        snapshot.snapshot_id
                    )
                    is not None
                ):
                    continue

                reconciliation_time = self._now()

                if self.repository.has_complete_detail_import(
                    snapshot.snapshot_id
                ):
                    self.state_repository.initialize_legacy_imported(
                        snapshot,
                        at=reconciliation_time,
                    )
                else:
                    self.state_repository.initialize_metadata(
                        snapshot,
                        at=reconciliation_time,
                    )

        imported = len(
            pending
        )
        total = len(
            manifest_snapshots
        )

        return ManifestImportResult(
            manifest_records=total,
            imported_records=imported,
            skipped_records=total - imported,
        )

    def _now(
        self,
    ) -> datetime:
        value = self._clock()

        if (
            not isinstance(
                value,
                datetime,
            )
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "clock must return a timezone-aware datetime"
            )

        return value
