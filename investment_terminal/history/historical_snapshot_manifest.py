"""
Append-only manifest for immutable historical review snapshots.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)


class HistoricalSnapshotManifest:
    """
    Maintain a JSON Lines index of archived historical snapshots.

    The manifest is an append-only navigation index. The archived review
    package remains the canonical historical evidence.
    """

    def __init__(
        self,
        manifest_path: str | Path,
    ) -> None:
        self.manifest_path = (
            manifest_path
            if isinstance(manifest_path, Path)
            else Path(manifest_path)
        )

        if self.manifest_path.suffix.lower() not in (
            ".jsonl",
            ".ndjson",
        ):
            raise ValueError(
                "manifest_path must use .jsonl or .ndjson"
            )

    def append(
        self,
        snapshot: HistoricalSnapshot,
    ) -> Path:
        """
        Append one snapshot metadata record.

        Duplicate snapshot IDs and archive paths are rejected before the
        manifest is changed.
        """
        if not isinstance(
            snapshot,
            HistoricalSnapshot,
        ):
            raise TypeError(
                "snapshot must be a HistoricalSnapshot"
            )

        existing = self.load_all()

        if any(
            item.snapshot_id
            == snapshot.snapshot_id
            for item in existing
        ):
            raise ValueError(
                "manifest already contains snapshot_id "
                f"{snapshot.snapshot_id}"
            )

        if any(
            item.relative_path
            == snapshot.relative_path
            for item in existing
        ):
            raise ValueError(
                "manifest already contains relative_path "
                f"{snapshot.relative_path}"
            )

        record = (
            json.dumps(
                snapshot.to_dict(),
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
                allow_nan=False,
            )
            + "\n"
        )

        self.manifest_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.manifest_path.open(
            "a",
            encoding="utf-8",
            newline="\n",
        ) as manifest:
            manifest.write(
                record
            )
            manifest.flush()

        return self.manifest_path

    def load_all(
        self,
    ) -> tuple[HistoricalSnapshot, ...]:
        """
        Load every valid manifest entry in chronological append order.
        """
        if not self.manifest_path.exists():
            return ()

        snapshots: list[
            HistoricalSnapshot
        ] = []

        with self.manifest_path.open(
            "r",
            encoding="utf-8",
        ) as manifest:
            for line_number, line in enumerate(
                manifest,
                start=1,
            ):
                if not line.strip():
                    continue

                snapshots.append(
                    self._parse_line(
                        line,
                        line_number=line_number,
                    )
                )

        return tuple(
            snapshots
        )

    def require_by_snapshot_id(
        self,
        snapshot_id: str,
    ) -> HistoricalSnapshot:
        normalized = self._required_text(
            snapshot_id,
            field_name="snapshot_id",
        ).lower()

        for snapshot in self.load_all():
            if (
                snapshot.snapshot_id
                == normalized
            ):
                return snapshot

        raise KeyError(
            "No historical snapshot found for "
            f"{normalized}"
        )

    def find_by_package_id(
        self,
        package_id: str,
    ) -> tuple[HistoricalSnapshot, ...]:
        normalized = self._required_text(
            package_id,
            field_name="package_id",
        )

        return tuple(
            snapshot
            for snapshot in self.load_all()
            if snapshot.package_id
            == normalized
        )

    def find_by_relative_path(
        self,
        relative_path: str,
    ) -> HistoricalSnapshot | None:
        normalized = (
            self._required_text(
                relative_path,
                field_name="relative_path",
            )
            .replace(
                "\\",
                "/",
            )
        )

        for snapshot in self.load_all():
            if (
                snapshot.relative_path
                == normalized
            ):
                return snapshot

        return None

    def find_generated_between(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> tuple[HistoricalSnapshot, ...]:
        self._validate_aware_datetime(
            start,
            field_name="start",
        )
        self._validate_aware_datetime(
            end,
            field_name="end",
        )

        if end < start:
            raise ValueError(
                "end must not be earlier than start"
            )

        return tuple(
            snapshot
            for snapshot in self.load_all()
            if (
                start
                <= snapshot.generated_at
                <= end
            )
        )

    def latest(
        self,
    ) -> HistoricalSnapshot | None:
        snapshots = self.load_all()

        if not snapshots:
            return None

        return max(
            snapshots,
            key=lambda snapshot: (
                snapshot.generated_at,
                snapshot.archived_at,
                snapshot.snapshot_id,
            ),
        )

    @classmethod
    def _parse_line(
        cls,
        line: str,
        *,
        line_number: int,
    ) -> HistoricalSnapshot:
        try:
            payload = json.loads(
                line
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Invalid historical manifest JSON "
                f"on line {line_number}"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "Historical manifest entry "
                f"on line {line_number} "
                "must be a JSON object"
            )

        try:
            return HistoricalSnapshot(
                snapshot_id=payload[
                    "snapshot_id"
                ],
                package_id=payload.get(
                    "package_id"
                ),
                package_schema_version=payload[
                    "package_schema_version"
                ],
                product_version=payload.get(
                    "product_version"
                ),
                generated_at=cls._parse_datetime(
                    payload[
                        "generated_at"
                    ],
                    field_name="generated_at",
                ),
                archived_at=cls._parse_datetime(
                    payload[
                        "archived_at"
                    ],
                    field_name="archived_at",
                ),
                relative_path=payload[
                    "relative_path"
                ],
                checksum_sha256=payload[
                    "checksum_sha256"
                ],
                supersedes=payload.get(
                    "supersedes"
                ),
                status=payload[
                    "status"
                ],
            )
        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "Invalid historical manifest entry "
                f"on line {line_number}: {exc}"
            ) from exc

    @staticmethod
    def _parse_datetime(
        value: object,
        *,
        field_name: str,
    ) -> datetime:
        if not isinstance(
            value,
            str,
        ):
            raise ValueError(
                f"{field_name} must be an ISO-8601 string"
            )

        normalized = (
            value[:-1] + "+00:00"
            if value.endswith(
                "Z"
            )
            else value
        )

        try:
            parsed = datetime.fromisoformat(
                normalized
            )
        except ValueError as exc:
            raise ValueError(
                f"{field_name} must be a valid ISO-8601 datetime"
            ) from exc

        HistoricalSnapshotManifest._validate_aware_datetime(
            parsed,
            field_name=field_name,
        )

        return parsed

    @staticmethod
    def _required_text(
        value: object,
        *,
        field_name: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} must be a non-empty string"
            )

        return value.strip()

    @staticmethod
    def _validate_aware_datetime(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if not isinstance(
            value,
            datetime,
        ):
            raise TypeError(
                f"{field_name} must be a datetime"
            )

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                f"{field_name} must be timezone-aware"
            )
