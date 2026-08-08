"""
Tests for HistoricalSnapshotComparisonService.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from investment_terminal.history.historical_comparison_facts_repository import (
    HistoricalComparisonFactsRepository,
)
from investment_terminal.history.historical_deployment_repository import (
    HistoricalDeploymentRepository,
)
from investment_terminal.history.historical_holdings_repository import (
    HistoricalHoldingsRepository,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_portfolio_summary_repository import (
    HistoricalPortfolioSummaryRepository,
)
from investment_terminal.history.historical_recommendations_repository import (
    HistoricalRecommendationsRepository,
)
from investment_terminal.history.historical_schema_migrations import (
    HISTORICAL_SCHEMA_MIGRATIONS,
    HISTORICAL_SCHEMA_TARGET_VERSION,
    HistoricalSchemaMigrator,
)
from investment_terminal.history.historical_snapshot_comparison_service import (
    HistoricalSnapshotComparisonService,
)
from investment_terminal.history.historical_snapshot_compatibility import (
    HistoricalSnapshotCompatibilityService,
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


def setup_service(
    tmp_path: Path,
) -> tuple[
    HistoricalSQLiteStore,
    HistoricalSnapshotComparisonService,
]:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
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

    service = HistoricalSnapshotComparisonService(
        snapshot_repository=snapshots,
        import_state_repository=states,
        facts_repository=HistoricalComparisonFactsRepository(
            store
        ),
        summary_repository=HistoricalPortfolioSummaryRepository(
            store
        ),
        holdings_repository=HistoricalHoldingsRepository(
            store
        ),
        recommendations_repository=HistoricalRecommendationsRepository(
            store
        ),
        deployment_repository=HistoricalDeploymentRepository(
            store
        ),
        compatibility_service=HistoricalSnapshotCompatibilityService(
            supported_package_schemas=(
                "1.0",
            )
        ),
    )

    return store, service


def insert_summary(
    store: HistoricalSQLiteStore,
    snapshot_id: str,
    *,
    portfolio_name: str = "Main",
    currency: str = "EUR",
    total: float = 10000.0,
    invested: float = 9000.0,
    cash: float = 1000.0,
    status: str = "COST_BASIS_ONLY",
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
                snapshot_id,
                portfolio_name,
                currency,
                total,
                invested,
                cash,
                500.0,
                status,
            ),
        )


def test_service_aggregates_all_leaf_comparisons(
    tmp_path: Path,
) -> None:
    store, service = setup_service(
        tmp_path
    )
    insert_summary(
        store,
        FIRST_ID,
        total=10000.0,
        invested=9000.0,
        cash=1000.0,
    )
    insert_summary(
        store,
        SECOND_ID,
        total=12000.0,
        invested=10000.0,
        cash=2000.0,
    )

    with store.connect() as connection:
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
                "World",
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
                "World",
                "ETF",
                "CORE",
                "EUR",
                12.0,
                100.0,
                1200.0,
                0.1,
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
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                FIRST_ID,
                "BABA",
                "BABA",
                "HOLD",
                70.0,
                0.6,
                '{"symbol":"BABA","action":"HOLD"}',
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
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SECOND_ID,
                "BABA",
                "BABA",
                "BUY",
                80.0,
                0.8,
                '{"symbol":"BABA","action":"BUY"}',
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
                FIRST_ID,
                "BABA",
                300.0,
                0.2,
                "Old",
                '{"symbol":"BABA","amount":300}',
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
                SECOND_ID,
                "BABA",
                500.0,
                0.3,
                "New",
                '{"symbol":"BABA","amount":500}',
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

    comparison = service.compare(
        earlier_snapshot_id=FIRST_ID,
        later_snapshot_id=SECOND_ID,
    )

    assert comparison.compatibility_status == "COMPATIBLE"
    assert comparison.portfolio_summary is not None
    assert comparison.portfolio_summary.total_value.absolute_change == 2000.0
    assert comparison.holdings[0].change_type == "CHANGED"
    assert comparison.recommendations[0].change_type == "CHANGED"
    assert comparison.deployment[0].change_type == "CHANGED"


def test_incompatible_snapshots_short_circuit_leaf_comparison(
    tmp_path: Path,
) -> None:
    store, service = setup_service(
        tmp_path
    )
    insert_summary(
        store,
        FIRST_ID,
        portfolio_name="Portfolio A",
        currency="EUR",
    )
    insert_summary(
        store,
        SECOND_ID,
        portfolio_name="Portfolio B",
        currency="EUR",
    )

    comparison = service.compare(
        earlier_snapshot_id=FIRST_ID,
        later_snapshot_id=SECOND_ID,
    )

    assert comparison.compatibility_status == "INCOMPATIBLE"
    assert comparison.portfolio_summary is None
    assert comparison.holdings == ()
    assert comparison.recommendations == ()
    assert comparison.deployment == ()
    assert "Portfolio identity does not match" in comparison.compatibility_notes


def test_partial_compatibility_still_returns_bounded_comparison(
    tmp_path: Path,
) -> None:
    store, service = setup_service(
        tmp_path
    )
    insert_summary(
        store,
        FIRST_ID,
        status="COST_BASIS_ONLY",
    )
    insert_summary(
        store,
        SECOND_ID,
        status="MARKET_VALUE_CONNECTED",
    )

    comparison = service.compare(
        earlier_snapshot_id=FIRST_ID,
        later_snapshot_id=SECOND_ID,
    )

    assert comparison.compatibility_status == "PARTIALLY_COMPATIBLE"
    assert comparison.portfolio_summary is not None
    assert (
        "Portfolio source status differs between snapshots"
        in comparison.compatibility_notes
    )


def test_service_rejects_missing_snapshot(
    tmp_path: Path,
) -> None:
    _, service = setup_service(
        tmp_path
    )

    try:
        service.compare(
            earlier_snapshot_id=FIRST_ID,
            later_snapshot_id=(
                "7a5dc1c4-9d9a-4c17-a63c-1f8bb35e2199"
            ),
        )
    except KeyError as exc:
        assert "No historical snapshot found" in str(
            exc
        )
    else:
        raise AssertionError(
            "Expected missing snapshot to raise KeyError"
        )
