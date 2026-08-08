"""
Tests for chronological recommendation history service.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from investment_terminal.history.historical_recommendation_history_service import (
    HistoricalRecommendationHistoryService,
)
from investment_terminal.history.historical_recommendation_transition_models import (
    HistoricalRecommendationTransition,
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


IDS = (
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
    "33333333-3333-4333-8333-333333333333",
    "44444444-4444-4444-8444-444444444444",
    "55555555-5555-4555-8555-555555555555",
    "66666666-6666-4666-8666-666666666666",
)
T0 = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


def snapshot(
    index: int,
) -> HistoricalSnapshot:
    generated_at = T0 + timedelta(
        days=index
    )
    return HistoricalSnapshot(
        snapshot_id=IDS[index],
        package_id=f"review-{index}",
        package_schema_version="1.0",
        product_version="0.14.0",
        generated_at=generated_at,
        archived_at=generated_at + timedelta(
            minutes=1
        ),
        relative_path=f"2026/08/{IDS[index]}.json",
        checksum_sha256="a" * 64,
        status="ARCHIVED",
    )


def prepare_service(
    tmp_path: Path,
) -> HistoricalRecommendationHistoryService:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    snapshots = HistoricalSnapshotRepository(
        store
    )
    snapshots.add_many(
        tuple(
            snapshot(index)
            for index in range(
                len(IDS)
            )
        )
    )

    rows = (
        # Snapshot 0 intentionally has no WORLD recommendation.
        (
            IDS[1],
            "WORLD",
            "IWDA",
            "BUY",
            80.0,
            0.80,
        ),
        (
            IDS[2],
            "WORLD",
            "IWDA",
            "BUY",
            82.0,
            0.82,
        ),
        # Snapshot 3 intentionally omits WORLD -> DISAPPEARED.
        (
            IDS[4],
            "WORLD",
            "IWDA",
            "HOLD",
            78.0,
            0.75,
        ),
        (
            IDS[5],
            "WORLD",
            "SWDA",
            "HOLD",
            78.0,
            0.75,
        ),
    )

    with store.connect() as connection:
        for (
            snapshot_id,
            key,
            symbol,
            action,
            score,
            confidence,
        ) in rows:
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
                    snapshot_id,
                    key,
                    symbol,
                    action,
                    score,
                    confidence,
                    None,
                    json.dumps(
                        {
                            "recommendation_id": key,
                            "symbol": symbol,
                            "recommendation": action,
                        }
                    ),
                ),
            )

    return HistoricalRecommendationHistoryService(
        snapshot_repository=snapshots,
        recommendations_repository=HistoricalRecommendationsRepository(
            store
        ),
    )


def test_states_begin_at_first_observation(
    tmp_path: Path,
) -> None:
    service = prepare_service(
        tmp_path
    )

    states = service.states_for(
        "WORLD"
    )

    assert [
        state.snapshot_id
        for state in states
    ] == list(
        IDS[1:]
    )
    assert states[0].present is True
    assert states[2].present is False


def test_transitions_capture_evolution(
    tmp_path: Path,
) -> None:
    service = prepare_service(
        tmp_path
    )

    transitions = service.transitions_for(
        "WORLD"
    )

    assert [
        item.transition_type
        for item in transitions
    ] == [
        HistoricalRecommendationTransition.FIRST_OBSERVED,
        HistoricalRecommendationTransition.METRICS_CHANGED,
        HistoricalRecommendationTransition.DISAPPEARED,
        HistoricalRecommendationTransition.REAPPEARED,
        HistoricalRecommendationTransition.DESCRIPTIVE_CHANGED,
    ]

    assert transitions[1].duration_seconds == 86400.0
    assert transitions[3].current.action == "HOLD"
    assert transitions[4].current.symbol == "SWDA"


def test_unknown_key_returns_empty_history(
    tmp_path: Path,
) -> None:
    service = prepare_service(
        tmp_path
    )

    assert service.states_for(
        "UNKNOWN"
    ) == ()
    assert service.transitions_for(
        "UNKNOWN"
    ) == ()


def test_history_is_deterministic_across_calls(
    tmp_path: Path,
) -> None:
    service = prepare_service(
        tmp_path
    )

    first = service.transitions_for(
        "WORLD"
    )
    second = service.transitions_for(
        "WORLD"
    )

    assert first == second
