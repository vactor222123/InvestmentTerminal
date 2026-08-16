"""
Tests for market-metadata source provenance and data quality.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.market.market_metadata_quality import (
    MarketMetadataProvenance,
    MarketMetadataQualityService,
)


def timestamp(day: int) -> datetime:
    return datetime(
        2026,
        8,
        day,
        12,
        0,
        tzinfo=timezone.utc,
    )


def complete_provenance() -> MarketMetadataProvenance:
    return MarketMetadataProvenance(
        source="exchange_reference",
        source_record_id="XETR",
        observed_at=timestamp(10),
        fetched_at=timestamp(10),
        checksum_sha256="a" * 64,
    )


def test_complete_fresh_provenance_is_ready() -> None:
    assessment = MarketMetadataQualityService.assess(
        complete_provenance(),
        checked_at=timestamp(12),
        maximum_age_days=7,
    )

    assert assessment.status == "READY"
    assert assessment.is_ready is True
    assert assessment.age_days == 2.0
    assert assessment.missing_provenance_fields == ()
    assert assessment.warnings == ()


def test_missing_optional_lineage_is_explicitly_partial() -> None:
    provenance = MarketMetadataProvenance(
        source="exchange_reference",
        observed_at=timestamp(10),
        fetched_at=timestamp(10),
    )

    assessment = MarketMetadataQualityService.assess(
        provenance,
        checked_at=timestamp(11),
        maximum_age_days=7,
    )

    assert assessment.status == "PARTIAL"
    assert assessment.missing_provenance_fields == (
        "source_record_id",
        "checksum_sha256",
    )
    assert assessment.warnings == (
        MarketMetadataQualityService.WARNING_PARTIAL,
    )


def test_stale_metadata_preserves_incomplete_lineage_warning() -> None:
    provenance = MarketMetadataProvenance(
        source="exchange_reference",
        observed_at=timestamp(1),
        fetched_at=timestamp(2),
        source_record_id="XETR",
    )

    assessment = MarketMetadataQualityService.assess(
        provenance,
        checked_at=timestamp(12),
        maximum_age_days=7,
    )

    assert assessment.status == "STALE"
    assert assessment.age_days == 11.0
    assert assessment.missing_provenance_fields == (
        "checksum_sha256",
    )
    assert assessment.warnings == (
        MarketMetadataQualityService.WARNING_STALE,
        MarketMetadataQualityService.WARNING_PARTIAL,
    )


def test_provenance_serialization_is_stable() -> None:
    data = complete_provenance().to_dict()

    assert data == {
        "source": "EXCHANGE_REFERENCE",
        "source_record_id": "XETR",
        "observed_at": timestamp(10).isoformat(),
        "fetched_at": timestamp(10).isoformat(),
        "checksum_sha256": "a" * 64,
        "is_fully_traceable": True,
    }


def test_provenance_rejects_fetch_before_observation() -> None:
    with pytest.raises(ValueError, match="fetched_at"):
        MarketMetadataProvenance(
            source="TEST",
            observed_at=timestamp(10),
            fetched_at=timestamp(9),
        )


@pytest.mark.parametrize(
    "checksum",
    [
        "a" * 63,
        "g" * 64,
    ],
)
def test_provenance_rejects_invalid_checksum(
    checksum: str,
) -> None:
    with pytest.raises(ValueError, match="checksum_sha256"):
        MarketMetadataProvenance(
            source="TEST",
            observed_at=timestamp(10),
            fetched_at=timestamp(10),
            checksum_sha256=checksum,
        )


def test_quality_rejects_check_before_observation() -> None:
    with pytest.raises(ValueError, match="checked_at"):
        MarketMetadataQualityService.assess(
            complete_provenance(),
            checked_at=timestamp(9),
            maximum_age_days=7,
        )
