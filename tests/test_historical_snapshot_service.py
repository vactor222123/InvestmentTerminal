"""
Tests for the complete historical snapshot application workflow.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from investment_terminal.history.historical_snapshot_archive import (
    HistoricalSnapshotArchive,
)
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
)
from investment_terminal.history.historical_snapshot_service import (
    HistoricalSnapshotService,
)


SNAPSHOT_ID = UUID(
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
ARCHIVED_AT = datetime(
    2026,
    8,
    3,
    18,
    0,
    tzinfo=timezone.utc,
)


def write_package(
    path: Path,
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "generated_at": (
                    "2026-08-03T17:35:00+00:00"
                ),
                "portfolio_name": "Test Portfolio",
                "warnings": [],
                "sections": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def create_service(
    tmp_path: Path,
) -> HistoricalSnapshotService:
    archive = HistoricalSnapshotArchive(
        tmp_path / "history",
        clock=lambda: ARCHIVED_AT,
        uuid_factory=lambda: SNAPSHOT_ID,
    )
    manifest = HistoricalSnapshotManifest(
        tmp_path
        / "history"
        / "manifest.jsonl"
    )

    return HistoricalSnapshotService(
        archive=archive,
        manifest=manifest,
    )


def test_service_archives_and_registers_snapshot(
    tmp_path: Path,
) -> None:
    source = (
        tmp_path
        / "investment_review_package.json"
    )
    write_package(
        source
    )
    service = create_service(
        tmp_path
    )

    snapshot = service.preserve(
        source,
        product_version="0.12.0",
        package_id="review-001",
    )

    archived_path = (
        service.archive.archive_root
        / snapshot.relative_path
    )

    assert archived_path.exists()
    assert service.manifest.load_all() == (
        snapshot,
    )
    assert snapshot.package_id == "review-001"
    assert snapshot.product_version == "0.12.0"


def test_service_returns_registered_snapshot(
    tmp_path: Path,
) -> None:
    source = tmp_path / "review.json"
    write_package(
        source
    )
    service = create_service(
        tmp_path
    )

    snapshot = service.preserve(
        source
    )

    assert (
        service.manifest.require_by_snapshot_id(
            snapshot.snapshot_id
        )
        == snapshot
    )


def test_service_removes_archive_when_manifest_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "review.json"
    write_package(
        source
    )
    service = create_service(
        tmp_path
    )

    def fail_append(
        snapshot: object,
    ) -> Path:
        raise ValueError(
            "manifest failure"
        )

    monkeypatch.setattr(
        service.manifest,
        "append",
        fail_append,
    )

    with pytest.raises(
        ValueError,
        match="manifest failure",
    ):
        service.preserve(
            source
        )

    archived_files = tuple(
        (
            tmp_path
            / "history"
        ).rglob(
            "*.json"
        )
    )

    assert archived_files == ()
    assert not (
        tmp_path
        / "history"
        / "manifest.jsonl"
    ).exists()


def test_service_syncs_archive_directory_after_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "review.json"
    write_package(
        source
    )
    service = create_service(
        tmp_path
    )
    calls: list[Path] = []

    def fail_append(
        snapshot: object,
    ) -> Path:
        raise ValueError(
            "manifest failure"
        )

    monkeypatch.setattr(
        service.manifest,
        "append",
        fail_append,
    )
    monkeypatch.setattr(
        "investment_terminal.history."
        "historical_snapshot_service.sync_directory",
        lambda directory: calls.append(
            directory
        ),
    )

    with pytest.raises(
        ValueError,
        match="manifest failure",
    ):
        service.preserve(
            source
        )

    assert [
        path.relative_to(
            tmp_path
        ).as_posix()
        for path in calls
    ] == [
        "history/2026/08",
        "history/2026",
        "history",
    ]


def test_service_reports_cleanup_durability_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "review.json"
    write_package(
        source
    )
    service = create_service(
        tmp_path
    )

    def fail_append(
        snapshot: object,
    ) -> Path:
        raise ValueError(
            "manifest failure"
        )

    def fail_sync(
        directory: Path,
    ) -> None:
        raise OSError(
            "directory sync failed"
        )

    monkeypatch.setattr(
        service.manifest,
        "append",
        fail_append,
    )
    monkeypatch.setattr(
        "investment_terminal.history."
        "historical_snapshot_service.sync_directory",
        fail_sync,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "unregistered archive file could not "
            "be durably removed"
        ),
    ) as exc_info:
        service.preserve(
            source
        )

    assert isinstance(
        exc_info.value.__cause__,
        OSError,
    )
    assert tuple(
        (
            tmp_path
            / "history"
        ).rglob(
            "*.json"
        )
    ) == ()


def test_service_removes_archive_when_manifest_is_interrupted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "review.json"
    write_package(
        source
    )
    service = create_service(
        tmp_path
    )

    class SimulatedInterruption(
        BaseException
    ):
        pass

    def interrupt_append(
        snapshot: object,
    ) -> Path:
        raise SimulatedInterruption()

    monkeypatch.setattr(
        service.manifest,
        "append",
        interrupt_append,
    )

    with pytest.raises(
        SimulatedInterruption,
    ):
        service.preserve(
            source
        )

    assert tuple(
        (
            tmp_path
            / "history"
        ).rglob(
            "*.json"
        )
    ) == ()
    assert not (
        tmp_path
        / "history"
        / "2026"
    ).exists()
    assert not (
        tmp_path
        / "history"
        / "manifest.jsonl"
    ).exists()


def test_service_does_not_remove_completed_snapshot(
    tmp_path: Path,
) -> None:
    source = tmp_path / "review.json"
    write_package(
        source
    )
    service = create_service(
        tmp_path
    )

    snapshot = service.preserve(
        source
    )
    archived_path = (
        service.archive.archive_root
        / snapshot.relative_path
    )

    with pytest.raises(
        FileExistsError,
        match=(
            "Historical snapshot already exists"
        ),
    ):
        service.preserve(
            source
        )

    assert archived_path.exists()
    assert service.manifest.load_all() == (
        snapshot,
    )


def test_service_rejects_invalid_archive_dependency(
    tmp_path: Path,
) -> None:
    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )

    with pytest.raises(
        TypeError,
        match=(
            "archive must be a HistoricalSnapshotArchive"
        ),
    ):
        HistoricalSnapshotService(
            archive=object(),  # type: ignore[arg-type]
            manifest=manifest,
        )


def test_service_rejects_invalid_manifest_dependency(
    tmp_path: Path,
) -> None:
    archive = HistoricalSnapshotArchive(
        tmp_path / "history"
    )

    with pytest.raises(
        TypeError,
        match=(
            "manifest must be a HistoricalSnapshotManifest"
        ),
    ):
        HistoricalSnapshotService(
            archive=archive,
            manifest=object(),  # type: ignore[arg-type]
        )
