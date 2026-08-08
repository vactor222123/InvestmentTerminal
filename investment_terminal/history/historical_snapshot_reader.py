"""
Verified read access to immutable historical review snapshots.
"""

import json
from pathlib import Path
from typing import Any

from investment_terminal.history.historical_snapshot_integrity import (
    HistoricalSnapshotIntegrityVerifier,
)
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)


class HistoricalSnapshotReader:
    """
    Resolve manifest metadata, verify archive integrity, and then read JSON.

    Historical package contents are never returned before SHA-256 verification
    succeeds against the manifest metadata.
    """

    def __init__(
        self,
        *,
        manifest: HistoricalSnapshotManifest,
        verifier: HistoricalSnapshotIntegrityVerifier,
    ) -> None:
        if not isinstance(
            manifest,
            HistoricalSnapshotManifest,
        ):
            raise TypeError(
                "manifest must be a HistoricalSnapshotManifest"
            )
        if not isinstance(
            verifier,
            HistoricalSnapshotIntegrityVerifier,
        ):
            raise TypeError(
                "verifier must be a HistoricalSnapshotIntegrityVerifier"
            )

        self.manifest = manifest
        self.verifier = verifier

    def read_by_snapshot_id(
        self,
        snapshot_id: str,
    ) -> dict[str, Any]:
        """
        Resolve, verify, and deserialize one historical review package.
        """
        snapshot = self.manifest.require_by_snapshot_id(
            snapshot_id
        )
        return self.read(
            snapshot
        )

    def read(
        self,
        snapshot: HistoricalSnapshot,
    ) -> dict[str, Any]:
        """
        Verify one snapshot before deserializing its archived JSON package.
        """
        if not isinstance(
            snapshot,
            HistoricalSnapshot,
        ):
            raise TypeError(
                "snapshot must be a HistoricalSnapshot"
            )

        package_bytes = self.verifier.read_verified_bytes(snapshot)

        return self.deserialize_verified_bytes(package_bytes)

    @staticmethod
    def deserialize_verified_bytes(
        package_bytes: bytes,
    ) -> dict[str, Any]:
        """Decode and deserialize bytes already verified by the integrity layer."""
        if not isinstance(package_bytes, bytes):
            raise TypeError("package_bytes must be bytes")

        try:
            text = package_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Historical snapshot archive must be UTF-8 encoded") from exc

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("Historical snapshot archive contains invalid JSON") from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "Historical snapshot archive root must be a JSON object"
            )

        return payload
