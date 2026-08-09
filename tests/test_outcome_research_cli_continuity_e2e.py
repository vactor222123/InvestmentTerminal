"""
End-to-end continuity coverage for repository-backed research CLI semantics.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_terminal.cli.outcome_research import (
    _print_human,
    build_argument_parser,
)
from investment_terminal.history.historical_archive_cadence import (
    HistoricalArchiveCadencePolicy,
)
from investment_terminal.history.historical_archive_repository_gap import (
    HistoricalArchiveRepositoryGapService,
)
from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalOutcomeMethodology,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
    HistoricalRecommendationObservation,
)
from investment_terminal.history.historical_outcome_query import (
    HistoricalOutcomeQuery,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_research_service import (
    HistoricalOutcomeResearchService,
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


METHODOLOGY = HistoricalOutcomeMethodology.sprint_14_exact_close_v1()
PROTOCOL = HistoricalOutcomeResearchProtocol.descriptive_v1(
    allowed_methodology_identities=(
        METHODOLOGY.identity_key,
    ),
    minimum_complete_sample_size=1,
)


def dt(day: int) -> datetime:
    return datetime(
        2026,
        8,
        day,
        12,
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
        checksum_sha256=(f"{sequence:x}" * 64)[:64],
        status="ARCHIVED",
    )


def result(
    sequence: int,
    origin_at: datetime,
) -> HistoricalMethodologyAwareObservationResult:
    return HistoricalMethodologyAwareObservationResult(
        methodology=METHODOLOGY,
        observation=HistoricalRecommendationObservation(
            origin_snapshot_id=(
                f"11111111-1111-4111-8111-{sequence:012d}"
            ),
            recommendation_key="WORLD",
            symbol="IWDA",
            action="BUY",
            origin_at=origin_at,
            window=HistoricalObservationWindow(
                kind="ELAPSED_DAYS",
                value=1,
            ),
            status="PARTIAL",
            evidence=None,
            warnings=(),
        ),
        outcome=None,
        origin_selected_evidence=None,
        endpoint_methodology_evidence=None,
    )


def query() -> HistoricalOutcomeQuery:
    return HistoricalOutcomeQuery(
        recommendation_key="WORLD",
        action="BUY",
        window_kind="ELAPSED_DAYS",
        window_value=1,
        methodology_id=METHODOLOGY.methodology_id,
        methodology_version=METHODOLOGY.version,
        origin_from=dt(1),
        origin_to=dt(3),
    )


def repository(
    tmp_path: Path,
    snapshots: tuple[HistoricalSnapshot, ...],
) -> HistoricalSnapshotRepository:
    repo = HistoricalSnapshotRepository(
        HistoricalSQLiteStore(
            tmp_path / "history.db"
        )
    )
    repo.add_many(snapshots)
    return repo


def daily_policy() -> HistoricalArchiveCadencePolicy:
    return HistoricalArchiveCadencePolicy.fixed_interval_v1(
        anchor_at=dt(1),
        interval_seconds=86_400,
    )


def report_for(
    *,
    source_results: tuple[
        HistoricalMethodologyAwareObservationResult,
        ...,
    ],
    gap_assessment,
) -> dict[str, object]:
    research = HistoricalOutcomeResearchService().analyze(
        results=source_results,
        protocol=PROTOCOL,
        population_query=query(),
        source_results=source_results,
        archive_gap_assessment=gap_assessment,
    )

    return {
        "command": "historical_outcome_research",
        "protocol": PROTOCOL.to_dict(),
        "recommendation_key": "WORLD",
        "methodology": METHODOLOGY.to_dict(),
        "window": {
            "kind": "ELAPSED_DAYS",
            "value": 1,
        },
        "session_calendar": None,
        "as_of": dt(10).isoformat(),
        "resolution": "D",
        "query": query().to_dict(),
        "archive_cadence": daily_policy().to_dict(),
        "archive_gap_assessment": gap_assessment.to_dict(),
        "produced_observation_count": len(source_results),
        "candidate_count": len(source_results),
        "cohort_count": len(research),
        "cohorts": [
            item.to_dict()
            for item in research
        ],
    }


def test_parser_accepts_explicit_cadence_options() -> None:
    parser = build_argument_parser()

    options = parser.parse_args(
        [
            "--recommendation-key",
            "WORLD",
            "--methodology",
            "ELAPSED_DAYS_EXACT_CLOSE",
            "--window-value",
            "1",
            "--minimum-sample-size",
            "1",
            "--as-of",
            "2026-08-10T12:00:00+00:00",
            "--origin-from",
            "2026-08-01T12:00:00+00:00",
            "--origin-to",
            "2026-08-03T12:00:00+00:00",
            "--archive-cadence-anchor",
            "2026-08-01T12:00:00+00:00",
            "--archive-cadence-interval-seconds",
            "86400",
        ]
    )

    assert options.archive_cadence_anchor == dt(1)
    assert options.archive_cadence_interval_seconds == 86_400


def test_real_history_sqlite_gap_flows_to_research_and_human_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = repository(
        tmp_path,
        (
            snapshot(1, dt(1)),
            snapshot(3, dt(3)),
        ),
    )
    gap = HistoricalArchiveRepositoryGapService(
        snapshot_repository=repo
    ).assess(
        policy=daily_policy(),
        start_at=dt(1),
        end_at=dt(3),
    )

    assert gap.status == "GAPS"
    assert gap.missing_timestamps == (
        dt(2),
    )

    source = (
        result(1, dt(1)),
        result(3, dt(3)),
    )
    report = report_for(
        source_results=source,
        gap_assessment=gap,
    )

    cohort = report["cohorts"][0]  # type: ignore[index]
    completeness = cohort["provenance"]["population_completeness"]  # type: ignore[index]
    assert completeness["status"] == "COVERED"
    assert completeness["internal_continuity_status"] == "GAPS"

    _print_human(report)  # type: ignore[arg-type]
    output = capsys.readouterr().out

    assert "Completeness : COVERED / internal=GAPS" in output
    assert "missing expected archive timestamps" in output


def test_real_history_sqlite_complete_grid_flows_to_research_and_human_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = repository(
        tmp_path,
        (
            snapshot(1, dt(1)),
            snapshot(2, dt(2)),
            snapshot(3, dt(3)),
        ),
    )
    gap = HistoricalArchiveRepositoryGapService(
        snapshot_repository=repo
    ).assess(
        policy=daily_policy(),
        start_at=dt(1),
        end_at=dt(3),
    )

    assert gap.status == "COMPLETE"
    assert gap.missing_count == 0

    source = (
        result(1, dt(1)),
        result(2, dt(2)),
        result(3, dt(3)),
    )
    report = report_for(
        source_results=source,
        gap_assessment=gap,
    )

    cohort = report["cohorts"][0]  # type: ignore[index]
    completeness = cohort["provenance"]["population_completeness"]  # type: ignore[index]
    assert completeness["internal_continuity_status"] == "COMPLETE"

    _print_human(report)  # type: ignore[arg-type]
    output = capsys.readouterr().out

    assert "Completeness : COVERED / internal=COMPLETE" in output
    assert "no missing expected archive timestamps" in output


def test_json_ready_report_keeps_cadence_gap_and_provenance_consistent(
    tmp_path: Path,
) -> None:
    repo = repository(
        tmp_path,
        (
            snapshot(1, dt(1)),
            snapshot(3, dt(3)),
        ),
    )
    gap = HistoricalArchiveRepositoryGapService(
        snapshot_repository=repo
    ).assess(
        policy=daily_policy(),
        start_at=dt(1),
        end_at=dt(3),
    )
    report = report_for(
        source_results=(
            result(1, dt(1)),
            result(3, dt(3)),
        ),
        gap_assessment=gap,
    )

    assert report["archive_cadence"]["identity_key"] == (  # type: ignore[index]
        "FIXED_INTERVAL_ARCHIVE_CADENCE@1"
    )
    assert report["archive_gap_assessment"]["status"] == "GAPS"  # type: ignore[index]
    assert report["archive_gap_assessment"]["missing_count"] == 1  # type: ignore[index]

    cohort = report["cohorts"][0]  # type: ignore[index]
    assert cohort["provenance"]["population_completeness"][  # type: ignore[index]
        "internal_continuity_status"
    ] == "GAPS"
    assert cohort["population_completeness"][  # type: ignore[index]
        "internal_continuity_status"
    ] == "GAPS"
