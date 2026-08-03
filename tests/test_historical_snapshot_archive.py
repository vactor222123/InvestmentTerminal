"""
Tests for immutable historical snapshot archiving.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from investment_terminal.history.historical_snapshot_archive import (
    HistoricalSnapshotArchive,
)


SNAPSHOT_ID = UUID(
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
ARCHIVED_AT = datetime(
    2026,
    8,
    3,
    18,
    0,
    tzinfo=timezone.utc,
)


def write_package(
    path: Path,
    *,
    generated_at: str = (
        "2026-08-03T17:35:00+00:00"
    ),
    schema_version: str = "1.0",
    package_id: str | None = None,
) -> bytes:
    payload: dict[str, object] = {
        "schema_version": schema_version,
        "generated_at": generated_at,
        "portfolio_name": "Test Portfolio",
        "warnings": [],
        "sections": {},
    }

    if package_id is not None:
        payload[
            "package_id"
        ] = package_id

    package_bytes = (
        json.dumps(
            payload,
            indent=2,
        )
        + "\n"
    ).encode(
        "utf-8"
    )
    path.write_bytes(
        package_bytes
    )

    return package_bytes


def create_archive(
    root: Path,
) -> HistoricalSnapshotArchive:
    return HistoricalSnapshotArchive(
        root,
        clock=lambda: ARCHIVED_AT,
        uuid_factory=lambda: SNAPSHOT_ID,
    )


def test_archive_preserves_exact_package_bytes(
    tmp_path: Path,
) -> None:
    source = (
        tmp_path
        / "investment_review_package.json"
    )
    package_bytes = write_package(
        source,
        package_id="review-001",
    )
    archive_root = (
        tmp_path
        / "history"
    )

    snapshot = create_archive(
        archive_root
    ).archive(
        source,
        product_version="0.12.0",
    )

    archived_path = (
        archive_root
        / snapshot.relative_path
    )

    assert archived_path.read_bytes() == (
        package_bytes
    )
    assert snapshot.snapshot_id == str(
        SNAPSHOT_ID
    )
    assert snapshot.package_id == "review-001"
    assert snapshot.package_schema_version == "1.0"
    assert snapshot.product_version == "0.12.0"
    assert snapshot.generated_at == datetime(
        2026,
        8,
        3,
        17,
        35,
        tzinfo=timezone.utc,
    )
    assert snapshot.archived_at == ARCHIVED_AT
    assert snapshot.relative_path == (
        "2026/08/"
        "2026-08-03T17-35-00Z_"
        f"{SNAPSHOT_ID}.json"
    )
    assert snapshot.checksum_sha256 == (
        hashlib.sha256(
            package_bytes
        ).hexdigest()
    )


def test_archive_accepts_zulu_timestamp(
    tmp_path: Path,
) -> None:
    source = tmp_path / "review.json"
    write_package(
        source,
        generated_at=(
            "2026-08-03T17:35:00Z"
        ),
    )

    snapshot = create_archive(
        tmp_path / "history"
    ).archive(
        source
    )

    assert snapshot.generated_at == datetime(
        2026,
        8,
        3,
        17,
        35,
        tzinfo=timezone.utc,
    )


def test_explicit_package_id_overrides_payload(
    tmp_path: Path,
) -> None:
    source = tmp_path / "review.json"
    write_package(
        source,
        package_id="payload-id",
    )

    snapshot = create_archive(
        tmp_path / "history"
    ).archive(
        source,
        package_id="explicit-id",
    )

    assert snapshot.package_id == "explicit-id"


def test_archive_does_not_overwrite_existing_snapshot(
    tmp_path: Path,
) -> None:
    source = tmp_path / "review.json"
    write_package(
        source
    )
    archive = create_archive(
        tmp_path / "history"
    )

    archive.archive(
        source
    )

    with pytest.raises(
        FileExistsError,
        match=(
            "Historical snapshot already exists"
        ),
    ):
        archive.archive(
            source
        )


def test_archive_rejects_missing_source(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="Review package does not exist",
    ):
        create_archive(
            tmp_path / "history"
        ).archive(
            tmp_path / "missing.json"
        )


def test_archive_rejects_non_json_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / "review.txt"
    source.write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=(
            "source_path must point to a JSON file"
        ),
    ):
        create_archive(
            tmp_path / "history"
        ).archive(
            source
        )


def test_archive_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    source = tmp_path / "review.json"
    source.write_text(
        "{invalid",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=(
            "Review package must contain valid JSON"
        ),
    ):
        create_archive(
            tmp_path / "history"
        ).archive(
            source
        )


@pytest.mark.parametrize(
    "missing_field",
    (
        "schema_version",
        "generated_at",
    ),
)
def test_archive_requires_package_metadata(
    tmp_path: Path,
    missing_field: str,
) -> None:
    source = tmp_path / "review.json"
    payload = {
        "schema_version": "1.0",
        "generated_at": (
            "2026-08-03T17:35:00+00:00"
        ),
    }
    del payload[
        missing_field
    ]
    source.write_text(
        json.dumps(
            payload
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=(
            f"{missing_field} must be "
            "a non-empty string"
        ),
    ):
        create_archive(
            tmp_path / "history"
        ).archive(
            source
        )


def test_archive_rejects_naive_generated_at(
    tmp_path: Path,
) -> None:
    source = tmp_path / "review.json"
    write_package(
        source,
        generated_at=(
            "2026-08-03T17:35:00"
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "generated_at must be timezone-aware"
        ),
    ):
        create_archive(
            tmp_path / "history"
        ).archive(
            source
        )


def test_archive_rejects_naive_clock(
    tmp_path: Path,
) -> None:
    source = tmp_path / "review.json"
    write_package(
        source
    )
    archive = HistoricalSnapshotArchive(
        tmp_path / "history",
        clock=lambda: datetime(
            2026,
            8,
            3,
            18,
            0,
        ),
        uuid_factory=lambda: SNAPSHOT_ID,
    )

    with pytest.raises(
        ValueError,
        match=(
            "archived_at must be timezone-aware"
        ),
    ):
        archive.archive(
            source
        )
