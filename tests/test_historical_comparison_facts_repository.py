"""
Tests for HistoricalComparisonFacts and its repository.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_comparison_facts import (
    HistoricalComparisonFacts,
)
from investment_terminal.history.historical_comparison_facts_repository import (
    HistoricalComparisonFactsRepository,
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
    HistoricalComparisonFactsRepository,
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
        HistoricalComparisonFactsRepository(
            store
        ),
    )


def test_facts_model_normalizes_and_serializes() -> None:
    facts = HistoricalComparisonFacts(
        snapshot_id=SNAPSHOT_ID.upper(),
        portfolio_summary_present=True,
        portfolio_name=" Portfolio ",
        base_currency=" EUR ",
        source_status=" CONNECTED ",
        holdings_count=2,
        recommendations_count=1,
        deployment_count=1,
        timeline_event_count=6,
    )

    assert facts.snapshot_id == SNAPSHOT_ID
    assert facts.portfolio_name == "Portfolio"
    assert facts.base_currency == "EUR"
    assert facts.has_any_detail_rows
    assert facts.to_dict()[
        "timeline_event_count"
    ] == 6


def test_facts_model_rejects_summary_values_without_summary() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "portfolio_name must be None when "
            "portfolio_summary_present is False"
        ),
    ):
        HistoricalComparisonFacts(
            snapshot_id=SNAPSHOT_ID,
            portfolio_summary_present=False,
            portfolio_name="Portfolio",
            base_currency=None,
            source_status=None,
            holdings_count=0,
            recommendations_count=0,
            deployment_count=0,
            timeline_event_count=0,
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "holdings_count",
        "recommendations_count",
        "deployment_count",
        "timeline_event_count",
    ),
)
def test_facts_model_rejects_negative_counts(
    field_name: str,
) -> None:
    values = {
        "snapshot_id": SNAPSHOT_ID,
        "portfolio_summary_present": False,
        "portfolio_name": None,
        "base_currency": None,
        "source_status": None,
        "holdings_count": 0,
        "recommendations_count": 0,
        "deployment_count": 0,
        "timeline_event_count": 0,
    }
    values[
        field_name
    ] = -1

    with pytest.raises(
        ValueError,
        match=(
            f"{field_name} must be a non-negative integer"
        ),
    ):
        HistoricalComparisonFacts(
            **values,
        )


def test_repository_returns_empty_projection_facts(
    tmp_path: Path,
) -> None:
    _, repository = create_repository(
        tmp_path
    )

    facts = repository.get(
        SNAPSHOT_ID
    )

    assert facts == HistoricalComparisonFacts(
        snapshot_id=SNAPSHOT_ID,
        portfolio_summary_present=False,
        portfolio_name=None,
        base_currency=None,
        source_status=None,
        holdings_count=0,
        recommendations_count=0,
        deployment_count=0,
        timeline_event_count=0,
    )
    assert not facts.has_any_detail_rows


def test_repository_returns_normalized_projection_facts(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )

    with store.connect() as connection:
        connection.execute(
            """
            INSERT INTO portfolio_summary (
                snapshot_id,
                portfolio_name,
                base_currency,
                source_status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                SNAPSHOT_ID,
                "Portfolio",
                "EUR",
                "MARKET_VALUE_CONNECTED",
            ),
        )
        connection.execute(
            """
            INSERT INTO holdings (
                snapshot_id,
                holding_key
            )
            VALUES (?, ?)
            """,
            (
                SNAPSHOT_ID,
                "WORLD",
            ),
        )
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
                "BABA",
                "{}",
            ),
        )
        connection.execute(
            """
            INSERT INTO deployment (
                snapshot_id,
                deployment_key,
                payload_json
            )
            VALUES (?, ?, ?)
            """,
            (
                SNAPSHOT_ID,
                "BABA",
                "{}",
            ),
        )
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
                SNAPSHOT_ID,
                "SNAPSHOT_ARCHIVED",
                "2026-08-03T17:36:00+00:00",
                "{}",
            ),
        )

    facts = repository.get(
        SNAPSHOT_ID.upper()
    )

    assert facts.portfolio_summary_present
    assert facts.portfolio_name == "Portfolio"
    assert facts.base_currency == "EUR"
    assert facts.source_status == "MARKET_VALUE_CONNECTED"
    assert facts.holdings_count == 1
    assert facts.recommendations_count == 1
    assert facts.deployment_count == 1
    assert facts.timeline_event_count == 1


def test_repository_rejects_missing_snapshot(
    tmp_path: Path,
) -> None:
    _, repository = create_repository(
        tmp_path
    )
    missing = (
        "f9b7adca-2f2b-47a4-901d-05ca37c445df"
    )

    with pytest.raises(
        KeyError,
        match="No historical snapshot found",
    ):
        repository.get(
            missing
        )


def test_repository_rejects_invalid_store() -> None:
    with pytest.raises(
        TypeError,
        match="store must be a HistoricalSQLiteStore",
    ):
        HistoricalComparisonFactsRepository(
            object()  # type: ignore[arg-type]
        )
