"""
Load and verify immutable archived Review Packages.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

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

        archive_path = self.resolve_path(
            snapshot
        )

        try:
            package_bytes = archive_path.read_bytes()
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                "Archived Review Package does not exist: "
                f"{archive_path}"
            ) from exc

        actual_checksum = hashlib.sha256(
            package_bytes
        ).hexdigest()

        if actual_checksum != snapshot.checksum_sha256:
            raise ValueError(
                "Archived Review Package checksum does not match "
                f"snapshot {snapshot.snapshot_id}"
            )

        try:
            text = package_bytes.decode(
                "utf-8"
            )
        except UnicodeDecodeError as exc:
            raise ValueError(
                "Archived Review Package must be UTF-8 encoded"
            ) from exc

        try:
            payload = json.loads(
                text
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Archived Review Package must contain valid JSON"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "Archived Review Package JSON must contain an object"
            )

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
