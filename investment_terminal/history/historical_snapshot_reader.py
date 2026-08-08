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

        archive_path = self.verifier.require_valid(
            snapshot
        )

        try:
            payload = json.loads(
                archive_path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Historical snapshot archive contains invalid JSON: "
                f"{archive_path}"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "Historical snapshot archive root must be a JSON object: "
                f"{archive_path}"
            )

        return payload
