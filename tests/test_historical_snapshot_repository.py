"""
Tests for HistoricalSnapshotRepository.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


FIRST_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
SECOND_ID = (
    "f9b7adca-2f2b-47a4-901d-05ca37c445df"
)
THIRD_ID = (
    "7a5dc1c4-9d9a-4c17-a63c-1f8bb35e2199"
)


def create_snapshot(
    *,
    snapshot_id: str = FIRST_ID,
    package_id: str | None = "review-001",
    generated_at: datetime | None = None,
    archived_at: datetime | None = None,
    relative_path: str | None = None,
    supersedes: str | None = None,
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
            or f"{generated:%Y/%m}/{snapshot_id}.json"
        ),
        checksum_sha256="a" * 64,
        supersedes=supersedes,
        status="ARCHIVED",
    )


def create_repository(
    tmp_path: Path,
) -> HistoricalSnapshotRepository:
    return HistoricalSnapshotRepository(
        HistoricalSQLiteStore(
            tmp_path / "history.db"
        )
    )


def test_repository_adds_and_gets_snapshot(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
    )
    snapshot = create_snapshot()

    assert repository.add(
        snapshot
    ) == snapshot
    assert repository.get(
        FIRST_ID
    ) == snapshot
    assert repository.require(
        FIRST_ID.upper()
    ) == snapshot
    assert repository.exists(
        FIRST_ID
    )
    assert repository.count() == 1


def test_repository_returns_none_for_missing_snapshot(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
    )

    assert repository.get(
        FIRST_ID
    ) is None
    assert not repository.exists(
        FIRST_ID
    )

    with pytest.raises(
        KeyError,
        match="No historical snapshot found",
    ):
        repository.require(
            FIRST_ID
        )


def test_repository_rejects_duplicate_snapshot(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
    )
    snapshot = create_snapshot()

    repository.add(
        snapshot
    )

    with pytest.raises(
        ValueError,
        match="Historical snapshot already exists",
    ):
        repository.add(
            snapshot
        )

    assert repository.count() == 1


def test_repository_add_many_is_atomic(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
    )
    first = create_snapshot()
    duplicate_path = create_snapshot(
        snapshot_id=SECOND_ID,
        relative_path=first.relative_path,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Historical snapshot batch could not be inserted"
        ),
    ):
        repository.add_many(
            (
                first,
                duplicate_path,
            )
        )

    assert repository.count() == 0


def test_repository_add_many_accepts_empty_input(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
    )

    assert repository.add_many(
        ()
    ) == ()
    assert repository.count() == 0


def test_repository_lists_all_in_chronological_order(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
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

    repository.add_many(
        (
            second,
            first,
        )
    )

    assert repository.list_all() == (
        first,
        second,
    )


def test_repository_list_all_returns_empty_tuple(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
    )

    assert repository.list_all() == ()


def test_repository_reports_detail_import_state(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
    )
    snapshot = create_snapshot()
    repository.add(
        snapshot
    )

    assert not repository.has_detail_import(
        snapshot.snapshot_id
    )

    with repository.store.connect() as connection:
        connection.execute(
            """
            INSERT INTO portfolio_summary (
                snapshot_id
            )
            VALUES (?)
            """,
            (
                snapshot.snapshot_id,
            ),
        )

    assert repository.has_detail_import(
        snapshot.snapshot_id
    )


def test_repository_finds_package_history(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
    )
    first = create_snapshot(
        package_id="shared",
    )
    second = create_snapshot(
        snapshot_id=SECOND_ID,
        package_id="shared",
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

    repository.add_many(
        (
            second,
            first,
        )
    )

    assert repository.find_by_package_id(
        "shared"
    ) == (
        first,
        second,
    )


def test_repository_finds_generated_range(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
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

    repository.add_many(
        (
            first,
            second,
        )
    )

    assert repository.find_generated_between(
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


def test_repository_latest_returns_latest_generated(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
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

    repository.add_many(
        (
            first,
            second,
        )
    )

    assert repository.latest() == second


def test_repository_latest_is_none_when_empty(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
    )

    assert repository.latest() is None


def test_repository_navigates_previous_and_next(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
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
    third = create_snapshot(
        snapshot_id=THIRD_ID,
        package_id="review-003",
        generated_at=datetime(
            2026,
            8,
            5,
            17,
            35,
            tzinfo=timezone.utc,
        ),
        archived_at=datetime(
            2026,
            8,
            5,
            17,
            36,
            tzinfo=timezone.utc,
        ),
    )

    repository.add_many(
        (
            third,
            first,
            second,
        )
    )

    assert repository.previous_before(
        second.snapshot_id
    ) == first
    assert repository.next_after(
        second.snapshot_id
    ) == third
    assert repository.previous_before(
        first.snapshot_id
    ) is None
    assert repository.next_after(
        third.snapshot_id
    ) is None


def test_repository_navigation_uses_full_canonical_order(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
    )
    generated = datetime(
        2026,
        8,
        3,
        17,
        35,
        tzinfo=timezone.utc,
    )
    archived = datetime(
        2026,
        8,
        3,
        17,
        36,
        tzinfo=timezone.utc,
    )

    first = create_snapshot(
        snapshot_id=FIRST_ID,
        package_id="review-001",
        generated_at=generated,
        archived_at=archived,
    )
    second = create_snapshot(
        snapshot_id=THIRD_ID,
        package_id="review-002",
        generated_at=generated,
        archived_at=archived,
    )
    third = create_snapshot(
        snapshot_id=SECOND_ID,
        package_id="review-003",
        generated_at=generated,
        archived_at=datetime(
            2026,
            8,
            3,
            17,
            37,
            tzinfo=timezone.utc,
        ),
    )

    repository.add_many(
        (
            third,
            second,
            first,
        )
    )

    ordered = repository.list_all()

    assert ordered == (
        first,
        second,
        third,
    )
    assert repository.next_after(
        first.snapshot_id
    ) == second
    assert repository.previous_before(
        second.snapshot_id
    ) == first
    assert repository.next_after(
        second.snapshot_id
    ) == third
    assert repository.previous_before(
        third.snapshot_id
    ) == second


@pytest.mark.parametrize(
    "method_name",
    (
        "previous_before",
        "next_after",
    ),
)
def test_repository_navigation_rejects_missing_snapshot(
    tmp_path: Path,
    method_name: str,
) -> None:
    repository = create_repository(
        tmp_path
    )

    with pytest.raises(
        KeyError,
        match="No historical snapshot found",
    ):
        getattr(
            repository,
            method_name,
        )(
            FIRST_ID
        )


def test_repository_rejects_invalid_store() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "store must be a HistoricalSQLiteStore"
        ),
    ):
        HistoricalSnapshotRepository(
            object()  # type: ignore[arg-type]
        )


def test_generated_range_rejects_naive_datetime(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match="start must be timezone-aware",
    ):
        repository.find_generated_between(
            start=datetime(
                2026,
                8,
                1,
            ),
            end=datetime(
                2026,
                8,
                5,
                tzinfo=timezone.utc,
            ),
        )


def test_generated_range_rejects_reverse_bounds(
    tmp_path: Path,
) -> None:
    repository = create_repository(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match="end must not be earlier than start",
    ):
        repository.find_generated_between(
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
