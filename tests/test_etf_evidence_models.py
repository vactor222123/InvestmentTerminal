"""Tests for provider-independent ETF evidence contracts."""

from datetime import datetime, timezone
import pytest

from investment_terminal.market.etf_evidence_models import (
    ETFCharacteristics, ETFCharacteristicsEvidence,
)
from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.market.market_metadata_quality import (
    MarketMetadataProvenance, MarketMetadataQualityService,
)


def timestamp(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def identity(instrument_type: str = "ETF") -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol=" world ", name=" Global Equity Fund ",
        instrument_type=instrument_type, currency="eur",
        isin="IE00B4L5Y983" if instrument_type == "ETF" else None,
    )


def provenance() -> MarketMetadataProvenance:
    return MarketMetadataProvenance(
        source="fund_reference", source_record_id="IE00B4L5Y983",
        observed_at=timestamp(10), fetched_at=timestamp(10),
        checksum_sha256="a" * 64,
    )


def test_characteristics_normalize_and_serialize_stably() -> None:
    item = ETFCharacteristics(
        identity=identity(), asset_class=" Global Equity ",
        benchmark_name=" MSCI World ", replication_method=" Physical sampling ",
        distribution_policy=" Accumulating ", total_expense_ratio=0.002,
        assets_under_management=12_500_000_000,
        assets_under_management_currency=" usd ", holdings_count=1_421,
    )
    assert item.to_dict() == {
        "identity": identity().to_dict(), "asset_class": "Global Equity",
        "benchmark_name": "MSCI World", "replication_method": "Physical sampling",
        "distribution_policy": "Accumulating", "total_expense_ratio": 0.002,
        "assets_under_management": 12_500_000_000.0,
        "assets_under_management_currency": "USD", "holdings_count": 1_421,
        "missing_characteristics": [],
    }


def test_missing_characteristics_remain_explicit() -> None:
    item = ETFCharacteristics(identity=identity())
    assert item.missing_characteristics == item.characteristic_field_names()
    assert item.total_expense_ratio is None


def test_characteristics_reject_non_etf_identity() -> None:
    with pytest.raises(ValueError, match="describe an ETF"):
        ETFCharacteristics(identity=identity("STOCK"))


@pytest.mark.parametrize("value", [-0.01, 1.01, float("nan"), True])
def test_expense_ratio_rejects_invalid_values(value: object) -> None:
    with pytest.raises(ValueError, match="total_expense_ratio"):
        ETFCharacteristics(identity=identity(), total_expense_ratio=value)  # type: ignore[arg-type]


def test_aum_value_and_currency_are_atomic() -> None:
    with pytest.raises(ValueError, match="provided together"):
        ETFCharacteristics(identity=identity(), assets_under_management=100.0)


@pytest.mark.parametrize("value", [-1, 1.5, True])
def test_holdings_count_requires_non_negative_integer(value: object) -> None:
    with pytest.raises(ValueError, match="holdings_count"):
        ETFCharacteristics(identity=identity(), holdings_count=value)  # type: ignore[arg-type]


def test_evidence_serializes_facts_lineage_and_quality() -> None:
    source = provenance()
    quality = MarketMetadataQualityService.assess(
        source, checked_at=timestamp(12), maximum_age_days=7,
    )
    evidence = ETFCharacteristicsEvidence(
        characteristics=ETFCharacteristics(
            identity=identity(), asset_class="Global Equity"
        ), provenance=source, quality=quality,
    )
    data = evidence.to_dict()
    assert data["characteristics"]["identity"]["instrument_type"] == "ETF"
    assert data["characteristics"]["missing_characteristics"][0] == "benchmark_name"
    assert data["provenance"]["source"] == "FUND_REFERENCE"
    assert data["quality"]["status"] == "READY"


def test_evidence_rejects_quality_checked_before_observation() -> None:
    source = provenance()
    older = MarketMetadataProvenance(
        source="fund_reference", observed_at=timestamp(8), fetched_at=timestamp(8),
    )
    quality = MarketMetadataQualityService.assess(
        older, checked_at=timestamp(9), maximum_age_days=7,
    )
    with pytest.raises(ValueError, match="quality.checked_at"):
        ETFCharacteristicsEvidence(
            characteristics=ETFCharacteristics(identity=identity()),
            provenance=source, quality=quality,
        )
