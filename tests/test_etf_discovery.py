"""Tests for deterministic ETF discovery evidence assembly."""

from datetime import datetime, timezone

import pytest

from investment_terminal.market.etf_composition_models import (
    ETFComposition,
    ETFCompositionEvidence,
)
from investment_terminal.market.etf_evidence_models import (
    ETFCharacteristics,
    ETFCharacteristicsEvidence,
)
from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.market.market_metadata_quality import (
    MarketMetadataProvenance,
    MarketMetadataQualityService,
)
from investment_terminal.universe.etf_discovery import (
    ETFDiscoveryEvidenceBuilder,
)
from investment_terminal.universe.maintained_universe_models import (
    AssetUniverseMember,
    MaintainedAssetUniverse,
    MaintainedAssetUniverseEvidence,
)


def timestamp(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def etf(symbol: str, isin: str) -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol=symbol,
        name=f"{symbol} ETF",
        instrument_type="ETF",
        currency="EUR",
        isin=isin,
    )


WORLD = etf("WORLD", "IE00B4L5Y983")
EM = etf("EM", "IE00BKM4GZ66")
STOCK = InstrumentIdentity(
    symbol="MSFT",
    name="Microsoft",
    instrument_type="STOCK",
    currency="USD",
    exchange_ticker="MSFT",
    exchange_code="XNAS",
)


def provenance(identity: str, day: int = 10) -> MarketMetadataProvenance:
    return MarketMetadataProvenance(
        source="test",
        source_record_id=identity,
        observed_at=timestamp(day),
        fetched_at=timestamp(day),
        checksum_sha256="a" * 64,
    )


def quality(source: MarketMetadataProvenance, checked_day: int = 11):
    return MarketMetadataQualityService.assess(
        source,
        checked_at=timestamp(checked_day),
        maximum_age_days=7,
    )


def universe(*instruments: InstrumentIdentity) -> MaintainedAssetUniverseEvidence:
    source = provenance("universe")
    return MaintainedAssetUniverseEvidence(
        universe=MaintainedAssetUniverse(
            universe_id="GLOBAL",
            version=1,
            name="Global",
            as_of=timestamp(10),
            members=tuple(
                AssetUniverseMember(
                    instrument=item,
                    included_at=timestamp(10),
                )
                for item in instruments
            ),
        ),
        provenance=source,
        quality=quality(source),
    )


def characteristics(
    instrument: InstrumentIdentity,
    *,
    day: int = 10,
) -> ETFCharacteristicsEvidence:
    source = provenance(f"characteristics-{instrument.symbol}", day)
    return ETFCharacteristicsEvidence(
        characteristics=ETFCharacteristics(
            identity=instrument,
            asset_class="Equity",
        ),
        provenance=source,
        quality=quality(source, checked_day=max(day, 11)),
    )


def composition(
    instrument: InstrumentIdentity,
) -> ETFCompositionEvidence:
    source = provenance(f"composition-{instrument.symbol}")
    return ETFCompositionEvidence(
        composition=ETFComposition(
            identity=instrument,
            holdings=(),
            exposures=(),
        ),
        provenance=source,
        quality=quality(source),
    )


def test_builder_joins_etf_evidence_and_excludes_non_etf_members() -> None:
    result = ETFDiscoveryEvidenceBuilder.build(
        universe(WORLD, STOCK, EM),
        assessed_at=timestamp(12),
        characteristics=(characteristics(WORLD), characteristics(EM)),
        compositions=(composition(WORLD), composition(EM)),
    )

    assert tuple(
        item.instrument.instrument_key for item in result.candidates
    ) == ("IE00B4L5Y983", "IE00BKM4GZ66")
    assert result.status_counts == {
        "READY": 2,
        "PARTIAL": 0,
        "STALE": 0,
    }
    assert result.all_ready is True
    assert result.to_dict()["candidate_count"] == 2


def test_missing_evidence_remains_explicit_and_partial() -> None:
    result = ETFDiscoveryEvidenceBuilder.build(
        universe(WORLD, EM),
        assessed_at=timestamp(12),
        characteristics=(characteristics(WORLD),),
    )

    world, emerging = result.candidates
    assert world.missing_evidence == ("COMPOSITION",)
    assert emerging.missing_evidence == (
        "CHARACTERISTICS",
        "COMPOSITION",
    )
    assert result.status_counts["PARTIAL"] == 2
    assert result.all_ready is False


def test_stale_source_makes_candidate_stale() -> None:
    source = provenance("stale", day=1)
    stale = ETFCharacteristicsEvidence(
        characteristics=ETFCharacteristics(identity=WORLD),
        provenance=source,
        quality=MarketMetadataQualityService.assess(
            source,
            checked_at=timestamp(11),
            maximum_age_days=3,
        ),
    )
    result = ETFDiscoveryEvidenceBuilder.build(
        universe(WORLD),
        assessed_at=timestamp(12),
        characteristics=(stale,),
        compositions=(composition(WORLD),),
    )

    assert result.candidates[0].quality_status == "STALE"


def test_empty_etf_population_is_explicitly_not_ready() -> None:
    result = ETFDiscoveryEvidenceBuilder.build(
        universe(STOCK),
        assessed_at=timestamp(12),
    )

    assert result.candidates == ()
    assert result.all_ready is False


def test_out_of_universe_evidence_fails_closed() -> None:
    with pytest.raises(ValueError, match="outside the universe"):
        ETFDiscoveryEvidenceBuilder.build(
            universe(WORLD),
            assessed_at=timestamp(12),
            characteristics=(characteristics(EM),),
        )


def test_duplicate_evidence_identity_fails_closed() -> None:
    item = characteristics(WORLD)
    with pytest.raises(ValueError, match="duplicate instrument"):
        ETFDiscoveryEvidenceBuilder.build(
            universe(WORLD),
            assessed_at=timestamp(12),
            characteristics=(item, item),
        )


def test_future_evidence_fails_closed() -> None:
    with pytest.raises(ValueError, match="later than assessed_at"):
        ETFDiscoveryEvidenceBuilder.build(
            universe(WORLD),
            assessed_at=timestamp(12),
            characteristics=(characteristics(WORLD, day=13),),
        )


def test_conflicting_full_identity_fails_closed() -> None:
    renamed = InstrumentIdentity(
        symbol="WORLD",
        name="Renamed ETF",
        instrument_type="ETF",
        currency="EUR",
        isin="IE00B4L5Y983",
    )
    with pytest.raises(ValueError, match="identity must match"):
        ETFDiscoveryEvidenceBuilder.build(
            universe(WORLD),
            assessed_at=timestamp(12),
            characteristics=(characteristics(renamed),),
        )
