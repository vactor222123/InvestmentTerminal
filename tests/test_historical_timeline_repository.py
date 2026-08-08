"""
Tests for HistoricalTimelineRepository.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
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
from investment_terminal.history.historical_timeline_models import (
    HistoricalTimelineEvent,
)
from investment_terminal.history.historical_timeline_repository import (
    HistoricalTimelineRepository,
)


FIRST_SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
SECOND_SNAPSHOT_ID = (
    "f9b7adca-2f2b-47a4-901d-05ca37c445df"
)
BASE_TIME = datetime(
    2026,
    8,
    3,
    17,
    35,
    tzinfo=timezone.utc,
)


def create_snapshot(
    snapshot_id: str,
    *,
    generated_at: datetime,
) -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=snapshot_id,
        package_id=f"review-{snapshot_id[:8]}",
        package_schema_version="1.0",
        product_version="0.12.0",
        generated_at=generated_at,
        archived_at=generated_at + timedelta(
            minutes=1
        ),
        relative_path=(
            f"{generated_at:%Y/%m}/{snapshot_id}.json"
        ),
        checksum_sha256="a" * 64,
        supersedes=None,
        status="ARCHIVED",
    )


def create_repository(
    tmp_path: Path,
) -> tuple[
    HistoricalSQLiteStore,
    HistoricalTimelineRepository,
]:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    snapshot_repository = HistoricalSnapshotRepository(
        store
    )
    snapshot_repository.add_many(
        (
            create_snapshot(
                FIRST_SNAPSHOT_ID,
                generated_at=BASE_TIME,
            ),
            create_snapshot(
                SECOND_SNAPSHOT_ID,
                generated_at=BASE_TIME + timedelta(
                    days=1
                ),
            ),
        )
    )

    return (
        store,
        HistoricalTimelineRepository(
            store
        ),
    )


def insert_event(
    store: HistoricalSQLiteStore,
    *,
    snapshot_id: str = FIRST_SNAPSHOT_ID,
    event_type: str = "HOLDING_RECORDED",
    occurred_at: datetime = BASE_TIME,
    subject_key: str | None = "WORLD",
    payload_json: str = '{"symbol":"WORLD"}',
) -> int:
    with store.connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO timeline_events (
                snapshot_id,
                event_type,
                occurred_at,
                subject_key,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                event_type,
                occurred_at.isoformat(),
                subject_key,
                payload_json,
            ),
        )
        event_id = cursor.lastrowid

    assert event_id is not None
    return int(
        event_id
    )


def test_repository_rejects_invalid_store() -> None:
    with pytest.raises(
        TypeError,
        match="store must be a HistoricalSQLiteStore",
    ):
        HistoricalTimelineRepository(
            object()  # type: ignore[arg-type]
        )


def test_repository_returns_empty_results(
    tmp_path: Path,
) -> None:
    _, repository = create_repository(
        tmp_path
    )

    assert repository.count() == 0
    assert repository.list_for_snapshot(
        FIRST_SNAPSHOT_ID
    ) == ()
    assert repository.find_by_type(
        "HOLDING_RECORDED"
    ) == ()
    assert repository.find_by_subject(
        "WORLD"
    ) == ()
    assert repository.find_between(
        start=BASE_TIME,
        end=BASE_TIME + timedelta(
            days=2
        ),
    ) == ()
    assert repository.latest(
        5
    ) == ()


def test_repository_lists_snapshot_events_as_typed_models(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )
    later_id = insert_event(
        store,
        occurred_at=BASE_TIME + timedelta(
            minutes=10
        ),
        subject_key="LATER",
    )
    earlier_id = insert_event(
        store,
        occurred_at=BASE_TIME,
        subject_key="EARLIER",
    )
    insert_event(
        store,
        snapshot_id=SECOND_SNAPSHOT_ID,
        occurred_at=BASE_TIME + timedelta(
            days=1
        ),
        subject_key="OTHER",
    )

    events = repository.list_for_snapshot(
        FIRST_SNAPSHOT_ID.upper()
    )

    assert all(
        isinstance(
            event,
            HistoricalTimelineEvent,
        )
        for event in events
    )
    assert [
        event.event_id
        for event in events
    ] == [
        earlier_id,
        later_id,
    ]
    assert events[0].payload["symbol"] == "WORLD"


def test_repository_finds_by_normalized_type(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )
    expected_id = insert_event(
        store,
        event_type="HOLDING_RECORDED",
    )
    insert_event(
        store,
        event_type="DEPLOYMENT_RECORDED",
        subject_key="DEPLOY",
    )

    events = repository.find_by_type(
        " holding_recorded "
    )

    assert [
        event.event_id
        for event in events
    ] == [
        expected_id,
    ]


def test_repository_finds_by_subject(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )
    expected_id = insert_event(
        store,
        subject_key="WORLD",
    )
    insert_event(
        store,
        subject_key="EM",
    )

    events = repository.find_by_subject(
        " WORLD "
    )

    assert [
        event.event_id
        for event in events
    ] == [
        expected_id,
    ]


def test_repository_finds_inclusive_time_range(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )
    first_id = insert_event(
        store,
        occurred_at=BASE_TIME,
        subject_key="FIRST",
    )
    second_id = insert_event(
        store,
        occurred_at=BASE_TIME + timedelta(
            hours=1
        ),
        subject_key="SECOND",
    )
    insert_event(
        store,
        occurred_at=BASE_TIME + timedelta(
            hours=2
        ),
        subject_key="THIRD",
    )

    events = repository.find_between(
        start=BASE_TIME,
        end=BASE_TIME + timedelta(
            hours=1
        ),
    )

    assert [
        event.event_id
        for event in events
    ] == [
        first_id,
        second_id,
    ]


def test_repository_latest_returns_newest_first(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )
    first_id = insert_event(
        store,
        occurred_at=BASE_TIME,
        subject_key="FIRST",
    )
    second_id = insert_event(
        store,
        occurred_at=BASE_TIME + timedelta(
            hours=1
        ),
        subject_key="SECOND",
    )
    third_id = insert_event(
        store,
        occurred_at=BASE_TIME + timedelta(
            hours=2
        ),
        subject_key="THIRD",
    )

    events = repository.latest(
        2
    )

    assert [
        event.event_id
        for event in events
    ] == [
        third_id,
        second_id,
    ]
    assert first_id not in {
        event.event_id
        for event in events
    }
    assert repository.count() == 3


@pytest.mark.parametrize(
    "limit",
    (
        0,
        -1,
        True,
        1.5,
        "1",
    ),
)
def test_repository_rejects_invalid_latest_limit(
    tmp_path: Path,
    limit,
) -> None:
    _, repository = create_repository(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match="limit must be a positive integer",
    ):
        repository.latest(
            limit
        )


def test_repository_rejects_invalid_snapshot_id(
    tmp_path: Path,
) -> None:
    _, repository = create_repository(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match="snapshot_id must be a valid UUID string",
    ):
        repository.list_for_snapshot(
            "not-a-uuid"
        )


@pytest.mark.parametrize(
    ("method_name", "value", "message"),
    (
        (
            "find_by_type",
            "   ",
            "event_type must be a non-empty string",
        ),
        (
            "find_by_subject",
            "",
            "subject_key must be a non-empty string",
        ),
    ),
)
def test_repository_rejects_blank_filters(
    tmp_path: Path,
    method_name: str,
    value: str,
    message: str,
) -> None:
    _, repository = create_repository(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match=message,
    ):
        getattr(
            repository,
            method_name,
        )(
            value
        )


def test_repository_rejects_naive_range(
    tmp_path: Path,
) -> None:
    _, repository = create_repository(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match="start must be timezone-aware",
    ):
        repository.find_between(
            start=datetime(
                2026,
                8,
                3,
                17,
                35,
            ),
            end=BASE_TIME,
        )


def test_repository_rejects_reverse_range(
    tmp_path: Path,
) -> None:
    _, repository = create_repository(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match="end must not be earlier than start",
    ):
        repository.find_between(
            start=BASE_TIME + timedelta(
                hours=1
            ),
            end=BASE_TIME,
        )


def test_repository_rejects_invalid_persisted_json(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )
    insert_event(
        store,
        payload_json="{invalid",
    )

    with pytest.raises(
        ValueError,
        match="timeline payload_json must contain valid JSON",
    ):
        repository.latest(
            1
        )


def test_repository_rejects_non_object_persisted_json(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )
    insert_event(
        store,
        payload_json='["not","object"]',
    )

    with pytest.raises(
        ValueError,
        match=(
            "timeline payload_json must contain a JSON object"
        ),
    ):
        repository.latest(
            1
        )


def test_repository_exposes_invalid_persisted_timestamp(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )

    with store.connect() as connection:
        connection.execute(
            """
            INSERT INTO timeline_events (
                snapshot_id,
                event_type,
                occurred_at,
                subject_key,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                FIRST_SNAPSHOT_ID,
                "HOLDING_RECORDED",
                "not-a-datetime",
                "WORLD",
                '{"symbol":"WORLD"}',
            ),
        )

    with pytest.raises(
        ValueError,
    ):
        repository.latest(
            1
        )
