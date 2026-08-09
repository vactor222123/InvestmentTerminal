"""
Tests for the versioned expected historical archive-cadence contract.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.history.historical_archive_cadence import (
    HistoricalArchiveCadencePolicy,
)


ANCHOR = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


def test_fixed_interval_v1_is_explicit_and_versioned() -> None:
    policy = HistoricalArchiveCadencePolicy.fixed_interval_v1(
        anchor_at=ANCHOR,
        interval_seconds=86_400,
    )

    assert policy.cadence_id == "FIXED_INTERVAL_ARCHIVE_CADENCE"
    assert policy.version == 1
    assert policy.identity_key == "FIXED_INTERVAL_ARCHIVE_CADENCE@1"
    assert policy.timestamp_basis == "GENERATED_AT"
    assert policy.anchor_at == ANCHOR
    assert policy.interval_seconds == 86_400


def test_serialization_is_stable_and_json_ready() -> None:
    data = HistoricalArchiveCadencePolicy.fixed_interval_v1(
        anchor_at=ANCHOR,
        interval_seconds=3_600,
    ).to_dict()

    assert data == {
        "cadence_id": "FIXED_INTERVAL_ARCHIVE_CADENCE",
        "version": 1,
        "identity_key": "FIXED_INTERVAL_ARCHIVE_CADENCE@1",
        "timestamp_basis": "GENERATED_AT",
        "anchor_at": ANCHOR.isoformat(),
        "interval_seconds": 3_600,
    }


def test_naive_anchor_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="anchor_at must be timezone-aware",
    ):
        HistoricalArchiveCadencePolicy.fixed_interval_v1(
            anchor_at=datetime(
                2026,
                8,
                1,
                12,
                0,
            ),
            interval_seconds=86_400,
        )


@pytest.mark.parametrize(
    "value",
    (
        0,
        -1,
        True,
        1.5,
        "86400",
    ),
)
def test_invalid_interval_is_rejected(
    value: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="interval_seconds must be a positive integer",
    ):
        HistoricalArchiveCadencePolicy.fixed_interval_v1(
            anchor_at=ANCHOR,
            interval_seconds=value,  # type: ignore[arg-type]
        )


def test_unsupported_timestamp_basis_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="timestamp_basis must be one of",
    ):
        HistoricalArchiveCadencePolicy(
            cadence_id="CUSTOM",
            version=1,
            timestamp_basis="ARCHIVED_AT",
            anchor_at=ANCHOR,
            interval_seconds=86_400,
        )


def test_fixed_interval_identity_rejects_unknown_version() -> None:
    with pytest.raises(
        ValueError,
        match="supports only version 1",
    ):
        HistoricalArchiveCadencePolicy(
            cadence_id="FIXED_INTERVAL_ARCHIVE_CADENCE",
            version=2,
            timestamp_basis="GENERATED_AT",
            anchor_at=ANCHOR,
            interval_seconds=86_400,
        )


def test_contract_does_not_encode_calendar_or_holiday_semantics() -> None:
    data = HistoricalArchiveCadencePolicy.fixed_interval_v1(
        anchor_at=ANCHOR,
        interval_seconds=86_400,
    ).to_dict()

    assert "timezone" not in data
    assert "business_days" not in data
    assert "holidays" not in data
    assert "session_calendar" not in data
    assert "tolerance" not in data
