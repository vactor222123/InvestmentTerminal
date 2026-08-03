"""
Tests for the append-only historical snapshot manifest.
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


FIRST_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
SECOND_ID = (
    "f9b7adca-2f2b-47a4-901d-05ca37c445df"
)


def create_snapshot(
    *,
    snapshot_id: str = FIRST_ID,
    package_id: str | None = "review-001",
    generated_at: datetime | None = None,
    archived_at: datetime | None = None,
    relative_path: str | None = None,
) -> HistoricalSnapshot:
    generated = generated_at or datetime(
        2026,
        8,
        3,
        17,
        35,
        tzinfo=timezone.utc,
    )
    archived = archived_at or datetime(
        2026,
        8,
        3,
        17,
        36,
        tzinfo=timezone.utc,
    )

    return HistoricalSnapshot(
        snapshot_id=snapshot_id,
        package_id=package_id,
        package_schema_version="1.0",
        product_version="0.12.0",
        generated_at=generated,
        archived_at=archived,
        relative_path=(
            relative_path
            or (
                f"{generated:%Y/%m}/"
                f"{snapshot_id}.json"
            )
        ),
        checksum_sha256="a" * 64,
        supersedes=None,
        status="ARCHIVED",
    )


def test_manifest_append_and_load(
    tmp_path: Path,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path
        / "history"
        / "manifest.jsonl"
    )
    first = create_snapshot()
    second = create_snapshot(
        snapshot_id=SECOND_ID,
        package_id="review-002",
        generated_at=datetime(
            2026,
            8,
            4,
            17,
            35,
            tzinfo=timezone.utc,
        ),
        archived_at=datetime(
            2026,
            8,
            4,
            17,
            36,
            tzinfo=timezone.utc,
        ),
    )

    manifest.append(
        first
    )
    manifest.append(
        second
    )

    assert manifest.load_all() == (
        first,
        second,
    )
    assert (
        manifest.manifest_path.read_text(
            encoding="utf-8"
        ).count(
            "\n"
        )
        == 2
    )


def test_manifest_loads_missing_file_as_empty(
    tmp_path: Path,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )

    assert manifest.load_all() == ()
    assert manifest.latest() is None


def test_manifest_rejects_duplicate_snapshot_id(
    tmp_path: Path,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )
    first = create_snapshot()
    duplicate = create_snapshot(
        relative_path=(
            "2026/08/other.json"
        ),
    )

    manifest.append(
        first
    )

    with pytest.raises(
        ValueError,
        match=(
            "manifest already contains snapshot_id"
        ),
    ):
        manifest.append(
            duplicate
        )


def test_manifest_rejects_duplicate_relative_path(
    tmp_path: Path,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )
    first = create_snapshot()
    duplicate = create_snapshot(
        snapshot_id=SECOND_ID,
        relative_path=first.relative_path,
    )

    manifest.append(
        first
    )

    with pytest.raises(
        ValueError,
        match=(
            "manifest already contains relative_path"
        ),
    ):
        manifest.append(
            duplicate
        )


def test_manifest_searches_by_snapshot_id(
    tmp_path: Path,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )
    snapshot = create_snapshot()
    manifest.append(
        snapshot
    )

    assert (
        manifest.require_by_snapshot_id(
            FIRST_ID.upper()
        )
        == snapshot
    )

    with pytest.raises(
        KeyError,
        match=(
            "No historical snapshot found"
        ),
    ):
        manifest.require_by_snapshot_id(
            SECOND_ID
        )


def test_manifest_finds_by_package_id(
    tmp_path: Path,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )
    first = create_snapshot(
        package_id="shared-package",
    )
    second = create_snapshot(
        snapshot_id=SECOND_ID,
        package_id="shared-package",
        generated_at=datetime(
            2026,
            8,
            4,
            17,
            35,
            tzinfo=timezone.utc,
        ),
        archived_at=datetime(
            2026,
            8,
            4,
            17,
            36,
            tzinfo=timezone.utc,
        ),
    )
    manifest.append(
        first
    )
    manifest.append(
        second
    )

    assert manifest.find_by_package_id(
        "shared-package"
    ) == (
        first,
        second,
    )


def test_manifest_finds_by_relative_path(
    tmp_path: Path,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )
    snapshot = create_snapshot()
    manifest.append(
        snapshot
    )

    assert manifest.find_by_relative_path(
        snapshot.relative_path.replace(
            "/",
            "\\",
        )
    ) == snapshot
    assert manifest.find_by_relative_path(
        "2026/08/missing.json"
    ) is None


def test_manifest_finds_generated_range(
    tmp_path: Path,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )
    first = create_snapshot()
    second = create_snapshot(
        snapshot_id=SECOND_ID,
        package_id="review-002",
        generated_at=datetime(
            2026,
            8,
            10,
            17,
            35,
            tzinfo=timezone.utc,
        ),
        archived_at=datetime(
            2026,
            8,
            10,
            17,
            36,
            tzinfo=timezone.utc,
        ),
    )
    manifest.append(
        first
    )
    manifest.append(
        second
    )

    assert manifest.find_generated_between(
        start=datetime(
            2026,
            8,
            1,
            tzinfo=timezone.utc,
        ),
        end=datetime(
            2026,
            8,
            5,
            tzinfo=timezone.utc,
        ),
    ) == (
        first,
    )


def test_manifest_latest_uses_generation_time(
    tmp_path: Path,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )
    first = create_snapshot()
    second = create_snapshot(
        snapshot_id=SECOND_ID,
        package_id="review-002",
        generated_at=datetime(
            2026,
            8,
            4,
            17,
            35,
            tzinfo=timezone.utc,
        ),
        archived_at=datetime(
            2026,
            8,
            4,
            17,
            36,
            tzinfo=timezone.utc,
        ),
    )
    manifest.append(
        first
    )
    manifest.append(
        second
    )

    assert manifest.latest() == second


def test_manifest_rejects_invalid_json_line(
    tmp_path: Path,
) -> None:
    path = tmp_path / "manifest.jsonl"
    path.write_text(
        "{invalid}\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=(
            "Invalid historical manifest JSON "
            "on line 1"
        ),
    ):
        HistoricalSnapshotManifest(
            path
        ).load_all()


def test_manifest_rejects_invalid_extension(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "manifest_path must use .jsonl or .ndjson"
        ),
    ):
        HistoricalSnapshotManifest(
            tmp_path / "manifest.json"
        )


def test_generated_range_rejects_invalid_bounds(
    tmp_path: Path,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )

    with pytest.raises(
        ValueError,
        match=(
            "end must not be earlier than start"
        ),
    ):
        manifest.find_generated_between(
            start=datetime(
                2026,
                8,
                5,
                tzinfo=timezone.utc,
            ),
            end=datetime(
                2026,
                8,
                1,
                tzinfo=timezone.utc,
            ),
        )
