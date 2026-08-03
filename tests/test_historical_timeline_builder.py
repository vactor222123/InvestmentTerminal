"""
Tests for HistoricalTimelineBuilder.
"""

import json
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
from investment_terminal.history.historical_timeline_builder import (
    HistoricalTimelineBuilder,
)


SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)


def create_snapshot() -> HistoricalSnapshot:
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
            17,
            36,
            tzinfo=timezone.utc,
        ),
        relative_path=(
            f"2026/08/{SNAPSHOT_ID}.json"
        ),
        checksum_sha256="a" * 64,
        supersedes=None,
        status="ARCHIVED",
    )


def create_store(
    tmp_path: Path,
) -> tuple[
    HistoricalSQLiteStore,
    HistoricalSnapshot,
]:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    snapshot = create_snapshot()
    HistoricalSnapshotRepository(
        store
    ).add(
        snapshot
    )

    return store, snapshot


def seed_normalized_history(
    store: HistoricalSQLiteStore,
) -> None:
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
                SNAPSHOT_ID,
                "Test Portfolio",
                "EUR",
                10000.0,
                8500.0,
                1500.0,
                1200.0,
                "COST_BASIS_ONLY",
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
                strategy,
                currency,
                quantity,
                unit_price,
                market_value,
                weight
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SNAPSHOT_ID,
                "IE00B4L5Y983",
                "WORLD",
                "World ETF",
                "ETF",
                "CORE",
                "LONG_TERM",
                "EUR",
                50.0,
                100.0,
                5000.0,
                0.5,
            ),
        )
        connection.execute(
            """
            INSERT INTO recommendations (
                snapshot_id,
                recommendation_key,
                symbol,
                action,
                score,
                confidence,
                rationale,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SNAPSHOT_ID,
                "BABA:BUY:0000",
                "BABA",
                "BUY",
                82.5,
                0.76,
                "Attractive valuation.",
                '{"symbol":"BABA"}',
            ),
        )
        connection.execute(
            """
            INSERT INTO deployment (
                snapshot_id,
                deployment_key,
                amount,
                share,
                reason,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                SNAPSHOT_ID,
                "BABA:0000",
                600.0,
                0.30,
                "Highest opportunity score.",
                '{"symbol":"BABA"}',
            ),
        )


def read_events(
    store: HistoricalSQLiteStore,
) -> list[dict]:
    with store.connect() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM timeline_events
            ORDER BY event_id
            """
        ).fetchall()

    return [
        dict(
            row
        )
        for row in rows
    ]


def test_builder_creates_complete_timeline(
    tmp_path: Path,
) -> None:
    store, snapshot = create_store(
        tmp_path
    )
    seed_normalized_history(
        store
    )

    created = HistoricalTimelineBuilder(
        store
    ).build(
        snapshot
    )

    events = read_events(
        store
    )

    assert created == 5
    assert [
        event["event_type"]
        for event in events
    ] == [
        "SNAPSHOT_ARCHIVED",
        "PORTFOLIO_SUMMARY_RECORDED",
        "HOLDING_RECORDED",
        "RECOMMENDATION_RECORDED",
        "DEPLOYMENT_RECORDED",
    ]
    assert events[0]["subject_key"] == SNAPSHOT_ID
    assert events[2]["subject_key"] == "IE00B4L5Y983"
    assert json.loads(
        events[3]["payload_json"]
    )["symbol"] == "BABA"


def test_builder_creates_snapshot_event_without_details(
    tmp_path: Path,
) -> None:
    store, snapshot = create_store(
        tmp_path
    )

    created = HistoricalTimelineBuilder(
        store
    ).build(
        snapshot
    )

    events = read_events(
        store
    )

    assert created == 1
    assert events[0]["event_type"] == (
        "SNAPSHOT_ARCHIVED"
    )


def test_builder_rejects_repeat_build(
    tmp_path: Path,
) -> None:
    store, snapshot = create_store(
        tmp_path
    )
    builder = HistoricalTimelineBuilder(
        store
    )

    builder.build(
        snapshot
    )

    with pytest.raises(
        ValueError,
        match="Timeline events already exist",
    ):
        builder.build(
            snapshot
        )


def test_builder_rejects_missing_snapshot(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )

    with pytest.raises(
        ValueError,
        match="Snapshot must exist in SQLite",
    ):
        HistoricalTimelineBuilder(
            store
        ).build(
            create_snapshot()
        )


def test_builder_rejects_invalid_store() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "store must be a HistoricalSQLiteStore"
        ),
    ):
        HistoricalTimelineBuilder(
            object()  # type: ignore[arg-type]
        )


def test_builder_rejects_invalid_snapshot(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )

    with pytest.raises(
        TypeError,
        match=(
            "snapshot must be a HistoricalSnapshot"
        ),
    ):
        HistoricalTimelineBuilder(
            store
        ).build(
            object()  # type: ignore[arg-type]
        )
