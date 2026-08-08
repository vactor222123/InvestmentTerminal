"""
Real end-to-end Sprint 12/13 History fixture.

The flow intentionally crosses the public History boundaries:
Review Package -> archive -> manifest -> SQLite sync/import -> timeline ->
query CLI -> comparison CLI -> replay CLI.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from investment_terminal.cli.compare_history import main as compare_history
from investment_terminal.cli.query_history import main as query_history
from investment_terminal.cli.replay_history import main as replay_history
from investment_terminal.history.historical_import_pipeline import (
    HistoricalImportPipeline,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_manifest_import_service import (
    HistoricalManifestImportService,
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


FIXTURE_ROOT = (
    Path(__file__).parent
    / "fixtures"
    / "history"
)

FIRST_ID = "11111111-1111-4111-8111-111111111111"
SECOND_ID = "22222222-2222-4222-8222-222222222222"

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


def _copy_fixture(
    tmp_path: Path,
    name: str,
) -> Path:
    source = FIXTURE_ROOT / name
    destination = tmp_path / "source" / name
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    destination.write_bytes(
        source.read_bytes()
    )
    return destination


def _archive(
    *,
    history_root: Path,
    source: Path,
    snapshot_id: str,
    archived_at: datetime,
    supersedes: str | None = None,
):
    archive = HistoricalSnapshotArchive(
        history_root,
        clock=lambda: archived_at,
        uuid_factory=lambda: UUID(
            snapshot_id
        ),
    )
    return archive.archive(
        source,
        product_version="0.13.0",
        supersedes=supersedes,
    )


def test_real_history_flow_end_to_end(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    history_root = tmp_path / "history"
    first_source = _copy_fixture(
        tmp_path,
        "review_package_2026_07.json",
    )
    second_source = _copy_fixture(
        tmp_path,
        "review_package_2026_08.json",
    )

    first = _archive(
        history_root=history_root,
        source=first_source,
        snapshot_id=FIRST_ID,
        archived_at=FIRST_ARCHIVED_AT,
    )
    second = _archive(
        history_root=history_root,
        source=second_source,
        snapshot_id=SECOND_ID,
        archived_at=SECOND_ARCHIVED_AT,
        supersedes=FIRST_ID,
    )

    assert (
        history_root
        / first.relative_path
    ).read_bytes() == first_source.read_bytes()
    assert (
        history_root
        / second.relative_path
    ).read_bytes() == second_source.read_bytes()
    assert second.supersedes == FIRST_ID

    manifest = HistoricalSnapshotManifest(
        history_root / "manifest.jsonl"
    )
    manifest.append(
        first
    )
    manifest.append(
        second
    )

    assert manifest.load_all() == (
        first,
        second,
    )

    database = history_root / "history.db"
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
    sync_result = HistoricalManifestImportService(
        manifest=manifest,
        repository=snapshots,
        state_repository=states,
        clock=lambda: SYNC_AT,
    ).synchronize()

    assert sync_result.manifest_records == 2
    assert sync_result.imported_records == 2
    assert snapshots.list_all() == (
        first,
        second,
    )

    import_times = iter(
        (
            datetime(2026, 9, 1, 9, 1, tzinfo=timezone.utc),
            datetime(2026, 9, 1, 9, 2, tzinfo=timezone.utc),
            datetime(2026, 9, 1, 9, 3, tzinfo=timezone.utc),
            datetime(2026, 9, 1, 9, 4, tzinfo=timezone.utc),
            datetime(2026, 9, 1, 9, 5, tzinfo=timezone.utc),
            datetime(2026, 9, 1, 9, 6, tzinfo=timezone.utc),
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

    first_result = pipeline.import_snapshot(
        first
    )
    second_result = pipeline.import_snapshot(
        second
    )

    assert first_result.holdings_imported == 3
    assert first_result.recommendations_imported == 2
    assert first_result.deployment_imported == 2
    assert first_result.timeline_events_created == 9
    assert second_result.holdings_imported == 3
    assert second_result.recommendations_imported == 2
    assert second_result.deployment_imported == 2
    assert second_result.timeline_events_created == 9
    assert states.require(
        FIRST_ID
    ).status == "IMPORTED"
    assert states.require(
        SECOND_ID
    ).status == "IMPORTED"

    query_history(
        [
            "--database",
            str(
                database
            ),
            "--json",
            "snapshots",
        ]
    )
    snapshots_report = json.loads(
        capsys.readouterr().out
    )
    assert snapshots_report[
        "count"
    ] == 2
    assert [
        item[
            "snapshot_id"
        ]
        for item in snapshots_report[
            "snapshots"
        ]
    ] == [
        FIRST_ID,
        SECOND_ID,
    ]

    query_history(
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
    timeline_report = json.loads(
        capsys.readouterr().out
    )
    assert timeline_report[
        "count"
    ] == 9
    assert {
        event[
            "event_type"
        ]
        for event in timeline_report[
            "events"
        ]
    } >= {
        "SNAPSHOT_ARCHIVED",
        "PORTFOLIO_SUMMARY_RECORDED",
        "HOLDING_RECORDED",
        "RECOMMENDATION_RECORDED",
        "DEPLOYMENT_RECORDED",
    }

    compare_history(
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
    comparison = json.loads(
        capsys.readouterr().out
    )

    assert comparison[
        "compatibility_status"
    ] == "PARTIALLY_COMPATIBLE"
    assert (
        "Portfolio source status differs between snapshots"
        in comparison[
            "compatibility_notes"
        ]
    )
    assert comparison[
        "portfolio_summary"
    ][
        "total_value"
    ][
        "absolute_change"
    ] == 3100.0

    holdings = {
        item[
            "holding_key"
        ]: item
        for item in comparison[
            "holdings"
        ]
    }
    assert holdings[
        "WORLD"
    ][
        "change_type"
    ] == "CHANGED"
    assert holdings[
        "EM"
    ][
        "change_type"
    ] == "CHANGED"
    assert holdings[
        "BOND"
    ][
        "change_type"
    ] == "CHANGED"

    recommendations = {
        item[
            "recommendation_key"
        ]: item
        for item in comparison[
            "recommendations"
        ]
    }
    assert recommendations[
        "EM-ADD"
    ][
        "change_type"
    ] == "CHANGED"
    assert recommendations[
        "EM-ADD"
    ][
        "previous"
    ][
        "action"
    ] == "BUY"
    assert recommendations[
        "EM-ADD"
    ][
        "current"
    ][
        "action"
    ] == "HOLD"

    deployment = {
        item[
            "deployment_key"
        ]: item
        for item in comparison[
            "deployment"
        ]
    }
    assert deployment[
        "NEXT-CONTRIBUTION-WORLD"
    ][
        "amount"
    ][
        "absolute_change"
    ] == 150.0

    replay_history(
        [
            "--history-root",
            str(
                history_root
            ),
            "--snapshot-id",
            SECOND_ID,
            "--mode",
            "exact",
            "--json",
        ]
    )
    exact_replay = json.loads(
        capsys.readouterr().out
    )
    expected_second = json.loads(
        second_source.read_text(
            encoding="utf-8"
        )
    )
    assert exact_replay[
        "exact_archived_evidence"
    ] is True
    assert exact_replay[
        "payload"
    ] == expected_second
    assert exact_replay[
        "evidence_checksum_sha256"
    ] == second.checksum_sha256

    replay_history(
        [
            "--history-root",
            str(
                history_root
            ),
            "--snapshot-id",
            SECOND_ID,
            "--mode",
            "normalized",
            "--json",
        ]
    )
    normalized_replay = json.loads(
        capsys.readouterr().out
    )

    assert normalized_replay[
        "exact_archived_evidence"
    ] is False
    assert normalized_replay[
        "payload"
    ][
        "import_state"
    ][
        "status"
    ] == "IMPORTED"
    assert len(
        normalized_replay[
            "payload"
        ][
            "holdings"
        ]
    ) == 3
    assert len(
        normalized_replay[
            "payload"
        ][
            "recommendations"
        ]
    ) == 2
    assert len(
        normalized_replay[
            "payload"
        ][
            "deployment"
        ]
    ) == 2
    assert len(
        normalized_replay[
            "payload"
        ][
            "timeline_events"
        ]
    ) == 9
    assert any(
        "archived Review Package remains canonical evidence"
        in warning
        for warning in normalized_replay[
            "warnings"
        ]
    )
