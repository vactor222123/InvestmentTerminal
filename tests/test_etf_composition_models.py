"""Tests for ETF holdings and exposure composition contracts."""

from datetime import datetime, timezone

import pytest

from investment_terminal.market.etf_composition_models import (
    ETFComposition,
    ETFCompositionEvidence,
    ETFConstituentHolding,
    ETFExposure,
)
from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.market.market_metadata_quality import (
    MarketMetadataProvenance,
    MarketMetadataQualityService,
)


def identity(
    symbol: str = "WORLD",
    instrument_type: str = "ETF",
) -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol=symbol,
        name=f"{symbol} instrument",
        instrument_type=instrument_type,
        currency="EUR",
        isin=("IE00B4L5Y983" if instrument_type == "ETF" else None),
    )


def timestamp(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def composition() -> ETFComposition:
    return ETFComposition(
        identity=identity(),
        holdings=(
            ETFConstituentHolding(
                name="Company A",
                weight=0.05,
                identity=identity("AAA", "STOCK"),
            ),
            ETFConstituentHolding(name="Company B", weight=0.03),
        ),
        exposures=(
            ETFExposure(dimension="country", label="United States", weight=0.7),
            ETFExposure(dimension="country", label="Germany", weight=0.1),
            ETFExposure(dimension="sector", label="Technology", weight=0.25),
        ),
        holdings_scope="Top reported holdings",
    )


def test_composition_serializes_explicit_partial_coverage() -> None:
    data = composition().to_dict()

    assert data["identity"]["instrument_type"] == "ETF"
    assert data["holdings_scope"] == "Top reported holdings"
    assert data["holdings_coverage"] == 0.08
    assert data["exposure_coverage"] == {
        "COUNTRY": 0.8,
        "SECTOR": 0.25,
    }
    assert data["holdings"][0]["holding_key"] == "AAA"
    assert data["holdings"][1]["identity"] is None
    assert data["exposures"][0]["exposure_key"] == "COUNTRY:UNITED STATES"


def test_composition_rejects_non_etf_identity() -> None:
    with pytest.raises(ValueError, match="describe an ETF"):
        ETFComposition(
            identity=identity("AAA", "STOCK"),
            holdings=(),
            exposures=(),
        )


@pytest.mark.parametrize("weight", [-0.01, 1.01, float("nan"), True])
def test_holding_rejects_invalid_weight(weight: object) -> None:
    with pytest.raises(ValueError, match="weight"):
        ETFConstituentHolding(name="Company", weight=weight)  # type: ignore[arg-type]


def test_composition_rejects_duplicate_holding_keys() -> None:
    with pytest.raises(ValueError, match="unique holding keys"):
        ETFComposition(
            identity=identity(),
            holdings=(
                ETFConstituentHolding(name=" Company A ", weight=0.1),
                ETFConstituentHolding(name="company a", weight=0.2),
            ),
            exposures=(),
        )


def test_composition_rejects_duplicate_exposure_keys() -> None:
    with pytest.raises(ValueError, match="unique dimension/label"):
        ETFComposition(
            identity=identity(),
            holdings=(),
            exposures=(
                ETFExposure(dimension="country", label=" Germany ", weight=0.4),
                ETFExposure(dimension="COUNTRY", label="germany", weight=0.4),
            ),
        )


def test_composition_rejects_holding_weight_above_total() -> None:
    with pytest.raises(ValueError, match="holdings weights"):
        ETFComposition(
            identity=identity(),
            holdings=(
                ETFConstituentHolding(name="A", weight=0.6),
                ETFConstituentHolding(name="B", weight=0.5),
            ),
            exposures=(),
        )


def test_composition_rejects_dimension_weight_above_total() -> None:
    with pytest.raises(ValueError, match="COUNTRY exposures"):
        ETFComposition(
            identity=identity(),
            holdings=(),
            exposures=(
                ETFExposure(dimension="country", label="A", weight=0.6),
                ETFExposure(dimension="country", label="B", weight=0.5),
            ),
        )


def test_empty_composition_preserves_zero_coverage() -> None:
    item = ETFComposition(identity=identity(), holdings=(), exposures=())

    assert item.holdings_coverage == 0.0
    assert item.exposure_coverage == {}


def test_evidence_serializes_composition_lineage_and_quality() -> None:
    provenance = MarketMetadataProvenance(
        source="fund_composition",
        source_record_id="IE00B4L5Y983",
        observed_at=timestamp(10),
        fetched_at=timestamp(10),
        checksum_sha256="b" * 64,
    )
    quality = MarketMetadataQualityService.assess(
        provenance,
        checked_at=timestamp(11),
        maximum_age_days=7,
    )

    data = ETFCompositionEvidence(
        composition=composition(),
        provenance=provenance,
        quality=quality,
    ).to_dict()

    assert data["composition"]["holdings_coverage"] == 0.08
    assert data["provenance"]["source"] == "FUND_COMPOSITION"
    assert data["quality"]["status"] == "READY"
