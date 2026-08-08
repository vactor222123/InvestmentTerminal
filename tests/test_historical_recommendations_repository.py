"""
Tests for HistoricalRecommendation and HistoricalRecommendationsRepository.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_recommendation_models import (
    HistoricalRecommendation,
)
from investment_terminal.history.historical_recommendations_repository import (
    HistoricalRecommendationsRepository,
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


SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)


def create_snapshot() -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=SNAPSHOT_ID,
        package_id="review-001",
        package_schema_version="1.0",
        product_version="0.13.0",
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
        relative_path=f"2026/08/{SNAPSHOT_ID}.json",
        checksum_sha256="a" * 64,
        status="ARCHIVED",
    )


def create_repository(
    tmp_path: Path,
) -> tuple[
    HistoricalSQLiteStore,
    HistoricalRecommendationsRepository,
]:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    HistoricalSnapshotRepository(
        store
    ).add(
        create_snapshot()
    )

    return (
        store,
        HistoricalRecommendationsRepository(
            store
        ),
    )


def test_recommendation_model_normalizes_and_detaches_payload() -> None:
    payload = {
        "nested": {
            "items": [
                1,
                2,
            ]
        }
    }
    recommendation = HistoricalRecommendation(
        snapshot_id=SNAPSHOT_ID.upper(),
        recommendation_key=" rec-1 ",
        symbol=" baba ",
        action=" buy ",
        score=82.5,
        confidence=0.75,
        rationale=" Value ",
        payload=payload,
    )
    payload[
        "nested"
    ][
        "items"
    ].append(
        3
    )

    assert recommendation.snapshot_id == SNAPSHOT_ID
    assert recommendation.recommendation_key == "rec-1"
    assert recommendation.symbol == "BABA"
    assert recommendation.action == "BUY"
    assert recommendation.to_dict()[
        "payload"
    ] == {
        "nested": {
            "items": [
                1,
                2,
            ]
        }
    }


def test_recommendation_model_accepts_optional_numeric_values() -> None:
    recommendation = HistoricalRecommendation(
        snapshot_id=SNAPSHOT_ID,
        recommendation_key="rec-1",
        symbol=None,
        action=None,
        score=None,
        confidence=None,
        rationale=None,
        payload={},
    )

    assert recommendation.score is None
    assert recommendation.confidence is None


def test_repository_returns_empty_tuple(
    tmp_path: Path,
) -> None:
    _, repository = create_repository(
        tmp_path
    )

    assert repository.list_for_snapshot(
        SNAPSHOT_ID
    ) == ()


def test_repository_returns_key_order_and_parsed_payload(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )

    with store.connect() as connection:
        connection.executemany(
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
                (
                    SNAPSHOT_ID,
                    "ZETA",
                    "ZZZ",
                    "HOLD",
                    50.0,
                    None,
                    None,
                    '{"action":"HOLD","symbol":"ZZZ"}',
                ),
                (
                    SNAPSHOT_ID,
                    "ALPHA",
                    "AAA",
                    "BUY",
                    80.0,
                    0.9,
                    "Strong",
                    '{"action":"BUY","symbol":"AAA"}',
                ),
            ),
        )

    recommendations = repository.list_for_snapshot(
        SNAPSHOT_ID.upper()
    )

    assert [
        item.recommendation_key
        for item in recommendations
    ] == [
        "ALPHA",
        "ZETA",
    ]
    assert recommendations[
        0
    ].payload[
        "action"
    ] == "BUY"


def test_repository_rejects_invalid_persisted_json(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )

    with store.connect() as connection:
        connection.execute(
            """
            INSERT INTO recommendations (
                snapshot_id,
                recommendation_key,
                payload_json
            )
            VALUES (?, ?, ?)
            """,
            (
                SNAPSHOT_ID,
                "BAD",
                "{invalid",
            ),
        )

    with pytest.raises(
        ValueError,
        match="must contain valid JSON",
    ):
        repository.list_for_snapshot(
            SNAPSHOT_ID
        )


def test_repository_rejects_missing_snapshot(
    tmp_path: Path,
) -> None:
    _, repository = create_repository(
        tmp_path
    )

    with pytest.raises(
        KeyError,
        match="No historical snapshot found",
    ):
        repository.list_for_snapshot(
            "f9b7adca-2f2b-47a4-901d-05ca37c445df"
        )
