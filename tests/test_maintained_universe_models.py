"""Tests for maintained asset-universe contracts."""

from datetime import datetime, timezone

import pytest

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


AS_OF = datetime(2026, 8, 1, tzinfo=timezone.utc)
CHECKED_AT = datetime(2026, 8, 2, tzinfo=timezone.utc)


def stock(symbol: str, name: str, exchange: str) -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol=symbol,
        name=name,
        instrument_type="STOCK",
        currency="USD",
        exchange_ticker=symbol,
        exchange_code=exchange,
    )


def member(symbol: str, name: str, exchange: str) -> AssetUniverseMember:
    return AssetUniverseMember(
        instrument=stock(symbol, name, exchange),
        included_at=AS_OF,
        inclusion_reason="Eligible large-cap listing",
    )


def universe() -> MaintainedAssetUniverse:
    return MaintainedAssetUniverse(
        universe_id="us_large_cap",
        version=3,
        name="US Large Cap",
        as_of=AS_OF,
        members=(
            member("MSFT", "Microsoft", "XNAS"),
            member("AAPL", "Apple", "XNAS"),
        ),
        description="Maintained discovery universe.",
    )


def test_universe_normalizes_identity_and_orders_members() -> None:
    snapshot = universe()

    assert snapshot.universe_id == "US_LARGE_CAP"
    assert snapshot.universe_key == "US_LARGE_CAP@3"
    assert snapshot.size == 2
    assert tuple(item.instrument.symbol for item in snapshot.members) == (
        "AAPL",
        "MSFT",
    )
    assert snapshot.contains("xnas:msft") is True


def test_universe_serialization_preserves_canonical_identity() -> None:
    payload = universe().to_dict()

    assert payload["universe_key"] == "US_LARGE_CAP@3"
    assert payload["as_of"] == AS_OF.isoformat()
    assert payload["members"][0]["instrument"]["instrument_key"] == (
        "XNAS:AAPL"
    )
    assert payload["members"][0]["inclusion_reason"] == (
        "Eligible large-cap listing"
    )


def test_universe_rejects_duplicate_instrument_identity() -> None:
    duplicate = member("MSFT", "Microsoft", "XNAS")

    with pytest.raises(ValueError, match="unique instrument"):
        MaintainedAssetUniverse(
            universe_id="US_LARGE_CAP",
            version=1,
            name="US Large Cap",
            as_of=AS_OF,
            members=(duplicate, duplicate),
        )


def test_universe_rejects_member_included_after_snapshot() -> None:
    future_member = AssetUniverseMember(
        instrument=stock("MSFT", "Microsoft", "XNAS"),
        included_at=CHECKED_AT,
    )

    with pytest.raises(ValueError, match="included after as_of"):
        MaintainedAssetUniverse(
            universe_id="US_LARGE_CAP",
            version=1,
            name="US Large Cap",
            as_of=AS_OF,
            members=(future_member,),
        )


def test_evidence_preserves_provenance_and_quality() -> None:
    provenance = MarketMetadataProvenance(
        source="exchange_reference",
        source_record_id="US-LARGE-CAP-2026-08",
        observed_at=AS_OF,
        fetched_at=AS_OF,
        checksum_sha256="a" * 64,
    )
    quality = MarketMetadataQualityService.assess(
        provenance,
        checked_at=CHECKED_AT,
        maximum_age_days=7,
    )
    evidence = MaintainedAssetUniverseEvidence(
        universe=universe(), provenance=provenance, quality=quality
    )

    assert evidence.to_dict()["quality"]["status"] == "READY"
    assert evidence.to_dict()["provenance"]["source"] == "EXCHANGE_REFERENCE"


def test_evidence_requires_matching_observation_time() -> None:
    provenance = MarketMetadataProvenance(
        source="TEST",
        observed_at=CHECKED_AT,
        fetched_at=CHECKED_AT,
    )
    quality = MarketMetadataQualityService.assess(
        provenance,
        checked_at=CHECKED_AT,
        maximum_age_days=7,
    )

    with pytest.raises(ValueError, match="must equal universe.as_of"):
        MaintainedAssetUniverseEvidence(
            universe=universe(), provenance=provenance, quality=quality
        )
