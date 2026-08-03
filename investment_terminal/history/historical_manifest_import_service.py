"""
Import HistoricalSnapshot metadata from the append-only manifest into SQLite.
"""

from dataclasses import dataclass

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
        """Return whether this run imported at least one new snapshot."""
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
    """
    Synchronize snapshot metadata from manifest.jsonl into history.db.

    Existing snapshot IDs are skipped. New manifest entries are inserted in
    one atomic batch. Archived JSON files remain the historical source of
    truth; this service imports only normalized metadata.
    """

    def __init__(
        self,
        *,
        manifest: HistoricalSnapshotManifest,
        repository: HistoricalSnapshotRepository,
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

        self.manifest = manifest
        self.repository = repository

    def synchronize(
        self,
    ) -> ManifestImportResult:
        """
        Import every manifest snapshot not already present in SQLite.
        """
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
