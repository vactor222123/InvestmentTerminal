"""
Integrity verification for immutable historical review snapshots.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)


@dataclass(frozen=True, slots=True)
class HistoricalSnapshotIntegrityResult:
    """Result of verifying one archived historical snapshot."""

    snapshot_id: str
    archive_path: Path
    expected_checksum_sha256: str
    actual_checksum_sha256: str
    is_valid: bool
    package_bytes: bytes


class HistoricalSnapshotIntegrityVerifier:
    """
    Verify that archived snapshot bytes still match manifest metadata.

    Historical evidence must never be consumed silently after corruption,
    partial replacement, manual modification, or archive-root escape.
    """

    def __init__(
        self,
        archive_root: str | Path,
    ) -> None:
        self.archive_root = (
            archive_root
            if isinstance(archive_root, Path)
            else Path(archive_root)
        )

    def verify(
        self,
        snapshot: HistoricalSnapshot,
    ) -> HistoricalSnapshotIntegrityResult:
        """
        Verify one snapshot and return the complete integrity result.
        """
        if not isinstance(
            snapshot,
            HistoricalSnapshot,
        ):
            raise TypeError(
                "snapshot must be a HistoricalSnapshot"
            )

        archive_path = self.resolve_path(
            snapshot
        )

        try:
            package_bytes = archive_path.read_bytes()
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                "Historical snapshot archive does not exist: "
                f"{archive_path}"
            ) from exc

        actual_checksum = hashlib.sha256(
            package_bytes
        ).hexdigest()

        return HistoricalSnapshotIntegrityResult(
            snapshot_id=snapshot.snapshot_id,
            archive_path=archive_path,
            expected_checksum_sha256=(
                snapshot.checksum_sha256
            ),
            actual_checksum_sha256=actual_checksum,
            is_valid=(
                actual_checksum
                == snapshot.checksum_sha256
            ),
            package_bytes=package_bytes,
        )

    def read_verified_bytes(
        self,
        snapshot: HistoricalSnapshot,
    ) -> bytes:
        """Read and return archive bytes only after checksum verification."""
        result = self.verify(snapshot)

        if not result.is_valid:
            raise ValueError(
                "Historical snapshot checksum mismatch: "
                f"{snapshot.snapshot_id}"
            )

        return result.package_bytes

    def require_valid(
        self,
        snapshot: HistoricalSnapshot,
    ) -> Path:
        """
        Return the archive path only when checksum verification succeeds.
        """
        result = self.verify(snapshot)

        if not result.is_valid:
            raise ValueError(
                "Historical snapshot checksum mismatch: "
                f"{snapshot.snapshot_id}"
            )

        return result.archive_path

    def resolve_path(
        self,
        snapshot: HistoricalSnapshot,
    ) -> Path:
        """
        Resolve a snapshot path without permitting archive-root escape.

        Resolution is performed before file reads so symlinks or junction-like
        path components cannot redirect verification outside archive_root.
        """
        if not isinstance(
            snapshot,
            HistoricalSnapshot,
        ):
            raise TypeError(
                "snapshot must be a HistoricalSnapshot"
            )

        root = self.archive_root.resolve()
        candidate = (
            root
            / Path(
                snapshot.relative_path
            )
        ).resolve()

        try:
            candidate.relative_to(
                root
            )
        except ValueError as exc:
            raise ValueError(
                "Historical snapshot path escapes the archive root"
            ) from exc

        return candidate
