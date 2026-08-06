"""
Failure-path tests for the append-only historical snapshot manifest.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)


FIRST_ID = "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
SECOND_ID = "f9b7adca-2f2b-47a4-901d-05ca37c445df"


def create_snapshot(
    snapshot_id: str,
) -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=snapshot_id,
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
            17,
            36,
            tzinfo=timezone.utc,
        ),
        relative_path=(
            f"2026/08/{snapshot_id}.json"
        ),
        checksum_sha256="a" * 64,
        supersedes=None,
        status="ARCHIVED",
    )


def test_failed_sync_restores_existing_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )
    first = create_snapshot(
        FIRST_ID
    )
    second = create_snapshot(
        SECOND_ID
    )
    manifest.append(
        first
    )
    original_bytes = (
        manifest.manifest_path.read_bytes()
    )
    calls = 0

    def fail_first_sync(
        file_descriptor: int,
    ) -> None:
        nonlocal calls
        calls += 1

        if calls == 1:
            raise OSError(
                "sync failed"
            )

    monkeypatch.setattr(
        "investment_terminal.history."
        "historical_snapshot_manifest.os.fsync",
        fail_first_sync,
    )

    with pytest.raises(
        OSError,
        match="sync failed",
    ):
        manifest.append(
            second
        )

    assert (
        manifest.manifest_path.read_bytes()
        == original_bytes
    )
    assert manifest.load_all() == (
        first,
    )


def test_failed_first_append_removes_empty_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )
    calls = 0

    def fail_first_sync(
        file_descriptor: int,
    ) -> None:
        nonlocal calls
        calls += 1

        if calls == 1:
            raise OSError(
                "sync failed"
            )

    monkeypatch.setattr(
        "investment_terminal.history."
        "historical_snapshot_manifest.os.fsync",
        fail_first_sync,
    )

    with pytest.raises(
        OSError,
        match="sync failed",
    ):
        manifest.append(
            create_snapshot(
                FIRST_ID
            )
        )

    assert not manifest.manifest_path.exists()
    assert manifest.load_all() == ()
