"""
Tests for immutable historical snapshot integrity verification.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_snapshot_integrity import (
    HistoricalSnapshotIntegrityVerifier,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)


SNAPSHOT_ID = "2f132e09-38c9-4471-bb48-875b4f9ec8e8"


def create_snapshot(
    *,
    relative_path: str,
    checksum_sha256: str,
) -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=SNAPSHOT_ID,
        package_id="review-001",
        package_schema_version="1.0",
        product_version="0.12.0",
        generated_at=datetime(
            2026,
            8,
            3,
            17,
            35,
            tzinfo=timezone.utc,
        ),
        archived_at=datetime(
            2026,
            8,
            3,
            18,
            0,
            tzinfo=timezone.utc,
        ),
        relative_path=relative_path,
        checksum_sha256=checksum_sha256,
        supersedes=None,
        status="ARCHIVED",
    )


def test_verify_accepts_unchanged_archive(
    tmp_path: Path,
) -> None:
    archive_root = tmp_path / "history"
    relative_path = (
        "2026/08/"
        f"{SNAPSHOT_ID}.json"
    )
    archive_path = (
        archive_root / relative_path
    )
    archive_path.parent.mkdir(
        parents=True,
    )
    package_bytes = (
        b'{"schema_version":"1.0"}\n'
    )
    archive_path.write_bytes(
        package_bytes
    )
    snapshot = create_snapshot(
        relative_path=relative_path,
        checksum_sha256=hashlib.sha256(
            package_bytes
        ).hexdigest(),
    )

    result = (
        HistoricalSnapshotIntegrityVerifier(
            archive_root
        ).verify(
            snapshot
        )
    )

    assert result.is_valid is True
    assert result.snapshot_id == SNAPSHOT_ID
    assert result.archive_path == archive_path.resolve()
    assert (
        result.expected_checksum_sha256
        == result.actual_checksum_sha256
    )


def test_verify_detects_modified_archive(
    tmp_path: Path,
) -> None:
    archive_root = tmp_path / "history"
    relative_path = (
        "2026/08/"
        f"{SNAPSHOT_ID}.json"
    )
    archive_path = (
        archive_root / relative_path
    )
    archive_path.parent.mkdir(
        parents=True,
    )
    original = b'{"state":"original"}\n'
    archive_path.write_bytes(
        b'{"state":"modified"}\n'
    )
    snapshot = create_snapshot(
        relative_path=relative_path,
        checksum_sha256=hashlib.sha256(
            original
        ).hexdigest(),
    )

    result = (
        HistoricalSnapshotIntegrityVerifier(
            archive_root
        ).verify(
            snapshot
        )
    )

    assert result.is_valid is False
    assert (
        result.expected_checksum_sha256
        != result.actual_checksum_sha256
    )


def test_require_valid_returns_verified_archive_path(
    tmp_path: Path,
) -> None:
    archive_root = tmp_path / "history"
    relative_path = (
        "2026/08/"
        f"{SNAPSHOT_ID}.json"
    )
    archive_path = (
        archive_root / relative_path
    )
    archive_path.parent.mkdir(
        parents=True,
    )
    package_bytes = b"snapshot"
    archive_path.write_bytes(
        package_bytes
    )
    snapshot = create_snapshot(
        relative_path=relative_path,
        checksum_sha256=hashlib.sha256(
            package_bytes
        ).hexdigest(),
    )

    result = (
        HistoricalSnapshotIntegrityVerifier(
            archive_root
        ).require_valid(
            snapshot
        )
    )

    assert result == archive_path.resolve()


def test_require_valid_rejects_checksum_mismatch(
    tmp_path: Path,
) -> None:
    archive_root = tmp_path / "history"
    relative_path = (
        "2026/08/"
        f"{SNAPSHOT_ID}.json"
    )
    archive_path = (
        archive_root / relative_path
    )
    archive_path.parent.mkdir(
        parents=True,
    )
    archive_path.write_bytes(
        b"modified"
    )
    snapshot = create_snapshot(
        relative_path=relative_path,
        checksum_sha256=hashlib.sha256(
            b"original"
        ).hexdigest(),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Historical snapshot checksum mismatch"
        ),
    ):
        HistoricalSnapshotIntegrityVerifier(
            archive_root
        ).require_valid(
            snapshot
        )


def test_verify_rejects_missing_archive(
    tmp_path: Path,
) -> None:
    snapshot = create_snapshot(
        relative_path=(
            "2026/08/"
            f"{SNAPSHOT_ID}.json"
        ),
        checksum_sha256="a" * 64,
    )

    with pytest.raises(
        FileNotFoundError,
        match=(
            "Historical snapshot archive does not exist"
        ),
    ):
        HistoricalSnapshotIntegrityVerifier(
            tmp_path / "history"
        ).verify(
            snapshot
        )


def test_verify_rejects_invalid_snapshot_type(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "snapshot must be a HistoricalSnapshot"
        ),
    ):
        HistoricalSnapshotIntegrityVerifier(
            tmp_path
        ).verify(
            object(),  # type: ignore[arg-type]
        )


def test_resolve_path_rejects_symlink_escape(
    tmp_path: Path,
) -> None:
    archive_root = tmp_path / "history"
    outside = tmp_path / "outside"
    outside.mkdir()
    archive_root.mkdir()
    link = archive_root / "2026"
    try:
        link.symlink_to(
            outside,
            target_is_directory=True,
        )
    except OSError:
        pytest.skip(
            "directory symlinks are not available"
        )

    snapshot = create_snapshot(
        relative_path=(
            "2026/"
            f"{SNAPSHOT_ID}.json"
        ),
        checksum_sha256="a" * 64,
    )

    with pytest.raises(
        ValueError,
        match=(
            "path escapes the archive root"
        ),
    ):
        HistoricalSnapshotIntegrityVerifier(
            archive_root
        ).verify(
            snapshot
        )


def test_resolve_path_accepts_nested_archive_path(
    tmp_path: Path,
) -> None:
    archive_root = tmp_path / "history"
    relative_path = (
        "2026/08/"
        f"{SNAPSHOT_ID}.json"
    )
    snapshot = create_snapshot(
        relative_path=relative_path,
        checksum_sha256="a" * 64,
    )

    resolved = (
        HistoricalSnapshotIntegrityVerifier(
            archive_root
        ).resolve_path(
            snapshot
        )
    )

    assert resolved == (
        archive_root
        / relative_path
    ).resolve()
