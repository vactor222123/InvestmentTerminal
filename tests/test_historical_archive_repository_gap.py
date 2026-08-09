"""
Tests for repository-backed historical archive gap composition.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_archive_cadence import (
    HistoricalArchiveCadencePolicy,
)
from investment_terminal.history.historical_archive_repository_gap import (
    HistoricalArchiveRepositoryGapService,
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


def dt(
    day: int,
    hour: int = 12,
) -> datetime:
    return datetime(
        2026,
        8,
        day,
        hour,
        0,
        tzinfo=timezone.utc,
    )


def snapshot(
    sequence: int,
    generated_at: datetime,
) -> HistoricalSnapshot:
    identifier = (
        f"11111111-1111-4111-8111-{sequence:012d}"
    )
    return HistoricalSnapshot(
        snapshot_id=identifier,
        package_id=f"review-{sequence:03d}",
        package_schema_version="1.0",
        product_version="0.18.0",
        generated_at=generated_at,
        archived_at=generated_at + timedelta(minutes=1),
        relative_path=f"2026/08/{identifier}.json",
        checksum_sha256=(
            f"{sequence:x}" * 64
        )[:64],
        status="ARCHIVED",
    )


def service(
    tmp_path: Path,
    snapshots: tuple[HistoricalSnapshot, ...],
) -> HistoricalArchiveRepositoryGapService:
    repository = HistoricalSnapshotRepository(
        HistoricalSQLiteStore(
            tmp_path / "history.db"
        )
    )
    repository.add_many(
        snapshots
    )
    return HistoricalArchiveRepositoryGapService(
        snapshot_repository=repository
    )


def daily_policy() -> HistoricalArchiveCadencePolicy:
    return HistoricalArchiveCadencePolicy.fixed_interval_v1(
        anchor_at=dt(1),
        interval_seconds=86_400,
    )


def test_repository_composition_reports_complete_grid(
    tmp_path: Path,
) -> None:
    assessor = service(
        tmp_path,
        (
            snapshot(1, dt(1)),
            snapshot(2, dt(2)),
            snapshot(3, dt(3)),
        ),
    )

    assessment = assessor.assess(
        policy=daily_policy(),
        start_at=dt(1),
        end_at=dt(3),
    )

    assert assessment.status == "COMPLETE"
    assert assessment.expected_count == 3
    assert assessment.observed_expected_count == 3
    assert assessment.missing_count == 0
    assert assessment.unexpected_observed_count == 0


def test_repository_composition_reports_missing_snapshot(
    tmp_path: Path,
) -> None:
    assessor = service(
        tmp_path,
        (
            snapshot(1, dt(1)),
            snapshot(3, dt(3)),
        ),
    )

    assessment = assessor.assess(
        policy=daily_policy(),
        start_at=dt(1),
        end_at=dt(3),
    )

    assert assessment.status == "GAPS"
    assert assessment.missing_count == 1
    assert assessment.missing_timestamps == (
        dt(2),
    )
    assert assessment.expected_coverage_fraction == pytest.approx(
        2 / 3
    )


def test_repository_composition_reports_unexpected_snapshot_separately(
    tmp_path: Path,
) -> None:
    assessor = service(
        tmp_path,
        (
            snapshot(1, dt(1)),
            snapshot(2, dt(2)),
            snapshot(3, dt(3)),
            snapshot(
                4,
                dt(
                    2,
                    13,
                ),
            ),
        ),
    )

    assessment = assessor.assess(
        policy=daily_policy(),
        start_at=dt(1),
        end_at=dt(3),
    )

    assert assessment.status == "COMPLETE"
    assert assessment.missing_count == 0
    assert assessment.unexpected_observed_count == 1
    assert assessment.unexpected_observed_timestamps == (
        dt(
            2,
            13,
        ),
    )


def test_repository_query_is_scoped_to_requested_interval(
    tmp_path: Path,
) -> None:
    assessor = service(
        tmp_path,
        (
            snapshot(1, dt(1)),
            snapshot(2, dt(2)),
            snapshot(3, dt(3)),
            snapshot(4, dt(4)),
        ),
    )

    assessment = assessor.assess(
        policy=daily_policy(),
        start_at=dt(2),
        end_at=dt(3),
    )

    assert assessment.status == "COMPLETE"
    assert assessment.expected_count == 2
    assert assessment.observed_expected_count == 2
    assert assessment.unexpected_observed_count == 0


def test_interval_before_policy_anchor_is_no_expectation(
    tmp_path: Path,
) -> None:
    assessor = service(
        tmp_path,
        (
            snapshot(
                1,
                datetime(
                    2026,
                    7,
                    31,
                    12,
                    0,
                    tzinfo=timezone.utc,
                ),
            ),
        ),
    )

    assessment = assessor.assess(
        policy=daily_policy(),
        start_at=datetime(
            2026,
            7,
            31,
            0,
            0,
            tzinfo=timezone.utc,
        ),
        end_at=datetime(
            2026,
            7,
            31,
            23,
            59,
            tzinfo=timezone.utc,
        ),
    )

    assert assessment.status == "NO_EXPECTATION"
    assert assessment.expected_count == 0
    assert assessment.unexpected_observed_count == 1


def test_empty_repository_with_expected_grid_is_gaps(
    tmp_path: Path,
) -> None:
    assessor = service(
        tmp_path,
        (),
    )

    assessment = assessor.assess(
        policy=daily_policy(),
        start_at=dt(1),
        end_at=dt(2),
    )

    assert assessment.status == "GAPS"
    assert assessment.expected_count == 2
    assert assessment.observed_expected_count == 0
    assert assessment.missing_timestamps == (
        dt(1),
        dt(2),
    )


def test_invalid_repository_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="snapshot_repository must be",
    ):
        HistoricalArchiveRepositoryGapService(
            snapshot_repository=object(),  # type: ignore[arg-type]
        )


def test_inverted_interval_is_rejected(
    tmp_path: Path,
) -> None:
    assessor = service(
        tmp_path,
        (),
    )

    with pytest.raises(
        ValueError,
        match="start_at must not be later",
    ):
        assessor.assess(
            policy=daily_policy(),
            start_at=dt(3),
            end_at=dt(1),
        )


def test_naive_interval_boundary_is_rejected(
    tmp_path: Path,
) -> None:
    assessor = service(
        tmp_path,
        (),
    )

    with pytest.raises(
        ValueError,
        match="start_at must be timezone-aware",
    ):
        assessor.assess(
            policy=daily_policy(),
            start_at=datetime(
                2026,
                8,
                1,
                12,
                0,
            ),
            end_at=dt(2),
        )
