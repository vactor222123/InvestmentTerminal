"""
Tests for verified historical snapshot reads.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_snapshot_integrity import (
    HistoricalSnapshotIntegrityVerifier,
)
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_snapshot_reader import (
    HistoricalSnapshotReader,
)


SNAPSHOT_ID = "2f132e09-38c9-4471-bb48-875b4f9ec8e8"


def create_snapshot(
    archive_root: Path,
    payload_bytes: bytes,
) -> HistoricalSnapshot:
    relative_path = (
        "2026/08/"
        f"{SNAPSHOT_ID}.json"
    )
    archive_path = archive_root / relative_path
    archive_path.parent.mkdir(
        parents=True,
    )
    archive_path.write_bytes(
        payload_bytes
    )
    return HistoricalSnapshot(
        snapshot_id=SNAPSHOT_ID,
        package_id="review-001",
        package_schema_version="1.0",
        product_version="0.12.0",
        generated_at=datetime(
            2026, 8, 3, 17, 35,
            tzinfo=timezone.utc,
        ),
        archived_at=datetime(
            2026, 8, 3, 18, 0,
            tzinfo=timezone.utc,
        ),
        relative_path=relative_path,
        checksum_sha256=hashlib.sha256(
            payload_bytes
        ).hexdigest(),
    )


def create_reader(
    tmp_path: Path,
) -> tuple[
    HistoricalSnapshotReader,
    HistoricalSnapshotManifest,
]:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "history" / "manifest.jsonl"
    )
    verifier = HistoricalSnapshotIntegrityVerifier(
        tmp_path / "history"
    )
    return (
        HistoricalSnapshotReader(
            manifest=manifest,
            verifier=verifier,
        ),
        manifest,
    )


def test_reader_returns_verified_json_object(
    tmp_path: Path,
) -> None:
    payload = {
        "schema_version": "1.0",
        "portfolio_name": "Test Portfolio",
    }
    package_bytes = (
        json.dumps(payload).encode("utf-8")
        + b"\n"
    )
    snapshot = create_snapshot(
        tmp_path / "history",
        package_bytes,
    )
    reader, manifest = create_reader(
        tmp_path
    )
    manifest.append(
        snapshot
    )

    assert reader.read_by_snapshot_id(
        SNAPSHOT_ID
    ) == payload


def test_reader_rejects_modified_archive_before_json_read(
    tmp_path: Path,
) -> None:
    original = b'{"state":"original"}\n'
    snapshot = create_snapshot(
        tmp_path / "history",
        original,
    )
    reader, manifest = create_reader(
        tmp_path
    )
    manifest.append(
        snapshot
    )
    (
        tmp_path
        / "history"
        / snapshot.relative_path
    ).write_bytes(
        b'{"state":"modified"}\n'
    )

    with pytest.raises(
        ValueError,
        match="Historical snapshot checksum mismatch",
    ):
        reader.read_by_snapshot_id(
            SNAPSHOT_ID
        )


def test_reader_rejects_verified_non_object_json(
    tmp_path: Path,
) -> None:
    package_bytes = b'["not","object"]\n'
    snapshot = create_snapshot(
        tmp_path / "history",
        package_bytes,
    )
    reader, manifest = create_reader(
        tmp_path
    )
    manifest.append(
        snapshot
    )

    with pytest.raises(
        ValueError,
        match="archive root must be a JSON object",
    ):
        reader.read(
            snapshot
        )


def test_reader_rejects_verified_invalid_json(
    tmp_path: Path,
) -> None:
    package_bytes = b'{"broken":\n'
    snapshot = create_snapshot(
        tmp_path / "history",
        package_bytes,
    )
    reader, manifest = create_reader(
        tmp_path
    )
    manifest.append(
        snapshot
    )

    with pytest.raises(
        ValueError,
        match="archive contains invalid JSON",
    ):
        reader.read(
            snapshot
        )


def test_reader_propagates_unknown_snapshot_id(
    tmp_path: Path,
) -> None:
    reader, _ = create_reader(
        tmp_path
    )

    with pytest.raises(
        KeyError,
        match="No historical snapshot found",
    ):
        reader.read_by_snapshot_id(
            SNAPSHOT_ID
        )


def test_reader_rejects_invalid_dependencies(
    tmp_path: Path,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )
    verifier = HistoricalSnapshotIntegrityVerifier(
        tmp_path
    )

    with pytest.raises(
        TypeError,
        match="manifest must be a HistoricalSnapshotManifest",
    ):
        HistoricalSnapshotReader(
            manifest=object(),  # type: ignore[arg-type]
            verifier=verifier,
        )

    with pytest.raises(
        TypeError,
        match="verifier must be a HistoricalSnapshotIntegrityVerifier",
    ):
        HistoricalSnapshotReader(
            manifest=manifest,
            verifier=object(),  # type: ignore[arg-type]
        )
