"""
Tests for HistoricalImportState.
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.history.historical_import_state_models import (
    HistoricalImportState,
)


SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
BASE_TIME = datetime(
    2026,
    8,
    8,
    10,
    0,
    tzinfo=timezone.utc,
)


def create_state(
    **overrides,
) -> HistoricalImportState:
    values = {
        "snapshot_id": SNAPSHOT_ID,
        "status": "METADATA_ONLY",
        "metadata_synchronized_at": BASE_TIME,
        "updated_at": BASE_TIME,
        "package_verified_at": None,
        "details_imported_at": None,
        "timeline_built_at": None,
        "importer_version": None,
        "failure_reason": None,
    }
    values.update(
        overrides
    )
    return HistoricalImportState(
        **values
    )


def test_metadata_only_state_serializes() -> None:
    state = create_state(
        snapshot_id=SNAPSHOT_ID.upper(),
        status=" metadata_only ",
    )

    assert state.snapshot_id == SNAPSHOT_ID
    assert state.status == "METADATA_ONLY"
    assert state.to_dict() == {
        "snapshot_id": SNAPSHOT_ID,
        "status": "METADATA_ONLY",
        "metadata_synchronized_at": BASE_TIME.isoformat(),
        "package_verified_at": None,
        "details_imported_at": None,
        "timeline_built_at": None,
        "importer_version": None,
        "failure_reason": None,
        "updated_at": BASE_TIME.isoformat(),
    }


def test_imported_state_requires_complete_timestamps() -> None:
    verified_at = BASE_TIME + timedelta(
        minutes=1
    )
    timeline_at = BASE_TIME + timedelta(
        minutes=2
    )
    imported_at = BASE_TIME + timedelta(
        minutes=3
    )

    state = create_state(
        status="IMPORTED",
        package_verified_at=verified_at,
        timeline_built_at=timeline_at,
        details_imported_at=imported_at,
        importer_version="0.13.0",
        updated_at=imported_at,
    )

    assert state.status == "IMPORTED"
    assert state.importer_version == "0.13.0"


@pytest.mark.parametrize(
    "status",
    (
        "VERIFIED",
        "IMPORTING",
        "IMPORTED",
    ),
)
def test_verified_or_later_requires_verification_time(
    status: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=f"{status} requires package_verified_at",
    ):
        create_state(
            status=status
        )


def test_imported_requires_detail_and_timeline_times() -> None:
    verified_at = BASE_TIME + timedelta(
        minutes=1
    )

    with pytest.raises(
        ValueError,
        match="IMPORTED requires details_imported_at",
    ):
        create_state(
            status="IMPORTED",
            package_verified_at=verified_at,
            updated_at=verified_at,
        )

    with pytest.raises(
        ValueError,
        match="IMPORTED requires timeline_built_at",
    ):
        create_state(
            status="IMPORTED",
            package_verified_at=verified_at,
            details_imported_at=verified_at,
            updated_at=verified_at,
        )


def test_failed_requires_failure_reason() -> None:
    with pytest.raises(
        ValueError,
        match="FAILED requires failure_reason",
    ):
        create_state(
            status="FAILED"
        )


def test_failure_reason_is_rejected_outside_failed_state() -> None:
    with pytest.raises(
        ValueError,
        match="failure_reason is only valid for FAILED state",
    ):
        create_state(
            failure_reason="unexpected"
        )


def test_state_validates_transition_graph() -> None:
    metadata = create_state()

    assert metadata.can_transition_to(
        "VERIFIED"
    )
    assert metadata.can_transition_to(
        "FAILED"
    )
    assert not metadata.can_transition_to(
        "IMPORTED"
    )

    with pytest.raises(
        ValueError,
        match="METADATA_ONLY -> IMPORTED",
    ):
        metadata.require_transition_to(
            "IMPORTED"
        )

    imported = create_state(
        status="IMPORTED",
        package_verified_at=BASE_TIME,
        details_imported_at=BASE_TIME,
        timeline_built_at=BASE_TIME,
        updated_at=BASE_TIME,
    )

    assert not imported.can_transition_to(
        "FAILED"
    )


def test_failed_state_can_retry_through_verified() -> None:
    failed = create_state(
        status="FAILED",
        failure_reason="checksum mismatch",
    )

    assert failed.require_transition_to(
        " verified "
    ) == "VERIFIED"


def test_state_rejects_invalid_status() -> None:
    with pytest.raises(
        ValueError,
        match="status must be one of",
    ):
        create_state(
            status="UNKNOWN"
        )


def test_state_rejects_naive_timestamp() -> None:
    with pytest.raises(
        ValueError,
        match="metadata_synchronized_at must be timezone-aware",
    ):
        create_state(
            metadata_synchronized_at=datetime(
                2026,
                8,
                8,
                10,
                0,
            )
        )


def test_state_rejects_timestamp_before_metadata_sync() -> None:
    with pytest.raises(
        ValueError,
        match="package_verified_at must not be earlier",
    ):
        create_state(
            status="VERIFIED",
            package_verified_at=BASE_TIME - timedelta(
                seconds=1
            ),
        )


def test_state_rejects_timestamp_after_updated_at() -> None:
    with pytest.raises(
        ValueError,
        match="package_verified_at must not be later than updated_at",
    ):
        create_state(
            status="VERIFIED",
            package_verified_at=BASE_TIME + timedelta(
                seconds=1
            ),
        )
