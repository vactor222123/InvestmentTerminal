"""
Tests for HistoricalReplayService.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_deployment_repository import (
    HistoricalDeploymentRepository,
)
from investment_terminal.history.historical_holdings_repository import (
    HistoricalHoldingsRepository,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_portfolio_summary_repository import (
    HistoricalPortfolioSummaryRepository,
)
from investment_terminal.history.historical_recommendations_repository import (
    HistoricalRecommendationsRepository,
)
from investment_terminal.history.historical_replay_models import (
    HistoricalReplayRequest,
)
from investment_terminal.history.historical_replay_service import (
    HistoricalReplayService,
)
from investment_terminal.history.historical_review_package_loader import (
    HistoricalReviewPackageLoader,
)
from investment_terminal.history.historical_schema_migrations import (
    HISTORICAL_SCHEMA_MIGRATIONS,
    HISTORICAL_SCHEMA_TARGET_VERSION,
    HistoricalSchemaMigrator,
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
from investment_terminal.history.historical_timeline_repository import (
    HistoricalTimelineRepository,
)


SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
GENERATED_AT = datetime(
    2026,
    8,
    3,
    17,
    35,
    tzinfo=timezone.utc,
)
ARCHIVED_AT = datetime(
    2026,
    8,
    3,
    17,
    36,
    tzinfo=timezone.utc,
)
STATE_AT = datetime(
    2026,
    8,
    8,
    12,
    0,
    tzinfo=timezone.utc,
)


def setup_service(
    tmp_path: Path,
) -> tuple[
    HistoricalReplayService,
    HistoricalSnapshot,
    HistoricalImportStateRepository,
]:
    root = tmp_path / "history"
    relative_path = f"2026/08/{SNAPSHOT_ID}.json"
    archive_path = root / relative_path
    archive_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "schema_version": "1.0",
        "generated_at": GENERATED_AT.isoformat(),
        "sections": {
            "portfolio": {
                "status": "COST_BASIS_ONLY",
            }
        },
    }
    package_bytes = (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )
        + "\n"
    ).encode(
        "utf-8"
    )
    archive_path.write_bytes(
        package_bytes
    )

    snapshot = HistoricalSnapshot(
        snapshot_id=SNAPSHOT_ID,
        package_id="review-001",
        package_schema_version="1.0",
        product_version="0.13.0",
        generated_at=GENERATED_AT,
        archived_at=ARCHIVED_AT,
        relative_path=relative_path,
        checksum_sha256=hashlib.sha256(
            package_bytes
        ).hexdigest(),
        status="ARCHIVED",
    )

    store = HistoricalSQLiteStore(
        root / "history.db"
    )
    snapshots = HistoricalSnapshotRepository(
        store
    )
    snapshots.add(
        snapshot
    )

    HistoricalSchemaMigrator(
        store=store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()

    states = HistoricalImportStateRepository(
        store
    )
    states.initialize_metadata(
        snapshot,
        at=STATE_AT,
    )

    service = HistoricalReplayService(
        snapshot_repository=snapshots,
        import_state_repository=states,
        portfolio_summary_repository=(
            HistoricalPortfolioSummaryRepository(
                store
            )
        ),
        holdings_repository=HistoricalHoldingsRepository(
            store
        ),
        recommendations_repository=(
            HistoricalRecommendationsRepository(
                store
            )
        ),
        deployment_repository=HistoricalDeploymentRepository(
            store
        ),
        timeline_repository=HistoricalTimelineRepository(
            store
        ),
        review_package_loader=HistoricalReviewPackageLoader(
            root
        ),
    )

    return (
        service,
        snapshot,
        states,
    )


def test_exact_replay_returns_verified_archived_package(
    tmp_path: Path,
) -> None:
    service, snapshot, _ = setup_service(
        tmp_path
    )

    result = service.replay(
        HistoricalReplayRequest(
            snapshot_id=SNAPSHOT_ID,
            mode="EXACT_ARCHIVED_PACKAGE",
        )
    )

    assert result.is_exact_archived_evidence
    assert result.evidence_checksum_sha256 == (
        snapshot.checksum_sha256
    )
    assert result.warnings == ()
    assert result.to_dict()[
        "payload"
    ][
        "schema_version"
    ] == "1.0"


def test_exact_replay_fails_when_archive_checksum_changes(
    tmp_path: Path,
) -> None:
    service, snapshot, _ = setup_service(
        tmp_path
    )

    archive_path = (
        tmp_path
        / "history"
        / snapshot.relative_path
    )
    archive_path.write_text(
        '{"schema_version":"1.0","generated_at":"changed"}',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="checksum does not match",
    ):
        service.replay(
            HistoricalReplayRequest(
                snapshot_id=SNAPSHOT_ID,
                mode="EXACT_ARCHIVED_PACKAGE",
            )
        )


def test_normalized_replay_returns_typed_projection(
    tmp_path: Path,
) -> None:
    service, snapshot, _ = setup_service(
        tmp_path
    )

    result = service.replay(
        HistoricalReplayRequest(
            snapshot_id=SNAPSHOT_ID,
            mode="NORMALIZED_HISTORICAL_VIEW",
        )
    )

    data = result.to_dict()

    assert result.is_normalized_view
    assert data[
        "payload"
    ][
        "snapshot"
    ][
        "snapshot_id"
    ] == snapshot.snapshot_id
    assert data[
        "payload"
    ][
        "import_state"
    ][
        "status"
    ] == "METADATA_ONLY"
    assert data[
        "payload"
    ][
        "portfolio_summary"
    ] is None
    assert data[
        "payload"
    ][
        "holdings"
    ] == []
    assert data[
        "payload"
    ][
        "timeline_events"
    ] == []
    assert any(
        "rebuildable SQLite projection"
        in warning
        for warning in data[
            "warnings"
        ]
    )
    assert any(
        "METADATA_ONLY"
        in warning
        for warning in data[
            "warnings"
        ]
    )


def test_normalized_replay_does_not_require_archive_file(
    tmp_path: Path,
) -> None:
    service, snapshot, _ = setup_service(
        tmp_path
    )

    (
        tmp_path
        / "history"
        / snapshot.relative_path
    ).unlink()

    result = service.replay(
        HistoricalReplayRequest(
            snapshot_id=SNAPSHOT_ID,
            mode="NORMALIZED_HISTORICAL_VIEW",
        )
    )

    assert result.is_normalized_view


def test_unsupported_recalculation_is_rejected_before_replay(
    tmp_path: Path,
) -> None:
    service, _, _ = setup_service(
        tmp_path
    )

    with pytest.raises(
        NotImplementedError,
        match="defined but not supported",
    ):
        service.replay(
            HistoricalReplayRequest(
                snapshot_id=SNAPSHOT_ID,
                mode="CURRENT_CODE_RECALCULATION",
            )
        )


def test_replay_rejects_missing_snapshot(
    tmp_path: Path,
) -> None:
    service, _, _ = setup_service(
        tmp_path
    )

    with pytest.raises(
        KeyError,
        match="No historical snapshot found",
    ):
        service.replay(
            HistoricalReplayRequest(
                snapshot_id=(
                    "f9b7adca-2f2b-47a4-901d-05ca37c445df"
                ),
                mode="EXACT_ARCHIVED_PACKAGE",
            )
        )


def test_replay_rejects_wrong_request_type(
    tmp_path: Path,
) -> None:
    service, _, _ = setup_service(
        tmp_path
    )

    with pytest.raises(
        TypeError,
        match="request must be a HistoricalReplayRequest",
    ):
        service.replay(
            object()  # type: ignore[arg-type]
        )
