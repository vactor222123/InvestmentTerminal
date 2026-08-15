from datetime import datetime, timezone

import pytest

from investment_terminal.cli.history_knowledge import (
    HistoricalSnapshotKnowledgeSourceAdapter,
)
from investment_terminal.history.historical_import_state_models import (
    HistoricalImportState,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.knowledge.projection import (
    HistoricalSnapshotKnowledgeSource,
)


SNAPSHOT_ID = "11111111-1111-4111-8111-111111111111"


def dt(hour: int) -> datetime:
    return datetime(2026, 8, 15, hour, 0, tzinfo=timezone.utc)


def snapshot() -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=SNAPSHOT_ID,
        package_id="review-001",
        package_schema_version="1",
        product_version="27.0",
        generated_at=dt(10),
        archived_at=dt(11),
        relative_path="2026/08/review-001.json",
        checksum_sha256="a" * 64,
    )


def import_state(status: str) -> HistoricalImportState:
    verified_at = (
        dt(12)
        if status in ("VERIFIED", "IMPORTING", "IMPORTED")
        else None
    )
    imported_at = dt(13) if status == "IMPORTED" else None

    return HistoricalImportState(
        snapshot_id=SNAPSHOT_ID,
        status=status,
        metadata_synchronized_at=dt(11),
        package_verified_at=verified_at,
        details_imported_at=imported_at,
        timeline_built_at=imported_at,
        importer_version=(
            "27.0"
            if status in ("IMPORTING", "IMPORTED")
            else None
        ),
        failure_reason=(
            "verification failed"
            if status == "FAILED"
            else None
        ),
        updated_at=(
            dt(13)
            if status == "IMPORTED"
            else dt(12)
        ),
    )


@pytest.mark.parametrize(
    "status",
    ("VERIFIED", "IMPORTING", "IMPORTED"),
)
def test_adapt_verified_history_to_neutral_knowledge_source(
    status: str,
) -> None:
    result = HistoricalSnapshotKnowledgeSourceAdapter().adapt(
        snapshot(),
        import_state(status),
    )

    assert result == HistoricalSnapshotKnowledgeSource(
        snapshot_id=SNAPSHOT_ID,
        package_id="review-001",
        generated_at=dt(10),
        archived_at=dt(11),
        checksum_sha256="a" * 64,
    )


@pytest.mark.parametrize(
    "status",
    ("METADATA_ONLY", "FAILED"),
)
def test_adapt_rejects_history_without_current_verified_evidence(
    status: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="verified package evidence",
    ):
        HistoricalSnapshotKnowledgeSourceAdapter().adapt(
            snapshot(),
            import_state(status),
        )


def test_adapt_rejects_mismatched_snapshot_and_import_state() -> None:
    other_state = HistoricalImportState(
        snapshot_id="22222222-2222-4222-8222-222222222222",
        status="VERIFIED",
        metadata_synchronized_at=dt(11),
        package_verified_at=dt(12),
        updated_at=dt(12),
    )

    with pytest.raises(
        ValueError,
        match="snapshot_id must match",
    ):
        HistoricalSnapshotKnowledgeSourceAdapter().adapt(
            snapshot(),
            other_state,
        )


def test_adapt_requires_history_domain_models() -> None:
    adapter = HistoricalSnapshotKnowledgeSourceAdapter()

    with pytest.raises(
        TypeError,
        match="snapshot must be a HistoricalSnapshot",
    ):
        adapter.adapt(
            object(),  # type: ignore[arg-type]
            import_state("VERIFIED"),
        )

    with pytest.raises(
        TypeError,
        match="import_state must be a HistoricalImportState",
    ):
        adapter.adapt(
            snapshot(),
            object(),  # type: ignore[arg-type]
        )
