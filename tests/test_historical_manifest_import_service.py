"""
Tests for manifest-to-SQLite snapshot synchronization.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_manifest_import_service import (
    HistoricalManifestImportService,
    ManifestImportResult,
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


FIRST_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
SECOND_ID = (
    "f9b7adca-2f2b-47a4-901d-05ca37c445df"
)


def create_snapshot(
    *,
    snapshot_id: str = FIRST_ID,
    package_id: str = "review-001",
    generated_at: datetime | None = None,
    archived_at: datetime | None = None,
) -> HistoricalSnapshot:
    generated = generated_at or datetime(
        2026,
        8,
        3,
        17,
        35,
        tzinfo=timezone.utc,
    )
    archived = archived_at or datetime(
        2026,
        8,
        3,
        17,
        36,
        tzinfo=timezone.utc,
    )

    return HistoricalSnapshot(
        snapshot_id=snapshot_id,
        package_id=package_id,
        package_schema_version="1.0",
        product_version="0.12.0",
        generated_at=generated,
        archived_at=archived,
        relative_path=(
            f"{generated:%Y/%m}/{snapshot_id}.json"
        ),
        checksum_sha256="a" * 64,
        supersedes=None,
        status="ARCHIVED",
    )


def create_service(
    tmp_path: Path,
) -> tuple[
    HistoricalManifestImportService,
    HistoricalSnapshotManifest,
    HistoricalSnapshotRepository,
]:
    manifest = HistoricalSnapshotManifest(
        tmp_path
        / "history"
        / "manifest.jsonl"
    )
    repository = HistoricalSnapshotRepository(
        HistoricalSQLiteStore(
            tmp_path
            / "history"
            / "history.db"
        )
    )

    return (
        HistoricalManifestImportService(
            manifest=manifest,
            repository=repository,
        ),
        manifest,
        repository,
    )


def test_service_imports_new_manifest_snapshots(
    tmp_path: Path,
) -> None:
    service, manifest, repository = create_service(
        tmp_path
    )
    first = create_snapshot()
    second = create_snapshot(
        snapshot_id=SECOND_ID,
        package_id="review-002",
        generated_at=datetime(
            2026,
            8,
            4,
            17,
            35,
            tzinfo=timezone.utc,
        ),
        archived_at=datetime(
            2026,
            8,
            4,
            17,
            36,
            tzinfo=timezone.utc,
        ),
    )
    manifest.append(
        first
    )
    manifest.append(
        second
    )

    result = service.synchronize()

    assert result == ManifestImportResult(
        manifest_records=2,
        imported_records=2,
        skipped_records=0,
    )
    assert result.changed
    assert repository.count() == 2
    assert repository.require(
        FIRST_ID
    ) == first
    assert repository.require(
        SECOND_ID
    ) == second


def test_service_is_idempotent(
    tmp_path: Path,
) -> None:
    service, manifest, repository = create_service(
        tmp_path
    )
    manifest.append(
        create_snapshot()
    )

    first_result = service.synchronize()
    second_result = service.synchronize()

    assert first_result.imported_records == 1
    assert second_result == ManifestImportResult(
        manifest_records=1,
        imported_records=0,
        skipped_records=1,
    )
    assert not second_result.changed
    assert repository.count() == 1


def test_service_imports_only_missing_snapshots(
    tmp_path: Path,
) -> None:
    service, manifest, repository = create_service(
        tmp_path
    )
    first = create_snapshot()
    second = create_snapshot(
        snapshot_id=SECOND_ID,
        package_id="review-002",
        generated_at=datetime(
            2026,
            8,
            4,
            17,
            35,
            tzinfo=timezone.utc,
        ),
        archived_at=datetime(
            2026,
            8,
            4,
            17,
            36,
            tzinfo=timezone.utc,
        ),
    )
    manifest.append(
        first
    )
    repository.add(
        first
    )
    manifest.append(
        second
    )

    result = service.synchronize()

    assert result == ManifestImportResult(
        manifest_records=2,
        imported_records=1,
        skipped_records=1,
    )
    assert repository.count() == 2


def test_service_handles_empty_manifest(
    tmp_path: Path,
) -> None:
    service, _, repository = create_service(
        tmp_path
    )

    result = service.synchronize()

    assert result == ManifestImportResult(
        manifest_records=0,
        imported_records=0,
        skipped_records=0,
    )
    assert not result.changed
    assert repository.count() == 0


def test_import_result_serializes() -> None:
    result = ManifestImportResult(
        manifest_records=3,
        imported_records=2,
        skipped_records=1,
    )

    assert result.to_dict() == {
        "manifest_records": 3,
        "imported_records": 2,
        "skipped_records": 1,
        "changed": True,
    }


@pytest.mark.parametrize(
    "values",
    (
        {
            "manifest_records": -1,
            "imported_records": 0,
            "skipped_records": 0,
        },
        {
            "manifest_records": 1,
            "imported_records": 2,
            "skipped_records": 0,
        },
        {
            "manifest_records": 1,
            "imported_records": True,
            "skipped_records": 0,
        },
    ),
)
def test_import_result_rejects_invalid_values(
    values: dict[str, object],
) -> None:
    with pytest.raises(
        ValueError,
    ):
        ManifestImportResult(
            **values,  # type: ignore[arg-type]
        )


def test_service_rejects_invalid_manifest(
    tmp_path: Path,
) -> None:
    repository = HistoricalSnapshotRepository(
        HistoricalSQLiteStore(
            tmp_path / "history.db"
        )
    )

    with pytest.raises(
        TypeError,
        match=(
            "manifest must be a HistoricalSnapshotManifest"
        ),
    ):
        HistoricalManifestImportService(
            manifest=object(),  # type: ignore[arg-type]
            repository=repository,
        )


def test_service_rejects_invalid_repository(
    tmp_path: Path,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )

    with pytest.raises(
        TypeError,
        match=(
            "repository must be a HistoricalSnapshotRepository"
        ),
    ):
        HistoricalManifestImportService(
            manifest=manifest,
            repository=object(),  # type: ignore[arg-type]
        )
