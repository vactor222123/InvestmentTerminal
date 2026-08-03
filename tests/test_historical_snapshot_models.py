"""
Tests for canonical historical snapshot models.
"""

from datetime import datetime, timezone
from uuid import UUID

import pytest

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)


SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
SUPERSEDED_ID = (
    "f9b7adca-2f2b-47a4-901d-05ca37c445df"
)
CHECKSUM = "a" * 64


def create_snapshot(
    **overrides: object,
) -> HistoricalSnapshot:
    values: dict[str, object] = {
        "snapshot_id": SNAPSHOT_ID,
        "package_id": "review-20260803-193501",
        "package_schema_version": "1.0",
        "product_version": "0.12.0",
        "generated_at": datetime(
            2026,
            8,
            3,
            17,
            35,
            tzinfo=timezone.utc,
        ),
        "archived_at": datetime(
            2026,
            8,
            3,
            17,
            36,
            tzinfo=timezone.utc,
        ),
        "relative_path": (
            "2026/08/"
            "2026-08-03T17-35-00Z_"
            f"{SNAPSHOT_ID}.json"
        ),
        "checksum_sha256": CHECKSUM,
        "supersedes": None,
        "status": "ARCHIVED",
    }
    values.update(
        overrides
    )

    return HistoricalSnapshot(
        **values,  # type: ignore[arg-type]
    )


def test_snapshot_normalizes_values() -> None:
    snapshot = create_snapshot(
        snapshot_id=SNAPSHOT_ID.upper(),
        checksum_sha256="A" * 64,
        relative_path=(
            "2026\\08\\snapshot.json"
        ),
        status=" verified ",
    )

    assert snapshot.snapshot_id == (
        str(
            UUID(
                SNAPSHOT_ID
            )
        )
    )
    assert snapshot.checksum_sha256 == CHECKSUM
    assert snapshot.relative_path == (
        "2026/08/snapshot.json"
    )
    assert snapshot.status == "VERIFIED"


def test_snapshot_serializes_to_stable_dict() -> None:
    snapshot = create_snapshot(
        supersedes=SUPERSEDED_ID,
    )

    assert snapshot.to_dict() == {
        "snapshot_id": SNAPSHOT_ID,
        "package_id": (
            "review-20260803-193501"
        ),
        "package_schema_version": "1.0",
        "product_version": "0.12.0",
        "generated_at": (
            "2026-08-03T17:35:00+00:00"
        ),
        "archived_at": (
            "2026-08-03T17:36:00+00:00"
        ),
        "relative_path": (
            "2026/08/"
            "2026-08-03T17-35-00Z_"
            f"{SNAPSHOT_ID}.json"
        ),
        "checksum_sha256": CHECKSUM,
        "supersedes": SUPERSEDED_ID,
        "status": "ARCHIVED",
    }


@pytest.mark.parametrize(
    "snapshot_id",
    (
        "",
        "not-a-uuid",
        "123",
    ),
)
def test_snapshot_rejects_invalid_id(
    snapshot_id: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="snapshot_id must be a valid UUID string",
    ):
        create_snapshot(
            snapshot_id=snapshot_id,
        )


def test_snapshot_rejects_naive_generated_at() -> None:
    with pytest.raises(
        ValueError,
        match="generated_at must be timezone-aware",
    ):
        create_snapshot(
            generated_at=datetime(
                2026,
                8,
                3,
                17,
                35,
            ),
        )


def test_snapshot_rejects_archive_time_before_generation() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "archived_at must not be earlier "
            "than generated_at"
        ),
    ):
        create_snapshot(
            archived_at=datetime(
                2026,
                8,
                3,
                17,
                34,
                tzinfo=timezone.utc,
            ),
        )


@pytest.mark.parametrize(
    "relative_path",
    (
        "/absolute/snapshot.json",
        "../outside/snapshot.json",
        "2026/08/snapshot.txt",
        "",
    ),
)
def test_snapshot_rejects_invalid_archive_path(
    relative_path: str,
) -> None:
    with pytest.raises(
        ValueError,
    ):
        create_snapshot(
            relative_path=relative_path,
        )


@pytest.mark.parametrize(
    "checksum",
    (
        "",
        "abc",
        "g" * 64,
        "a" * 63,
        "a" * 65,
    ),
)
def test_snapshot_rejects_invalid_checksum(
    checksum: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "checksum_sha256 must contain "
            "64 hexadecimal characters"
        ),
    ):
        create_snapshot(
            checksum_sha256=checksum,
        )


def test_snapshot_rejects_self_supersession() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "supersedes must not reference snapshot_id"
        ),
    ):
        create_snapshot(
            supersedes=SNAPSHOT_ID,
        )


def test_snapshot_rejects_unknown_status() -> None:
    with pytest.raises(
        ValueError,
        match="status must be one of",
    ):
        create_snapshot(
            status="DELETED",
        )


def test_optional_fields_may_be_none() -> None:
    snapshot = create_snapshot(
        package_id=None,
        product_version=None,
        supersedes=None,
    )

    assert snapshot.package_id is None
    assert snapshot.product_version is None
    assert snapshot.supersedes is None
