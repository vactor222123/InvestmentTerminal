"""
Focused integration tests for explicit historical import-state workflow.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

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
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
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
BASE_TIME = datetime(
    2026,
    8,
    8,
    12,
    0,
    tzinfo=timezone.utc,
)


def package_payload() -> dict:
    return {
        "schema_version": "1.0",
        "generated_at": "2026-08-03T17:35:00+00:00",
        "sections": {
            "portfolio": {
                "status": "COST_BASIS_ONLY",
                "cost_basis_snapshot": {
                    "portfolio_name": "Test",
                    "base_currency": "EUR",
                    "total_value": 10000.0,
                    "invested_value": 9000.0,
                    "cash_value": 1000.0,
                    "monthly_contribution": 500.0,
                },
                "market_value": None,
            },
            "machine_recommendations": {
                "status": "CONNECTED",
                "recommendations": {
                    "items": []
                },
                "allocation": {
                    "items": []
                },
            },
        },
    }


def setup_history(
    tmp_path: Path,
):
    root = tmp_path / "history"
    relative_path = "2026/08/review.json"
    package_path = root / relative_path
    package_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    package_bytes = (
        json.dumps(
            package_payload(),
            indent=2,
        )
        + "\n"
    ).encode(
        "utf-8"
    )
    package_path.write_bytes(
        package_bytes
    )

    snapshot = HistoricalSnapshot(
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
        relative_path=relative_path,
        checksum_sha256=hashlib.sha256(
            package_bytes
        ).hexdigest(),
        status="ARCHIVED",
    )

    manifest = HistoricalSnapshotManifest(
        root / "manifest.jsonl"
    )
    manifest.append(
        snapshot
    )

    store = HistoricalSQLiteStore(
        root / "history.db"
    )
    store.initialize()
    HistoricalSchemaMigrator(
        store=store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()

    snapshot_repository = HistoricalSnapshotRepository(
        store
    )
    state_repository = HistoricalImportStateRepository(
        store
    )

    return (
        root,
        snapshot,
        manifest,
        store,
        snapshot_repository,
        state_repository,
    )


def test_manifest_sync_creates_metadata_only_state(
    tmp_path: Path,
) -> None:
    (
        _,
        snapshot,
        manifest,
        _,
        snapshot_repository,
        state_repository,
    ) = setup_history(
        tmp_path
    )

    service = HistoricalManifestImportService(
        manifest=manifest,
        repository=snapshot_repository,
        state_repository=state_repository,
        clock=lambda: BASE_TIME,
    )

    service.synchronize()

    state = state_repository.require(
        snapshot.snapshot_id
    )
    assert state.status == "METADATA_ONLY"
    assert state.metadata_synchronized_at == BASE_TIME


def test_manifest_sync_backfills_state_for_existing_metadata(
    tmp_path: Path,
) -> None:
    (
        _,
        snapshot,
        manifest,
        _,
        snapshot_repository,
        state_repository,
    ) = setup_history(
        tmp_path
    )
    snapshot_repository.add(
        snapshot
    )

    service = HistoricalManifestImportService(
        manifest=manifest,
        repository=snapshot_repository,
        state_repository=state_repository,
        clock=lambda: BASE_TIME,
    )

    result = service.synchronize()

    assert result.imported_records == 0
    assert state_repository.require(
        snapshot.snapshot_id
    ).status == "METADATA_ONLY"


def test_pipeline_commits_details_and_imported_state_together(
    tmp_path: Path,
) -> None:
    (
        root,
        snapshot,
        manifest,
        store,
        snapshot_repository,
        state_repository,
    ) = setup_history(
        tmp_path
    )

    HistoricalManifestImportService(
        manifest=manifest,
        repository=snapshot_repository,
        state_repository=state_repository,
        clock=lambda: BASE_TIME,
    ).synchronize()

    ticks = iter(
        BASE_TIME + timedelta(
            seconds=index
        )
        for index in range(
            1,
            20,
        )
    )
    pipeline = HistoricalImportPipeline(
        store=store,
        loader=HistoricalReviewPackageLoader(
            root
        ),
        state_repository=state_repository,
        clock=lambda: next(
            ticks
        ),
    )

    pipeline.import_snapshot(
        snapshot
    )

    state = state_repository.require(
        snapshot.snapshot_id
    )
    assert state.status == "IMPORTED"
    assert state.package_verified_at is not None
    assert state.details_imported_at is not None
    assert state.timeline_built_at is not None


def test_pipeline_rolls_back_details_then_marks_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        root,
        snapshot,
        manifest,
        store,
        snapshot_repository,
        state_repository,
    ) = setup_history(
        tmp_path
    )

    HistoricalManifestImportService(
        manifest=manifest,
        repository=snapshot_repository,
        state_repository=state_repository,
        clock=lambda: BASE_TIME,
    ).synchronize()

    ticks = iter(
        BASE_TIME + timedelta(
            seconds=index
        )
        for index in range(
            1,
            20,
        )
    )
    pipeline = HistoricalImportPipeline(
        store=store,
        loader=HistoricalReviewPackageLoader(
            root
        ),
        state_repository=state_repository,
        clock=lambda: next(
            ticks
        ),
    )

    def fail_build(
        *args,
        **kwargs,
    ):
        raise RuntimeError(
            "timeline failed"
        )

    monkeypatch.setattr(
        pipeline.timeline_builder,
        "build",
        fail_build,
    )

    with pytest.raises(
        RuntimeError,
        match="timeline failed",
    ):
        pipeline.import_snapshot(
            snapshot
        )

    assert state_repository.require(
        snapshot.snapshot_id
    ).status == "FAILED"

    with store.connect() as connection:
        summary_count = connection.execute(
            "SELECT COUNT(*) FROM portfolio_summary"
        ).fetchone()[0]

    assert summary_count == 0
