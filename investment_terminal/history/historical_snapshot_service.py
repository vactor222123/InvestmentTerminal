"""
Application service for the complete historical snapshot workflow.
"""

from pathlib import Path

from investment_terminal.history.historical_snapshot_archive import (
    HistoricalSnapshotArchive,
)
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.utils.atomic_write import (
    sync_directory,
)


class HistoricalSnapshotService:
    """
    Archive one review package and register it in the snapshot manifest.

    The service coordinates the History Domain workflow:

        review package
            -> immutable archive file
            -> HistoricalSnapshot metadata
            -> append-only manifest

    If manifest registration fails or is interrupted, the newly-created
    archive file is removed because the workflow has not completed and the
    snapshot has not become a registered historical record.
    """

    def __init__(
        self,
        *,
        archive: HistoricalSnapshotArchive,
        manifest: HistoricalSnapshotManifest,
    ) -> None:
        if not isinstance(
            archive,
            HistoricalSnapshotArchive,
        ):
            raise TypeError(
                "archive must be a HistoricalSnapshotArchive"
            )

        if not isinstance(
            manifest,
            HistoricalSnapshotManifest,
        ):
            raise TypeError(
                "manifest must be a HistoricalSnapshotManifest"
            )

        self.archive = archive
        self.manifest = manifest

    def preserve(
        self,
        source_path: str | Path,
        *,
        product_version: str | None = None,
        package_id: str | None = None,
        supersedes: str | None = None,
    ) -> HistoricalSnapshot:
        """
        Preserve one review package and return its registered snapshot.
        """
        snapshot = self.archive.archive(
            source_path,
            product_version=product_version,
            package_id=package_id,
            supersedes=supersedes,
        )
        archived_path = (
            self.archive.archive_root
            / snapshot.relative_path
        )

        try:
            self.manifest.append(
                snapshot
            )
        except BaseException:
            self._remove_unregistered_snapshot(
                archived_path
            )
            raise

        return snapshot

    @staticmethod
    def _remove_unregistered_snapshot(
        archived_path: Path,
    ) -> None:
        """
        Remove an archive file created by an incomplete workflow.

        The deletion is synchronized before cleanup is considered complete.
        Only the newly-created unregistered file is removed. Existing manifest
        entries and completed historical snapshots are never modified.
        """
        try:
            archived_path.unlink(
                missing_ok=True
            )
            sync_directory(
                archived_path.parent
            )
        except OSError as exc:
            raise RuntimeError(
                "Snapshot manifest registration failed and the "
                "unregistered archive file could not be durably removed: "
                f"{archived_path}"
            ) from exc

        HistoricalSnapshotService._remove_empty_parents(
            archived_path.parent
        )

    @staticmethod
    def _remove_empty_parents(
        directory: Path,
    ) -> None:
        """
        Remove empty year/month directories without touching non-empty paths.
        """
        current = directory

        for _ in range(2):
            try:
                current.rmdir()
            except OSError:
                return

            current = current.parent
