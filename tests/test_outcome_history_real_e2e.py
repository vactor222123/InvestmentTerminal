"""
Real end-to-end Sprint 14 outcome-aware Historical Intelligence fixture.

Flow:
Review Packages -> archive -> manifest -> History import ->
recommendation history/transition -> exact local candles ->
outcome observation -> aggregation -> outcome CLI.

The fixture is deterministic and network-free.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest

from investment_terminal.cli.outcome_history import (
    main as outcome_history,
)
from investment_terminal.config.settings import Settings
from investment_terminal.database.database import Database
from investment_terminal.history.historical_import_pipeline import (
    HistoricalImportPipeline,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_manifest_import_service import (
    HistoricalManifestImportService,
)
from investment_terminal.history.historical_recommendation_history_service import (
    HistoricalRecommendationHistoryService,
)
from investment_terminal.history.historical_recommendation_transition_models import (
    HistoricalRecommendationTransition,
)
from investment_terminal.history.historical_recommendations_repository import (
    HistoricalRecommendationsRepository,
)
from investment_terminal.history.historical_review_package_loader import (
    HistoricalReviewPackageLoader,
)
from investment_terminal.history.historical_schema_migrations import (
    HISTORICAL_SCHEMA_MIGRATIONS,
    HISTORICAL_SCHEMA_TARGET_VERSION,
    HistoricalSchemaMigrator,
)
from investment_terminal.history.historical_snapshot_archive import (
    HistoricalSnapshotArchive,
)
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.models.candle import Candle
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)


FIXTURE_ROOT = (
    Path(__file__).parent
    / "fixtures"
    / "history"
)

FIRST_ID = "11111111-1111-4111-8111-111111111111"
SECOND_ID = "22222222-2222-4222-8222-222222222222"

FIRST_GENERATED_AT = datetime(
    2026,
    7,
    31,
    18,
    0,
    tzinfo=timezone.utc,
)
SECOND_GENERATED_AT = datetime(
    2026,
    8,
    31,
    18,
    0,
    tzinfo=timezone.utc,
)

FIRST_ARCHIVED_AT = datetime(
    2026,
    8,
    1,
    8,
    0,
    tzinfo=timezone.utc,
)
SECOND_ARCHIVED_AT = datetime(
    2026,
    9,
    1,
    8,
    0,
    tzinfo=timezone.utc,
)
SYNC_AT = datetime(
    2026,
    9,
    1,
    9,
    0,
    tzinfo=timezone.utc,
)


def test_real_outcome_flow_end_to_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    history_root = tmp_path / "history"
    history_database = _prepare_history(
        tmp_path=tmp_path,
        history_root=history_root,
    )
    market_database = _prepare_market_database(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    store = HistoricalSQLiteStore(
        history_database
    )
    recommendation_history = HistoricalRecommendationHistoryService(
        snapshot_repository=HistoricalSnapshotRepository(
            store
        ),
        recommendations_repository=HistoricalRecommendationsRepository(
            store
        ),
    )

    states = recommendation_history.states_for(
        "EM-ADD"
    )
    assert len(
        states
    ) == 2
    assert [
        state.action
        for state in states
    ] == [
        "BUY",
        "HOLD",
    ]
    assert [
        state.symbol
        for state in states
    ] == [
        "EIMI",
        "EIMI",
    ]

    transitions = recommendation_history.transitions_for(
        "EM-ADD"
    )
    assert [
        transition.transition_type
        for transition in transitions
    ] == [
        HistoricalRecommendationTransition.FIRST_OBSERVED,
        HistoricalRecommendationTransition.ACTION_CHANGED,
    ]

    # At second snapshot + 4 days:
    # - first 5-day window is complete;
    # - second 5-day window is not mature yet.
    outcome_history(
        [
            "--history-database",
            str(
                history_database
            ),
            "--market-database",
            str(
                market_database
            ),
            "--recommendation-key",
            "EM-ADD",
            "--window-days",
            "5",
            "--as-of",
            (
                SECOND_GENERATED_AT
                + timedelta(
                    days=4
                )
            ).isoformat(),
            "--resolution",
            "D",
            "--json",
        ]
    )
    partial_report = json.loads(
        capsys.readouterr().out
    )

    assert partial_report[
        "count"
    ] == 2
    assert [
        item[
            "observation"
        ][
            "status"
        ]
        for item in partial_report[
            "observations"
        ]
    ] == [
        "COMPLETE",
        "NOT_MATURE",
    ]
    assert partial_report[
        "summary"
    ][
        "complete_count"
    ] == 1
    assert partial_report[
        "summary"
    ][
        "not_mature_count"
    ] == 1
    assert partial_report[
        "summary"
    ][
        "coverage_fraction"
    ] == 0.5

    first_outcome = partial_report[
        "observations"
    ][
        0
    ][
        "outcome"
    ]
    assert first_outcome is not None
    assert first_outcome[
        "currency"
    ] == "EUR"
    assert first_outcome[
        "origin_source"
    ] == "LOCAL_CANDLE_REPOSITORY_CLOSE"
    assert first_outcome[
        "endpoint_source"
    ] == "LOCAL_CANDLE_REPOSITORY_CLOSE"

    # At second snapshot + 5 days both observations are complete.
    outcome_history(
        [
            "--history-database",
            str(
                history_database
            ),
            "--market-database",
            str(
                market_database
            ),
            "--recommendation-key",
            "EM-ADD",
            "--window-days",
            "5",
            "--as-of",
            (
                SECOND_GENERATED_AT
                + timedelta(
                    days=5
                )
            ).isoformat(),
            "--resolution",
            "D",
            "--json",
        ]
    )
    complete_report = json.loads(
        capsys.readouterr().out
    )

    assert [
        item[
            "observation"
        ][
            "status"
        ]
        for item in complete_report[
            "observations"
        ]
    ] == [
        "COMPLETE",
        "COMPLETE",
    ]
    assert complete_report[
        "summary"
    ][
        "complete_count"
    ] == 2
    assert complete_report[
        "summary"
    ][
        "coverage_fraction"
    ] == 1.0
    assert complete_report[
        "summary"
    ][
        "action_counts"
    ] == [
        {
            "action": "BUY",
            "count": 1,
        },
        {
            "action": "HOLD",
            "count": 1,
        },
    ]

    movements = [
        item[
            "outcome"
        ][
            "price_change_fraction"
        ]
        for item in complete_report[
            "observations"
        ]
    ]
    assert movements[
        0
    ] == pytest.approx(
        0.05
    )
    assert movements[
        1
    ] == pytest.approx(
        -0.025
    )

    assert complete_report[
        "summary"
    ][
        "mean_price_change_fraction"
    ] == pytest.approx(
        (
            0.05
            - 0.025
        )
        / 2
    )
    assert complete_report[
        "summary"
    ][
        "median_price_change_fraction"
    ] == pytest.approx(
        (
            0.05
            - 0.025
        )
        / 2
    )
    assert (
        "not portfolio performance"
        in complete_report[
            "summary"
        ][
            "metric_semantics"
        ]
    )

    # Task 8 persistence decision remains true: outcome analysis does not
    # create or require an outcome table in History.
    with store.connect() as connection:
        table_names = {
            row[
                "name"
            ]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

    assert not any(
        "outcome"
        in name.lower()
        for name in table_names
    )


def _prepare_history(
    *,
    tmp_path: Path,
    history_root: Path,
) -> Path:
    first_source = _copy_fixture(
        tmp_path,
        "review_package_2026_07.json",
    )
    second_source = _copy_fixture(
        tmp_path,
        "review_package_2026_08.json",
    )

    first = HistoricalSnapshotArchive(
        history_root,
        clock=lambda: FIRST_ARCHIVED_AT,
        uuid_factory=lambda: UUID(
            FIRST_ID
        ),
    ).archive(
        first_source,
        product_version="0.14.0",
    )
    second = HistoricalSnapshotArchive(
        history_root,
        clock=lambda: SECOND_ARCHIVED_AT,
        uuid_factory=lambda: UUID(
            SECOND_ID
        ),
    ).archive(
        second_source,
        product_version="0.14.0",
        supersedes=FIRST_ID,
    )

    manifest = HistoricalSnapshotManifest(
        history_root
        / "manifest.jsonl"
    )
    manifest.append(
        first
    )
    manifest.append(
        second
    )

    database = (
        history_root
        / "history.db"
    )
    store = HistoricalSQLiteStore(
        database
    )
    store.initialize()
    HistoricalSchemaMigrator(
        store=store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()

    snapshots = HistoricalSnapshotRepository(
        store
    )
    states = HistoricalImportStateRepository(
        store
    )
    HistoricalManifestImportService(
        manifest=manifest,
        repository=snapshots,
        state_repository=states,
        clock=lambda: SYNC_AT,
    ).synchronize()

    import_times = iter(
        (
            datetime(
                2026,
                9,
                1,
                9,
                1,
                tzinfo=timezone.utc,
            ),
            datetime(
                2026,
                9,
                1,
                9,
                2,
                tzinfo=timezone.utc,
            ),
            datetime(
                2026,
                9,
                1,
                9,
                3,
                tzinfo=timezone.utc,
            ),
            datetime(
                2026,
                9,
                1,
                9,
                4,
                tzinfo=timezone.utc,
            ),
            datetime(
                2026,
                9,
                1,
                9,
                5,
                tzinfo=timezone.utc,
            ),
            datetime(
                2026,
                9,
                1,
                9,
                6,
                tzinfo=timezone.utc,
            ),
        )
    )
    pipeline = HistoricalImportPipeline(
        store=store,
        loader=HistoricalReviewPackageLoader(
            history_root
        ),
        state_repository=states,
        clock=lambda: next(
            import_times
        ),
    )

    pipeline.import_snapshot(
        first
    )
    pipeline.import_snapshot(
        second
    )

    assert states.require(
        FIRST_ID
    ).status == "IMPORTED"
    assert states.require(
        SECOND_ID
    ).status == "IMPORTED"

    return database


def _prepare_market_database(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    database_path = (
        tmp_path
        / "market.db"
    )
    previous = Settings.DATABASE_PATH
    monkeypatch.setattr(
        Settings,
        "DATABASE_PATH",
        database_path,
    )
    database = Database()
    database.initialize()
    repository = CandleRepository(
        database
    )

    try:
        _save_close(
            repository,
            timestamp=FIRST_GENERATED_AT,
            close=40.0,
        )
        _save_close(
            repository,
            timestamp=(
                FIRST_GENERATED_AT
                + timedelta(
                    days=5
                )
            ),
            close=42.0,
        )
        _save_close(
            repository,
            timestamp=SECOND_GENERATED_AT,
            close=44.0,
        )
        _save_close(
            repository,
            timestamp=(
                SECOND_GENERATED_AT
                + timedelta(
                    days=5
                )
            ),
            close=42.9,
        )
    finally:
        database.close()
        monkeypatch.setattr(
            Settings,
            "DATABASE_PATH",
            previous,
        )

    return database_path


def _save_close(
    repository: CandleRepository,
    *,
    timestamp: datetime,
    close: float,
) -> None:
    repository.save(
        Candle(
            symbol="EIMI",
            resolution="D",
            timestamp=timestamp,
            open_price=close,
            high_price=close,
            low_price=close,
            close_price=close,
            volume=1000.0,
            currency="EUR",
        )
    )


def _copy_fixture(
    tmp_path: Path,
    name: str,
) -> Path:
    source = (
        FIXTURE_ROOT
        / name
    )
    destination = (
        tmp_path
        / "source"
        / name
    )
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    destination.write_bytes(
        source.read_bytes()
    )
    return destination
