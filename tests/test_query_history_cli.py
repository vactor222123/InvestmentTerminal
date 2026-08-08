"""
Tests for the read-only History query CLI.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_terminal.cli.query_history import (
    main,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_schema_migrations import (
    HISTORICAL_SCHEMA_MIGRATIONS,
    HISTORICAL_SCHEMA_TARGET_VERSION,
    HistoricalSchemaMigrator,
)
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
    package_id: str,
) -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=snapshot_id,
        package_id=package_id,
        package_schema_version="1.0",
        product_version="0.13.0",
        generated_at=generated_at,
        archived_at=generated_at + timedelta(
            minutes=1
        ),
        relative_path=f"2026/08/{snapshot_id}.json",
        checksum_sha256="a" * 64,
        status="ARCHIVED",
    )


def prepare_database(
    tmp_path: Path,
) -> Path:
    database = tmp_path / "history.db"
    store = HistoricalSQLiteStore(
        database
    )
    snapshots = HistoricalSnapshotRepository(
        store
    )

    first = create_snapshot(
        FIRST_ID,
        generated_at=BASE_TIME,
        package_id="review-a",
    )
    second = create_snapshot(
        SECOND_ID,
        generated_at=BASE_TIME + timedelta(
            days=1
        ),
        package_id="review-b",
    )
    snapshots.add_many(
        (
            first,
            second,
        )
    )

    HistoricalSchemaMigrator(
        store=store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()

    states = HistoricalImportStateRepository(
        store
    )
    states.initialize_metadata(
        first,
        at=BASE_TIME + timedelta(
            days=2
        ),
    )
    states.initialize_legacy_imported(
        second,
        at=BASE_TIME + timedelta(
            days=2
        ),
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
                FIRST_ID,
                "SNAPSHOT_ARCHIVED",
                BASE_TIME.isoformat(),
                "portfolio",
                "{}",
            ),
        )
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
                SECOND_ID,
                "RECOMMENDATION_RECORDED",
                (
                    BASE_TIME
                    + timedelta(
                        days=1
                    )
                ).isoformat(),
                "BABA",
                '{"action":"BUY"}',
            ),
        )

    return database


def test_snapshots_json_lists_chronologically(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = prepare_database(
        tmp_path
    )

    main(
        [
            "--database",
            str(
                database
            ),
            "--json",
            "snapshots",
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report[
        "count"
    ] == 2
    assert [
        item[
            "snapshot_id"
        ]
        for item in report[
            "snapshots"
        ]
    ] == [
        FIRST_ID,
        SECOND_ID,
    ]


def test_snapshots_package_filter(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = prepare_database(
        tmp_path
    )

    main(
        [
            "--database",
            str(
                database
            ),
            "--json",
            "snapshots",
            "--package-id",
            "review-b",
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report[
        "count"
    ] == 1
    assert report[
        "snapshots"
    ][0][
        "snapshot_id"
    ] == SECOND_ID


def test_snapshots_date_filter_requires_aware_bounds(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = prepare_database(
        tmp_path
    )

    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--database",
                str(
                    database
                ),
                "snapshots",
                "--start",
                "2026-08-03T00:00:00",
                "--end",
                "2026-08-04T00:00:00+00:00",
            ]
        )

    assert exc.value.code == 2
    assert (
        "timezone offset"
        in capsys.readouterr().err
    )


def test_timeline_filters_by_snapshot(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = prepare_database(
        tmp_path
    )

    main(
        [
            "--database",
            str(
                database
            ),
            "--json",
            "timeline",
            "--snapshot-id",
            SECOND_ID,
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report[
        "count"
    ] == 1
    assert report[
        "events"
    ][0][
        "event_type"
    ] == "RECOMMENDATION_RECORDED"


def test_timeline_rejects_multiple_filter_modes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = prepare_database(
        tmp_path
    )

    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--database",
                str(
                    database
                ),
                "timeline",
                "--snapshot-id",
                FIRST_ID,
                "--event-type",
                "SNAPSHOT_ARCHIVED",
            ]
        )

    assert exc.value.code == 2
    assert (
        "only one filter mode"
        in capsys.readouterr().err
    )


def test_show_json_includes_state_navigation_and_timeline(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = prepare_database(
        tmp_path
    )

    main(
        [
            "--database",
            str(
                database
            ),
            "--json",
            "show",
            "--snapshot-id",
            FIRST_ID,
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report[
        "snapshot"
    ][
        "snapshot_id"
    ] == FIRST_ID
    assert report[
        "import_state"
    ][
        "status"
    ] == "METADATA_ONLY"
    assert report[
        "previous_snapshot_id"
    ] is None
    assert report[
        "next_snapshot_id"
    ] == SECOND_ID
    assert len(
        report[
            "timeline_events"
        ]
    ) == 1


def test_human_output_is_readable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = prepare_database(
        tmp_path
    )

    main(
        [
            "--database",
            str(
                database
            ),
            "show",
            "--snapshot-id",
            SECOND_ID,
        ]
    )

    output = capsys.readouterr().out

    assert f"Snapshot: {SECOND_ID}" in output
    assert "Import state: IMPORTED" in output
    assert f"Previous: {FIRST_ID}" in output


def test_missing_database_is_actionable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing.db"

    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--database",
                str(
                    missing
                ),
                "snapshots",
            ]
        )

    assert exc.value.code == 2
    assert (
        "History database does not exist"
        in capsys.readouterr().err
    )
    assert not missing.exists()


def test_unknown_snapshot_is_actionable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = prepare_database(
        tmp_path
    )

    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--database",
                str(
                    database
                ),
                "show",
                "--snapshot-id",
                (
                    "7a5dc1c4-9d9a-4c17-a63c-1f8bb35e2199"
                ),
            ]
        )

    assert exc.value.code == 2
    assert (
        "No historical snapshot found"
        in capsys.readouterr().err
    )
