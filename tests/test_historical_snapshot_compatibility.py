"""
Tests for HistoricalSnapshotCompatibilityService.
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.history.historical_comparison_facts import (
    HistoricalComparisonFacts,
)
from investment_terminal.history.historical_import_state_models import (
    HistoricalImportState,
)
from investment_terminal.history.historical_snapshot_compatibility import (
    HistoricalSnapshotCompatibilityService,
    SnapshotCompatibilityResult,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)


FIRST_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
SECOND_ID = (
    "f9b7adca-2f2b-47a4-901d-05ca37c445df"
)
BASE_TIME = datetime(
    2026,
    8,
    3,
    17,
    35,
    tzinfo=timezone.utc,
)


def snapshot(
    snapshot_id: str,
    *,
    generated_at: datetime,
    schema_version: str = "1.0",
) -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=snapshot_id,
        package_id=f"review-{snapshot_id[:8]}",
        package_schema_version=schema_version,
        product_version="0.13.0",
        generated_at=generated_at,
        archived_at=generated_at + timedelta(
            minutes=1
        ),
        relative_path=(
            f"{generated_at:%Y/%m}/{snapshot_id}.json"
        ),
        checksum_sha256="a" * 64,
        status="ARCHIVED",
    )


def imported_state(
    snapshot_id: str,
) -> HistoricalImportState:
    return HistoricalImportState(
        snapshot_id=snapshot_id,
        status="IMPORTED",
        metadata_synchronized_at=BASE_TIME,
        package_verified_at=BASE_TIME,
        details_imported_at=BASE_TIME,
        timeline_built_at=BASE_TIME,
        importer_version="0.13.0",
        updated_at=BASE_TIME,
    )


def facts(
    snapshot_id: str,
    *,
    portfolio_name: str = "Main Portfolio",
    base_currency: str = "EUR",
    source_status: str = "MARKET_VALUE_CONNECTED",
) -> HistoricalComparisonFacts:
    return HistoricalComparisonFacts(
        snapshot_id=snapshot_id,
        portfolio_summary_present=True,
        portfolio_name=portfolio_name,
        base_currency=base_currency,
        source_status=source_status,
        holdings_count=2,
        recommendations_count=1,
        deployment_count=1,
        timeline_event_count=6,
    )


def service() -> HistoricalSnapshotCompatibilityService:
    return HistoricalSnapshotCompatibilityService(
        supported_package_schemas=(
            "1.0",
        )
    )


def test_compatible_snapshots() -> None:
    earlier = snapshot(
        FIRST_ID,
        generated_at=BASE_TIME,
    )
    later = snapshot(
        SECOND_ID,
        generated_at=BASE_TIME + timedelta(
            days=1
        ),
    )

    result = service().assess(
        earlier_snapshot=earlier,
        later_snapshot=later,
        earlier_state=imported_state(
            FIRST_ID
        ),
        later_state=imported_state(
            SECOND_ID
        ),
        earlier_facts=facts(
            FIRST_ID
        ),
        later_facts=facts(
            SECOND_ID
        ),
    )

    assert result == SnapshotCompatibilityResult(
        earlier_snapshot_id=FIRST_ID,
        later_snapshot_id=SECOND_ID,
        status="COMPATIBLE",
        blockers=(),
        warnings=(),
        source_status_changed=False,
    )
    assert result.may_compare


def test_wrong_chronology_is_incompatible() -> None:
    earlier = snapshot(
        FIRST_ID,
        generated_at=BASE_TIME + timedelta(
            days=1
        ),
    )
    later = snapshot(
        SECOND_ID,
        generated_at=BASE_TIME,
    )

    result = service().assess(
        earlier_snapshot=earlier,
        later_snapshot=later,
        earlier_state=imported_state(
            FIRST_ID
        ),
        later_state=imported_state(
            SECOND_ID
        ),
        earlier_facts=facts(
            FIRST_ID
        ),
        later_facts=facts(
            SECOND_ID
        ),
    )

    assert result.status == "INCOMPATIBLE"
    assert not result.may_compare
    assert (
        "Earlier snapshot generated_at must precede later snapshot"
        in result.blockers
    )


def test_unsupported_schema_is_incompatible() -> None:
    earlier = snapshot(
        FIRST_ID,
        generated_at=BASE_TIME,
        schema_version="9.0",
    )
    later = snapshot(
        SECOND_ID,
        generated_at=BASE_TIME + timedelta(
            days=1
        ),
    )

    result = service().assess(
        earlier_snapshot=earlier,
        later_snapshot=later,
        earlier_state=imported_state(
            FIRST_ID
        ),
        later_state=imported_state(
            SECOND_ID
        ),
        earlier_facts=facts(
            FIRST_ID
        ),
        later_facts=facts(
            SECOND_ID
        ),
    )

    assert result.status == "INCOMPATIBLE"
    assert (
        "Earlier snapshot package schema is not supported"
        in result.blockers
    )


@pytest.mark.parametrize(
    ("field_name", "earlier_value", "later_value", "message"),
    (
        (
            "portfolio_name",
            "Portfolio A",
            "Portfolio B",
            "Portfolio identity does not match",
        ),
        (
            "base_currency",
            "EUR",
            "USD",
            "Base currency does not match",
        ),
    ),
)
def test_identity_or_currency_mismatch_is_incompatible(
    field_name: str,
    earlier_value: str,
    later_value: str,
    message: str,
) -> None:
    earlier = snapshot(
        FIRST_ID,
        generated_at=BASE_TIME,
    )
    later = snapshot(
        SECOND_ID,
        generated_at=BASE_TIME + timedelta(
            days=1
        ),
    )

    earlier_kwargs = {
        "portfolio_name": "Main Portfolio",
        "base_currency": "EUR",
    }
    later_kwargs = dict(
        earlier_kwargs
    )
    earlier_kwargs[
        field_name
    ] = earlier_value
    later_kwargs[
        field_name
    ] = later_value

    result = service().assess(
        earlier_snapshot=earlier,
        later_snapshot=later,
        earlier_state=imported_state(
            FIRST_ID
        ),
        later_state=imported_state(
            SECOND_ID
        ),
        earlier_facts=facts(
            FIRST_ID,
            **earlier_kwargs,
        ),
        later_facts=facts(
            SECOND_ID,
            **later_kwargs,
        ),
    )

    assert result.status == "INCOMPATIBLE"
    assert message in result.blockers


def test_source_status_difference_is_exposed_as_partial() -> None:
    earlier = snapshot(
        FIRST_ID,
        generated_at=BASE_TIME,
    )
    later = snapshot(
        SECOND_ID,
        generated_at=BASE_TIME + timedelta(
            days=1
        ),
    )

    result = service().assess(
        earlier_snapshot=earlier,
        later_snapshot=later,
        earlier_state=imported_state(
            FIRST_ID
        ),
        later_state=imported_state(
            SECOND_ID
        ),
        earlier_facts=facts(
            FIRST_ID,
            source_status="COST_BASIS_ONLY",
        ),
        later_facts=facts(
            SECOND_ID,
            source_status="MARKET_VALUE_CONNECTED",
        ),
    )

    assert result.status == "PARTIALLY_COMPATIBLE"
    assert result.source_status_changed
    assert (
        "Portfolio source status differs between snapshots"
        in result.warnings
    )


def test_missing_details_are_visible_as_partial() -> None:
    earlier = snapshot(
        FIRST_ID,
        generated_at=BASE_TIME,
    )
    later = snapshot(
        SECOND_ID,
        generated_at=BASE_TIME + timedelta(
            days=1
        ),
    )
    empty_facts = HistoricalComparisonFacts(
        snapshot_id=FIRST_ID,
        portfolio_summary_present=False,
        portfolio_name=None,
        base_currency=None,
        source_status=None,
        holdings_count=0,
        recommendations_count=0,
        deployment_count=0,
        timeline_event_count=0,
    )

    result = service().assess(
        earlier_snapshot=earlier,
        later_snapshot=later,
        earlier_state=imported_state(
            FIRST_ID
        ),
        later_state=imported_state(
            SECOND_ID
        ),
        earlier_facts=empty_facts,
        later_facts=facts(
            SECOND_ID
        ),
    )

    assert result.status == "PARTIALLY_COMPATIBLE"
    assert (
        "Earlier snapshot portfolio summary is missing"
        in result.warnings
    )
    assert (
        "Earlier snapshot has no structured detail rows"
        in result.warnings
    )


def test_non_imported_state_is_visible_as_partial() -> None:
    earlier = snapshot(
        FIRST_ID,
        generated_at=BASE_TIME,
    )
    later = snapshot(
        SECOND_ID,
        generated_at=BASE_TIME + timedelta(
            days=1
        ),
    )
    metadata_only = HistoricalImportState(
        snapshot_id=FIRST_ID,
        status="METADATA_ONLY",
        metadata_synchronized_at=BASE_TIME,
        updated_at=BASE_TIME,
    )

    result = service().assess(
        earlier_snapshot=earlier,
        later_snapshot=later,
        earlier_state=metadata_only,
        later_state=imported_state(
            SECOND_ID
        ),
        earlier_facts=facts(
            FIRST_ID
        ),
        later_facts=facts(
            SECOND_ID
        ),
    )

    assert result.status == "PARTIALLY_COMPATIBLE"
    assert (
        "One or both snapshots do not have IMPORTED state"
        in result.warnings
    )


def test_service_rejects_mismatched_fact_identity() -> None:
    earlier = snapshot(
        FIRST_ID,
        generated_at=BASE_TIME,
    )
    later = snapshot(
        SECOND_ID,
        generated_at=BASE_TIME + timedelta(
            days=1
        ),
    )

    with pytest.raises(
        ValueError,
        match="earlier_facts does not belong",
    ):
        service().assess(
            earlier_snapshot=earlier,
            later_snapshot=later,
            earlier_state=imported_state(
                FIRST_ID
            ),
            later_state=imported_state(
                SECOND_ID
            ),
            earlier_facts=facts(
                SECOND_ID
            ),
            later_facts=facts(
                SECOND_ID
            ),
        )
