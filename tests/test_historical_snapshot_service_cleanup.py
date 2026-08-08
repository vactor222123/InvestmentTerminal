"""
Focused durability tests for historical snapshot directory cleanup.
"""

from pathlib import Path

import pytest

from investment_terminal.history.historical_snapshot_service import (
    HistoricalSnapshotService,
)


def test_empty_archive_directories_are_synced_after_removal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    month = tmp_path / "history" / "2026" / "08"
    month.mkdir(parents=True)
    calls: list[Path] = []

    monkeypatch.setattr(
        "investment_terminal.history."
        "historical_snapshot_service.sync_directory",
        lambda directory: calls.append(directory),
    )

    HistoricalSnapshotService._remove_empty_parents(month)

    assert [
        path.relative_to(tmp_path).as_posix()
        for path in calls
    ] == [
        "history/2026",
        "history",
    ]
    assert not (tmp_path / "history" / "2026").exists()


def test_empty_directory_cleanup_stops_at_non_empty_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    month = tmp_path / "history" / "2026" / "08"
    month.mkdir(parents=True)
    sibling = month.parent / "keep.txt"
    sibling.write_text("keep", encoding="utf-8")
    calls: list[Path] = []

    monkeypatch.setattr(
        "investment_terminal.history."
        "historical_snapshot_service.sync_directory",
        lambda directory: calls.append(directory),
    )

    HistoricalSnapshotService._remove_empty_parents(month)

    assert calls == [month.parent]
    assert sibling.exists()
    assert month.parent.exists()


def test_empty_directory_sync_failure_is_recovery_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    month = tmp_path / "history" / "2026" / "08"
    month.mkdir(parents=True)

    def fail_sync(directory: Path) -> None:
        raise OSError("directory sync failed")

    monkeypatch.setattr(
        "investment_terminal.history."
        "historical_snapshot_service.sync_directory",
        fail_sync,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "removed an empty archive directory "
            "but could not durably persist"
        ),
    ) as exc_info:
        HistoricalSnapshotService._remove_empty_parents(month)

    assert isinstance(exc_info.value.__cause__, OSError)
    assert not month.exists()
