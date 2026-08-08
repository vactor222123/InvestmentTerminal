"""
Immutable archive writer for investment review packages.
"""

import hashlib
import json
import os
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)


class HistoricalSnapshotArchive:
    """
    Preserve an existing review-package JSON file without changing its bytes.

    The source package and snapshot metadata are validated before any archive
    file is created. Valid packages are copied into the append-only archive
    with exclusive file creation and represented by a canonical
    HistoricalSnapshot metadata object.
    """

    def __init__(
        self,
        archive_root: str | Path,
        *,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self.archive_root = (
            archive_root
            if isinstance(archive_root, Path)
            else Path(archive_root)
        )
        self._clock = clock or (
            lambda: datetime.now(
                timezone.utc
            )
        )
        self._uuid_factory = uuid_factory or uuid4

    def archive(
        self,
        source_path: str | Path,
        *,
        product_version: str | None = None,
        package_id: str | None = None,
        supersedes: str | None = None,
    ) -> HistoricalSnapshot:
        """Archive one completed investment review package."""
        source = (
            source_path
            if isinstance(source_path, Path)
            else Path(source_path)
        )

        if source.suffix.lower() != ".json":
            raise ValueError(
                "source_path must point to a JSON file"
            )

        try:
            package_bytes = source.read_bytes()
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Review package does not exist: {source}"
            ) from exc

        payload = self._load_payload(
            package_bytes
        )
        schema_version = self._required_text(
            payload.get(
                "schema_version"
            ),
            field_name="schema_version",
        )
        generated_at = self._parse_generated_at(
            payload.get(
                "generated_at"
            )
        )
        resolved_package_id = (
            package_id
            if package_id is not None
            else self._package_id_from_payload(
                payload
            )
        )

        archived_at = self._clock()
        self._validate_aware_datetime(
            archived_at,
            field_name="archived_at",
        )

        snapshot_id = str(
            self._uuid_factory()
        )
        relative_path = self._build_relative_path(
            generated_at=generated_at,
            snapshot_id=snapshot_id,
        )
        checksum = hashlib.sha256(
            package_bytes
        ).hexdigest()

        snapshot = HistoricalSnapshot(
            snapshot_id=snapshot_id,
            package_id=resolved_package_id,
            package_schema_version=schema_version,
            product_version=product_version,
            generated_at=generated_at,
            archived_at=archived_at,
            relative_path=relative_path,
            checksum_sha256=checksum,
            supersedes=supersedes,
            status="ARCHIVED",
        )

        destination = (
            self.archive_root
            / Path(
                snapshot.relative_path
            )
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._write_exclusive_durable(
            destination,
            package_bytes,
        )

        return snapshot

    @staticmethod
    def _write_exclusive_durable(
        destination: Path,
        package_bytes: bytes,
    ) -> None:
        created = False

        try:
            with destination.open(
                "xb",
            ) as output:
                created = True
                output.write(
                    package_bytes
                )
                output.flush()
                os.fsync(
                    output.fileno()
                )
        except FileExistsError as exc:
            raise FileExistsError(
                "Historical snapshot already exists: "
                f"{destination}"
            ) from exc
        except BaseException:
            if created:
                with suppress(
                    OSError,
                ):
                    destination.unlink()
            raise

    @staticmethod
    def _load_payload(
        package_bytes: bytes,
    ) -> dict[str, Any]:
        try:
            text = package_bytes.decode(
                "utf-8"
            )
        except UnicodeDecodeError as exc:
            raise ValueError(
                "Review package must be UTF-8 encoded"
            ) from exc

        try:
            payload = json.loads(
                text
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Review package must contain valid JSON"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "Review package JSON must contain an object"
            )

        return payload

    @classmethod
    def _parse_generated_at(
        cls,
        value: object,
    ) -> datetime:
        text = cls._required_text(
            value,
            field_name="generated_at",
        )

        normalized = (
            text[:-1] + "+00:00"
            if text.endswith("Z")
            else text
        )

        try:
            generated_at = datetime.fromisoformat(
                normalized
            )
        except ValueError as exc:
            raise ValueError(
                "generated_at must be a valid ISO-8601 datetime"
            ) from exc

        cls._validate_aware_datetime(
            generated_at,
            field_name="generated_at",
        )

        return generated_at

    @staticmethod
    def _package_id_from_payload(
        payload: dict[str, Any],
    ) -> str | None:
        direct = payload.get(
            "package_id"
        )

        if (
            isinstance(direct, str)
            and direct.strip()
        ):
            return direct.strip()

        metadata = payload.get(
            "metadata"
        )

        if isinstance(
            metadata,
            dict,
        ):
            nested = metadata.get(
                "package_id"
            )

            if (
                isinstance(nested, str)
                and nested.strip()
            ):
                return nested.strip()

        return None

    @staticmethod
    def _build_relative_path(
        *,
        generated_at: datetime,
        snapshot_id: str,
    ) -> str:
        utc_generated_at = (
            generated_at.astimezone(
                timezone.utc
            )
        )
        timestamp = utc_generated_at.strftime(
            "%Y-%m-%dT%H-%M-%SZ"
        )

        return (
            f"{utc_generated_at:%Y/%m}/"
            f"{timestamp}_{snapshot_id}.json"
        )

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
