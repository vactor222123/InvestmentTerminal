"""
Load and verify immutable archived Review Packages.
"""

from pathlib import Path
from typing import Any

from investment_terminal.history.historical_snapshot_integrity import (
    HistoricalSnapshotIntegrityVerifier,
)
from investment_terminal.history.historical_snapshot_reader import (
    HistoricalSnapshotReader,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)


class HistoricalReviewPackageLoader:
    """
    Read one archived Review Package using HistoricalSnapshot metadata.

    The loader verifies:

    - archive path safety;
    - file existence;
    - exact SHA-256 integrity;
    - UTF-8 encoding;
    - JSON object structure;
    - package schema version;
    - generated_at identity.

    It does not modify the archive or the snapshot metadata.
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
        self.verifier = HistoricalSnapshotIntegrityVerifier(
            self.archive_root
        )

    def load(
        self,
        snapshot: HistoricalSnapshot,
    ) -> dict[str, Any]:
        """Return the verified archived Review Package payload."""
        if not isinstance(
            snapshot,
            HistoricalSnapshot,
        ):
            raise TypeError(
                "snapshot must be a HistoricalSnapshot"
            )

        try:
            package_bytes = self.verifier.read_verified_bytes(snapshot)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                "Archived Review Package does not exist: "
                f"{self.verifier.resolve_path(snapshot)}"
            ) from exc
        except ValueError as exc:
            raise ValueError(
                "Archived Review Package checksum does not match "
                f"snapshot {snapshot.snapshot_id}"
            ) from exc

        try:
            payload = HistoricalSnapshotReader.deserialize_verified_bytes(
                package_bytes
            )
        except ValueError as exc:
            message = str(exc)
            if "UTF-8" in message:
                raise ValueError(
                    "Archived Review Package must be UTF-8 encoded"
                ) from exc
            if "invalid JSON" in message:
                raise ValueError(
                    "Archived Review Package must contain valid JSON"
                ) from exc
            if "JSON object" in message:
                raise ValueError(
                    "Archived Review Package JSON must contain an object"
                ) from exc
            raise

        self._validate_package_identity(
            payload=payload,
            snapshot=snapshot,
        )

        return payload

    def resolve_path(
        self,
        snapshot: HistoricalSnapshot,
    ) -> Path:
        """
        Resolve the archive path while preventing archive-root escape.
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
                "snapshot relative_path escapes the archive root"
            ) from exc

        return candidate

    @staticmethod
    def _validate_package_identity(
        *,
        payload: dict[str, Any],
        snapshot: HistoricalSnapshot,
    ) -> None:
        schema_version = payload.get(
            "schema_version"
        )

        if schema_version != snapshot.package_schema_version:
            raise ValueError(
                "Archived Review Package schema_version does not "
                "match snapshot metadata"
            )

        generated_at = payload.get(
            "generated_at"
        )

        if not isinstance(
            generated_at,
            str,
        ):
            raise ValueError(
                "Archived Review Package generated_at must be "
                "an ISO-8601 string"
            )

        normalized = (
            generated_at[:-1] + "+00:00"
            if generated_at.endswith(
                "Z"
            )
            else generated_at
        )

        try:
            from datetime import datetime

            parsed = datetime.fromisoformat(
                normalized
            )
        except ValueError as exc:
            raise ValueError(
                "Archived Review Package generated_at must be "
                "a valid ISO-8601 datetime"
            ) from exc

        if (
            parsed.tzinfo is None
            or parsed.utcoffset() is None
        ):
            raise ValueError(
                "Archived Review Package generated_at must be "
                "timezone-aware"
            )

        if parsed != snapshot.generated_at:
            raise ValueError(
                "Archived Review Package generated_at does not "
                "match snapshot metadata"
            )
