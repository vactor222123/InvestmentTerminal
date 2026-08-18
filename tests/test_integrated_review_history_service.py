"""Tests for integrated Review Package preservation and projection."""

from datetime import datetime, timezone
import json
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
from investment_terminal.history.historical_snapshot_archive import (
    HistoricalSnapshotArchive,
)
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_snapshot_service import (
    HistoricalSnapshotService,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.history.integrated_review_history_service import (
    HistoricalProjectionAfterArchiveError,
    IntegratedReviewHistoryService,
)
from tests.test_historical_import_pipeline import (
    package_payload,
)


def create_service(
    tmp_path: Path,
) -> tuple[
    IntegratedReviewHistoryService,
    HistoricalSnapshotManifest,
    HistoricalSnapshotRepository,
]:
    archive_root = tmp_path / "archive"
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )
    store = HistoricalSQLiteStore(
        tmp_path / "history.sqlite3"
    )
    store.initialize()
    HistoricalSchemaMigrator(
        store=store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()
    repository = HistoricalSnapshotRepository(
        store
    )
    state_repository = HistoricalImportStateRepository(
        store
    )
    snapshot_service = HistoricalSnapshotService(
        archive=HistoricalSnapshotArchive(
            archive_root,
            clock=lambda: datetime(
                2026,
                8,
                18,
                10,
                5,
                tzinfo=timezone.utc,
            ),
        ),
        manifest=manifest,
    )
    manifest_import = HistoricalManifestImportService(
        manifest=manifest,
        repository=repository,
        state_repository=state_repository,
    )
    pipeline = HistoricalImportPipeline(
        store=store,
        loader=HistoricalReviewPackageLoader(
            archive_root
        ),
        state_repository=state_repository,
    )
    return (
        IntegratedReviewHistoryService(
            snapshot_service=snapshot_service,
            manifest_import_service=manifest_import,
            import_pipeline=pipeline,
        ),
        manifest,
        repository,
    )


def write_review_package(
    tmp_path: Path,
) -> Path:
    source = tmp_path / "review.json"
    source.write_text(
        json.dumps(
            package_payload()
        ),
        encoding="utf-8",
    )
    return source


def test_preserve_and_project_reports_separate_outcomes(
    tmp_path: Path,
) -> None:
    service, manifest, repository = create_service(
        tmp_path
    )

    result = service.preserve_and_project(
        write_review_package(
            tmp_path
        ),
        product_version="6.4.0",
        package_id="review-run-1",
    )

    assert manifest.load_all() == (
        result.snapshot,
    )
    assert repository.get(
        result.snapshot.snapshot_id
    ) == result.snapshot
    assert result.detail_import.snapshot_id == result.snapshot.snapshot_id
    assert result.to_dict()["archive"]["status"] == "COMPLETED"
    assert result.to_dict()["projection"]["status"] == "COMPLETED"


def test_projection_failure_keeps_registered_archive_visible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, manifest, repository = create_service(
        tmp_path
    )
    source = write_review_package(
        tmp_path
    )

    def fail_import(snapshot: object) -> None:
        raise OSError(
            "SQLite projection failed"
        )

    monkeypatch.setattr(
        service.import_pipeline,
        "import_snapshot",
        fail_import,
    )

    with pytest.raises(
        HistoricalProjectionAfterArchiveError,
        match="projection failed",
    ) as raised:
        service.preserve_and_project(
            source
        )

    failure = raised.value
    assert manifest.load_all() == (
        failure.snapshot,
    )
    assert repository.get(
        failure.snapshot.snapshot_id
    ) == failure.snapshot
    archived = (
        service.snapshot_service.archive.archive_root
        / failure.snapshot.relative_path
    )
    assert archived.read_bytes() == source.read_bytes()
    assert failure.to_dict()["archive"]["status"] == "COMPLETED"
    assert failure.to_dict()["projection"] == {
        "status": "FAILED",
        "reason": "SQLite projection failed",
    }


def test_archive_failure_does_not_start_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, manifest, repository = create_service(
        tmp_path
    )
    called = False

    def fail_archive(*args: object, **kwargs: object) -> None:
        raise OSError(
            "archive failed"
        )

    def track_projection() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(
        service.snapshot_service,
        "preserve",
        fail_archive,
    )
    monkeypatch.setattr(
        service.manifest_import_service,
        "synchronize",
        track_projection,
    )

    with pytest.raises(
        OSError,
        match="archive failed",
    ):
        service.preserve_and_project(
            write_review_package(
                tmp_path
            )
        )

    assert called is False
    assert manifest.load_all() == ()
    assert repository.list_all() == ()


def test_service_rejects_untyped_dependencies(
    tmp_path: Path,
) -> None:
    service, _, _ = create_service(
        tmp_path
    )

    with pytest.raises(
        TypeError,
        match="snapshot_service",
    ):
        IntegratedReviewHistoryService(
            snapshot_service=object(),
            manifest_import_service=service.manifest_import_service,
            import_pipeline=service.import_pipeline,
        )
