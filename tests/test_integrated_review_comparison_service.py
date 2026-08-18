"""Tests for deterministic integrated historical comparison selection."""

from datetime import timedelta
from pathlib import Path

import pytest

from investment_terminal.cli.compare_history import (
    _build_service,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
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
from investment_terminal.history.integrated_review_comparison_service import (
    IntegratedReviewComparisonService,
)
from tests.test_compare_history_cli import (
    BASE_TIME,
    FIRST_ID,
    SECOND_ID,
    prepare_database,
    snapshot,
)


THIRD_ID = "8be27847-a9d8-4c14-aafa-54b2e01f609d"


def create_service(
    database: Path,
) -> IntegratedReviewComparisonService:
    store = HistoricalSQLiteStore(
        database
    )
    return IntegratedReviewComparisonService(
        snapshot_repository=HistoricalSnapshotRepository(
            store
        ),
        import_state_repository=HistoricalImportStateRepository(
            store
        ),
        comparison_service=_build_service(
            store
        ),
    )


def test_selects_previous_imported_compatible_snapshot(
    tmp_path: Path,
) -> None:
    service = create_service(
        prepare_database(
            tmp_path
        )
    )

    result = service.compare_previous(
        SECOND_ID
    )

    assert result.status == "COMPLETED"
    assert result.previous_snapshot_id == FIRST_ID
    assert result.comparison is not None
    assert result.comparison.compatibility_status == "COMPATIBLE"
    assert result.to_dict()["comparison"][
        "later_snapshot_id"
    ] == SECOND_ID


def test_first_imported_snapshot_reports_first_run(
    tmp_path: Path,
) -> None:
    service = create_service(
        prepare_database(
            tmp_path
        )
    )

    result = service.compare_previous(
        FIRST_ID
    )

    assert result.status == "FIRST_RUN"
    assert result.previous_snapshot_id is None
    assert result.comparison is None
    assert result.reason == "No earlier historical snapshot exists"


def test_current_non_imported_snapshot_is_unavailable(
    tmp_path: Path,
) -> None:
    database = prepare_database(
        tmp_path
    )
    store = HistoricalSQLiteStore(
        database
    )
    current = snapshot(
        THIRD_ID,
        generated_at=BASE_TIME + timedelta(
            days=2
        ),
    )
    HistoricalSnapshotRepository(
        store
    ).add(
        current
    )

    result = create_service(
        database
    ).compare_previous(
        THIRD_ID
    )

    assert result.status == "UNAVAILABLE"
    assert result.reason == "Current snapshot does not have IMPORTED state"


def test_selects_nearest_earlier_imported_snapshot(
    tmp_path: Path,
) -> None:
    database = prepare_database(
        tmp_path
    )
    store = HistoricalSQLiteStore(
        database
    )
    current = snapshot(
        THIRD_ID,
        generated_at=BASE_TIME + timedelta(
            days=2
        ),
    )
    HistoricalSnapshotRepository(
        store
    ).add(
        current
    )
    HistoricalImportStateRepository(
        store
    ).initialize_legacy_imported(
        current,
        at=BASE_TIME + timedelta(
            days=3
        ),
    )

    result = create_service(
        database
    ).compare_previous(
        THIRD_ID
    )

    assert result.status == "COMPLETED"
    assert result.previous_snapshot_id == SECOND_ID


def test_reports_unavailable_when_only_earlier_snapshot_is_incompatible(
    tmp_path: Path,
) -> None:
    service = create_service(
        prepare_database(
            tmp_path,
            second_portfolio_name="Other",
        )
    )

    result = service.compare_previous(
        SECOND_ID
    )

    assert result.status == "UNAVAILABLE"
    assert result.reason == (
        "No earlier compatible snapshot with IMPORTED state exists"
    )


def test_service_rejects_untyped_dependency(
    tmp_path: Path,
) -> None:
    service = create_service(
        prepare_database(
            tmp_path
        )
    )

    with pytest.raises(
        TypeError,
        match="snapshot_repository",
    ):
        IntegratedReviewComparisonService(
            snapshot_repository=object(),
            import_state_repository=service.import_state_repository,
            comparison_service=service.comparison_service,
        )
