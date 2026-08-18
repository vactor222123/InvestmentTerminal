"""Tests for maintained-universe sector analysis evidence."""

from datetime import datetime, timezone

import pytest

from investment_terminal.market.company_classification_models import (
    CompanyClassification,
)
from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.market.market_metadata_quality import (
    MarketMetadataProvenance,
    MarketMetadataQualityService,
)
from investment_terminal.universe.maintained_universe_models import (
    AssetUniverseMember,
    MaintainedAssetUniverse,
    MaintainedAssetUniverseEvidence,
)
from investment_terminal.universe.sector_analysis import (
    SectorAnalysisEvidenceBuilder,
)


def ts(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def stock(symbol: str, exchange: str = "XNAS") -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol=symbol, name=symbol, instrument_type="STOCK", currency="USD",
        exchange_ticker=symbol, exchange_code=exchange,
    )


def universe(*items: InstrumentIdentity) -> MaintainedAssetUniverseEvidence:
    source = MarketMetadataProvenance(
        source="test", source_record_id="u1", observed_at=ts(10),
        fetched_at=ts(10), checksum_sha256="a" * 64,
    )
    return MaintainedAssetUniverseEvidence(
        MaintainedAssetUniverse(
            "GLOBAL", 1, "Global", ts(10),
            tuple(AssetUniverseMember(item, ts(10)) for item in items),
        ),
        source,
        MarketMetadataQualityService.assess(
            source, checked_at=ts(11), maximum_age_days=7,
        ),
    )


def classification(symbol: str, sector: str, industry: str):
    return CompanyClassification(symbol, sector, industry)


def test_groups_classified_stocks_and_excludes_etfs() -> None:
    etf = InstrumentIdentity(
        symbol="WORLD", name="World", instrument_type="ETF", currency="EUR",
        isin="IE00B4L5Y983",
    )
    result = SectorAnalysisEvidenceBuilder.build(
        universe(stock("MSFT"), stock("JPM", "XNYS"), stock("V"), etf),
        (
            classification("MSFT", "Technology", "Software"),
            classification("JPM", "Financials", "Banks"),
            classification("V", "Financials", "Payments"),
        ),
        assessed_at=ts(12),
    )
    assert tuple(item.sector for item in result.sectors) == (
        "Financials", "Technology",
    )
    assert result.sectors[0].industry_counts == {"Banks": 1, "Payments": 1}
    assert result.coverage == 1.0
    assert result.quality_status == "READY"
    assert result.to_dict()["classified_instrument_count"] == 3


def test_missing_classification_is_explicit_and_partial() -> None:
    result = SectorAnalysisEvidenceBuilder.build(
        universe(stock("MSFT"), stock("UNKNOWN")),
        (classification("MSFT", "Technology", "Software"),),
        assessed_at=ts(12),
    )
    assert result.unclassified_instrument_keys == ("XNAS:UNKNOWN",)
    assert result.coverage == 0.5
    assert result.quality_status == "PARTIAL"


def test_no_stock_population_is_explicitly_partial() -> None:
    etf = InstrumentIdentity(
        symbol="WORLD", name="World", instrument_type="ETF", currency="EUR",
        isin="IE00B4L5Y983",
    )
    result = SectorAnalysisEvidenceBuilder.build(
        universe(etf), (), assessed_at=ts(12),
    )
    assert result.eligible_instrument_count == 0
    assert result.coverage == 0.0
    assert result.quality_status == "PARTIAL"


def test_out_of_universe_and_duplicate_classifications_fail_closed() -> None:
    value = universe(stock("MSFT"))
    with pytest.raises(ValueError, match="outside universe"):
        SectorAnalysisEvidenceBuilder.build(
            value, (classification("AAPL", "Technology", "Hardware"),),
            assessed_at=ts(12),
        )
    item = classification("MSFT", "Technology", "Software")
    with pytest.raises(ValueError, match="duplicate symbol"):
        SectorAnalysisEvidenceBuilder.build(
            value, (item, item), assessed_at=ts(12),
        )


def test_exchange_duplicate_symbol_fails_as_ambiguous() -> None:
    with pytest.raises(ValueError, match="symbols must be unique"):
        SectorAnalysisEvidenceBuilder.build(
            universe(stock("ABC", "XNAS"), stock("ABC", "XNYS")),
            (classification("ABC", "Technology", "Software"),),
            assessed_at=ts(12),
        )
