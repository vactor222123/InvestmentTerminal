"""
Tests for the historical snapshot comparison CLI.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_terminal.cli.compare_history import (
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


def snapshot(
    snapshot_id: str,
    *,
    generated_at: datetime,
) -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=snapshot_id,
        package_id=f"review-{snapshot_id[:8]}",
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
    *,
    second_portfolio_name: str = "Main",
    second_source_status: str = "COST_BASIS_ONLY",
) -> Path:
    database = tmp_path / "history.db"
    store = HistoricalSQLiteStore(
        database
    )
    snapshots = HistoricalSnapshotRepository(
        store
    )
    first = snapshot(
        FIRST_ID,
        generated_at=BASE_TIME,
    )
    second = snapshot(
        SECOND_ID,
        generated_at=BASE_TIME + timedelta(
            days=1
        ),
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
    for item in (
        first,
        second,
    ):
        states.initialize_legacy_imported(
            item,
            at=BASE_TIME + timedelta(
                days=2
            ),
        )

    with store.connect() as connection:
        connection.execute(
            """
            INSERT INTO portfolio_summary (
                snapshot_id,
                portfolio_name,
                base_currency,
                total_value,
                invested_value,
                cash_value,
                monthly_contribution,
                source_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                FIRST_ID,
                "Main",
                "EUR",
                10000.0,
                9000.0,
                1000.0,
                500.0,
                "COST_BASIS_ONLY",
            ),
        )
        connection.execute(
            """
            INSERT INTO portfolio_summary (
                snapshot_id,
                portfolio_name,
                base_currency,
                total_value,
                invested_value,
                cash_value,
                monthly_contribution,
                source_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SECOND_ID,
                second_portfolio_name,
                "EUR",
                12000.0,
                10000.0,
                2000.0,
                500.0,
                second_source_status,
            ),
        )
        connection.execute(
            """
            INSERT INTO holdings (
                snapshot_id,
                holding_key,
                symbol,
                name,
                asset_type,
                sleeve,
                currency,
                quantity,
                unit_price,
                market_value,
                weight
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                FIRST_ID,
                "WORLD",
                "WORLD",
                "World ETF",
                "ETF",
                "CORE",
                "EUR",
                10.0,
                100.0,
                1000.0,
                0.1,
            ),
        )
        connection.execute(
            """
            INSERT INTO holdings (
                snapshot_id,
                holding_key,
                symbol,
                name,
                asset_type,
                sleeve,
                currency,
                quantity,
                unit_price,
                market_value,
                weight
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SECOND_ID,
                "WORLD",
                "WORLD",
                "World ETF",
                "ETF",
                "CORE",
                "EUR",
                12.0,
                100.0,
                1200.0,
                0.1,
            ),
        )
        for snapshot_id in (
            FIRST_ID,
            SECOND_ID,
        ):
            connection.execute(
                """
                INSERT INTO timeline_events (
                    snapshot_id,
                    event_type,
                    occurred_at,
                    payload_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    "SNAPSHOT_ARCHIVED",
                    BASE_TIME.isoformat(),
                    "{}",
                ),
            )

    return database


def test_json_output_returns_complete_comparison(
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
            "--earlier",
            FIRST_ID,
            "--later",
            SECOND_ID,
            "--json",
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report[
        "earlier_snapshot_id"
    ] == FIRST_ID
    assert report[
        "later_snapshot_id"
    ] == SECOND_ID
    assert report[
        "compatibility_status"
    ] == "COMPATIBLE"
    assert report[
        "portfolio_summary"
    ][
        "total_value"
    ][
        "absolute_change"
    ] == 2000.0
    assert report[
        "holdings"
    ][0][
        "change_type"
    ] == "CHANGED"


def test_human_output_summarizes_changes(
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
            "--earlier",
            FIRST_ID,
            "--later",
            SECOND_ID,
        ]
    )

    output = capsys.readouterr().out

    assert "Compatibility: COMPATIBLE" in output
    assert "Total value:" in output
    assert "Holdings: added 0, removed 0, changed 1" in output
    assert "WORLD: CHANGED" in output


def test_human_output_exposes_source_status_warning(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = prepare_database(
        tmp_path,
        second_source_status="MARKET_VALUE_CONNECTED",
    )

    main(
        [
            "--database",
            str(
                database
            ),
            "--earlier",
            FIRST_ID,
            "--later",
            SECOND_ID,
        ]
    )

    output = capsys.readouterr().out

    assert "Compatibility: PARTIALLY_COMPATIBLE" in output
    assert (
        "Portfolio source status differs between snapshots"
        in output
    )
    assert (
        "COST_BASIS_ONLY -> MARKET_VALUE_CONNECTED"
        in output
    )


def test_incompatible_result_is_reported_without_leaf_details(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = prepare_database(
        tmp_path,
        second_portfolio_name="Other",
    )

    main(
        [
            "--database",
            str(
                database
            ),
            "--earlier",
            FIRST_ID,
            "--later",
            SECOND_ID,
        ]
    )

    output = capsys.readouterr().out

    assert "Compatibility: INCOMPATIBLE" in output
    assert "Portfolio identity does not match" in output
    assert "Comparison details were not produced." in output


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
                "--earlier",
                FIRST_ID,
                "--later",
                "7a5dc1c4-9d9a-4c17-a63c-1f8bb35e2199",
            ]
        )

    assert exc.value.code == 2
    assert (
        "No historical snapshot found"
        in capsys.readouterr().err
    )


def test_missing_database_is_actionable_and_not_created(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = tmp_path / "missing.db"

    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--database",
                str(
                    database
                ),
                "--earlier",
                FIRST_ID,
                "--later",
                SECOND_ID,
            ]
        )

    assert exc.value.code == 2
    assert (
        "History database does not exist"
        in capsys.readouterr().err
    )
    assert not database.exists()


def test_same_snapshot_is_actionable(
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
                "--earlier",
                FIRST_ID,
                "--later",
                FIRST_ID,
            ]
        )

    assert exc.value.code == 2
    assert (
        "must differ"
        in capsys.readouterr().err
    )
