"""
Tests for verified archived Review Package loading.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_review_package_loader import (
    HistoricalReviewPackageLoader,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)


SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
GENERATED_AT = datetime(
    2026,
    8,
    3,
    17,
    35,
    tzinfo=timezone.utc,
)
ARCHIVED_AT = datetime(
    2026,
    8,
    3,
    17,
    36,
    tzinfo=timezone.utc,
)
RELATIVE_PATH = (
    "2026/08/review.json"
)


def write_package(
    archive_root: Path,
    *,
    payload: object | None = None,
) -> tuple[Path, bytes]:
    package_payload = (
        payload
        if payload is not None
        else {
            "schema_version": "1.0",
            "generated_at": (
                "2026-08-03T17:35:00+00:00"
            ),
            "portfolio_name": "Test Portfolio",
            "warnings": [],
            "sections": {},
        }
    )
    package_bytes = (
        json.dumps(
            package_payload,
            indent=2,
        )
        + "\n"
    ).encode(
        "utf-8"
    )
    path = (
        archive_root
        / RELATIVE_PATH
    )
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_bytes(
        package_bytes
    )

    return path, package_bytes


def create_snapshot(
    *,
    checksum: str,
    relative_path: str = RELATIVE_PATH,
    schema_version: str = "1.0",
    generated_at: datetime = GENERATED_AT,
    archived_at: datetime = ARCHIVED_AT,
) -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=SNAPSHOT_ID,
        package_id="review-001",
        package_schema_version=schema_version,
        product_version="0.12.0",
        generated_at=generated_at,
        archived_at=archived_at,
        relative_path=relative_path,
        checksum_sha256=checksum,
        supersedes=None,
        status="ARCHIVED",
    )


def test_loader_returns_verified_payload(
    tmp_path: Path,
) -> None:
    archive_root = tmp_path / "history"
    _, package_bytes = write_package(
        archive_root
    )
    snapshot = create_snapshot(
        checksum=hashlib.sha256(
            package_bytes
        ).hexdigest()
    )

    payload = HistoricalReviewPackageLoader(
        archive_root
    ).load(
        snapshot
    )

    assert payload[
        "schema_version"
    ] == "1.0"
    assert payload[
        "portfolio_name"
    ] == "Test Portfolio"


def test_loader_rejects_changed_archive_bytes(
    tmp_path: Path,
) -> None:
    archive_root = tmp_path / "history"
    path, package_bytes = write_package(
        archive_root
    )
    snapshot = create_snapshot(
        checksum=hashlib.sha256(
            package_bytes
        ).hexdigest()
    )
    path.write_text(
        '{"changed": true}\n',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="checksum does not match",
    ):
        HistoricalReviewPackageLoader(
            archive_root
        ).load(
            snapshot
        )


def test_loader_rejects_missing_archive_file(
    tmp_path: Path,
) -> None:
    snapshot = create_snapshot(
        checksum="a" * 64
    )

    with pytest.raises(
        FileNotFoundError,
        match=(
            "Archived Review Package does not exist"
        ),
    ):
        HistoricalReviewPackageLoader(
            tmp_path / "history"
        ).load(
            snapshot
        )


def test_loader_rejects_schema_mismatch(
    tmp_path: Path,
) -> None:
    archive_root = tmp_path / "history"
    _, package_bytes = write_package(
        archive_root
    )
    snapshot = create_snapshot(
        checksum=hashlib.sha256(
            package_bytes
        ).hexdigest(),
        schema_version="2.0",
    )

    with pytest.raises(
        ValueError,
        match="schema_version does not match",
    ):
        HistoricalReviewPackageLoader(
            archive_root
        ).load(
            snapshot
        )


def test_loader_rejects_generated_at_mismatch(
    tmp_path: Path,
) -> None:
    archive_root = tmp_path / "history"
    _, package_bytes = write_package(
        archive_root
    )
    snapshot = create_snapshot(
        checksum=hashlib.sha256(
            package_bytes
        ).hexdigest(),
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

    with pytest.raises(
        ValueError,
        match="generated_at does not match",
    ):
        HistoricalReviewPackageLoader(
            archive_root
        ).load(
            snapshot
        )


def test_loader_rejects_non_object_json(
    tmp_path: Path,
) -> None:
    archive_root = tmp_path / "history"
    _, package_bytes = write_package(
        archive_root,
        payload=[],
    )
    snapshot = create_snapshot(
        checksum=hashlib.sha256(
            package_bytes
        ).hexdigest()
    )

    with pytest.raises(
        ValueError,
        match="JSON must contain an object",
    ):
        HistoricalReviewPackageLoader(
            archive_root
        ).load(
            snapshot
        )


def test_loader_rejects_invalid_json_after_valid_checksum(
    tmp_path: Path,
) -> None:
    archive_root = tmp_path / "history"
    path = archive_root / RELATIVE_PATH
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    package_bytes = b"{invalid}\n"
    path.write_bytes(
        package_bytes
    )
    snapshot = create_snapshot(
        checksum=hashlib.sha256(
            package_bytes
        ).hexdigest()
    )

    with pytest.raises(
        ValueError,
        match="must contain valid JSON",
    ):
        HistoricalReviewPackageLoader(
            archive_root
        ).load(
            snapshot
        )


def test_loader_rejects_invalid_dependency() -> None:
    loader = HistoricalReviewPackageLoader(
        "history"
    )

    with pytest.raises(
        TypeError,
        match=(
            "snapshot must be a HistoricalSnapshot"
        ),
    ):
        loader.load(
            object()  # type: ignore[arg-type]
        )
