"""
Tests for research source import-lifecycle quality assessment.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from investment_terminal.history.historical_import_state_models import (
    HistoricalImportState,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
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
from investment_terminal.history.historical_outcome_source_import_quality import (
    HistoricalOutcomeSourceImportQualityService,
)


NOW = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)


def snapshot_id(number: int) -> str:
    return f"11111111-1111-4111-8111-{number:012d}"


def result(number: int) -> HistoricalMethodologyAwareObservationResult:
    return HistoricalMethodologyAwareObservationResult(
        methodology=HistoricalOutcomeMethodology.sprint_14_exact_close_v1(),
        observation=HistoricalRecommendationObservation(
            origin_snapshot_id=snapshot_id(number),
            recommendation_key="WORLD",
            symbol="IWDA",
            action="BUY",
            origin_at=NOW,
            window=HistoricalObservationWindow(
                kind="ELAPSED_DAYS",
                value=5,
            ),
            status="PARTIAL",
            evidence=None,
            warnings=(),
        ),
        outcome=None,
        origin_selected_evidence=None,
        endpoint_methodology_evidence=None,
    )


def imported(number: int) -> HistoricalImportState:
    return HistoricalImportState(
        snapshot_id=snapshot_id(number),
        status="IMPORTED",
        metadata_synchronized_at=NOW,
        package_verified_at=NOW,
        details_imported_at=NOW,
        timeline_built_at=NOW,
        importer_version="test",
        updated_at=NOW,
    )


def metadata_only(number: int) -> HistoricalImportState:
    return HistoricalImportState(
        snapshot_id=snapshot_id(number),
        status="METADATA_ONLY",
        metadata_synchronized_at=NOW,
        updated_at=NOW,
    )


def service(states: dict[str, HistoricalImportState | None]):
    repository = Mock(
        spec=HistoricalImportStateRepository
    )
    repository.get.side_effect = (
        lambda item: states.get(item)
    )
    return HistoricalOutcomeSourceImportQualityService(
        repository
    ), repository


def test_all_unique_source_snapshots_imported_is_complete() -> None:
    assessor, repository = service(
        {
            snapshot_id(1): imported(1),
            snapshot_id(2): imported(2),
        }
    )

    assessment = assessor.assess(
        (
            result(1),
            result(2),
        )
    )

    assert assessment.status == "COMPLETE"
    assert assessment.unique_snapshot_count == 2
    assert assessment.imported_snapshot_count == 2
    assert assessment.imported_fraction == 1.0
    assert assessment.warning is None
    assert repository.get.call_count == 2


def test_non_imported_snapshot_makes_quality_partial() -> None:
    assessor, _ = service(
        {
            snapshot_id(1): imported(1),
            snapshot_id(2): metadata_only(2),
        }
    )

    assessment = assessor.assess(
        (
            result(1),
            result(2),
        )
    )

    assert assessment.status == "PARTIAL"
    assert assessment.imported_snapshot_count == 1
    assert assessment.non_imported_snapshot_count == 1
    assert assessment.missing_state_snapshot_count == 0
    assert assessment.status_counts == (
        ("METADATA_ONLY", 1),
        ("IMPORTED", 1),
    )


def test_missing_import_state_is_accounted_separately() -> None:
    assessor, _ = service(
        {
            snapshot_id(1): imported(1),
            snapshot_id(2): None,
        }
    )

    assessment = assessor.assess(
        (
            result(1),
            result(2),
        )
    )

    assert assessment.status == "PARTIAL"
    assert assessment.imported_snapshot_count == 1
    assert assessment.non_imported_snapshot_count == 0
    assert assessment.missing_state_snapshot_count == 1
    assert assessment.imported_fraction == 0.5


def test_duplicate_observations_do_not_inflate_snapshot_counts() -> None:
    assessor, repository = service(
        {
            snapshot_id(1): imported(1),
        }
    )

    assessment = assessor.assess(
        (
            result(1),
            result(1),
        )
    )

    assert assessment.source_observation_count == 2
    assert assessment.unique_snapshot_count == 1
    assert assessment.imported_snapshot_count == 1
    assert repository.get.call_count == 1


def test_empty_source_is_unknown() -> None:
    assessor, _ = service({})

    assessment = assessor.assess(())

    assert assessment.status == "UNKNOWN"
    assert assessment.unique_snapshot_count == 0
    assert assessment.imported_fraction is None
    assert assessment.warning is not None


def test_serialization_exposes_lifecycle_distribution() -> None:
    assessor, _ = service(
        {
            snapshot_id(1): imported(1),
            snapshot_id(2): metadata_only(2),
            snapshot_id(3): None,
        }
    )

    data = assessor.assess(
        (
            result(1),
            result(2),
            result(3),
        )
    ).to_dict()

    assert data["status"] == "PARTIAL"
    assert data["unique_snapshot_count"] == 3
    assert data["imported_snapshot_count"] == 1
    assert data["missing_state_snapshot_count"] == 1
    assert data["status_counts"] == {
        "METADATA_ONLY": 1,
        "IMPORTED": 1,
    }


def test_invalid_result_type_is_rejected() -> None:
    assessor, _ = service({})

    with pytest.raises(
        TypeError,
        match="results must contain only",
    ):
        assessor.assess(
            (
                object(),  # type: ignore[arg-type]
            )
        )
