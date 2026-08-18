"""Tests for append-only maintained-universe repository semantics."""

from datetime import datetime, timezone

import pytest

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.market.market_metadata_quality import (
    MarketMetadataProvenance,
    MarketMetadataQualityService,
)
from investment_terminal.universe.maintained_universe_models import (
    AssetUniverseMember,
    MaintainedAssetUniverse,
    MaintainedAssetUniverseEvidence,
)
from investment_terminal.universe.maintained_universe_repository import (
    InMemoryMaintainedAssetUniverseRepository,
    MaintainedAssetUniverseRepository,
)


def timestamp(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def instrument(symbol: str, exchange: str = "XNAS") -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol=symbol,
        name=f"{symbol} Asset",
        instrument_type="STOCK",
        currency="USD",
        exchange_ticker=symbol,
        exchange_code=exchange,
    )


def evidence(
    universe_id: str,
    version: int,
    day: int,
    *,
    instruments: tuple[InstrumentIdentity, ...] = (instrument("MSFT"),),
    source_record_id: str | None = None,
) -> MaintainedAssetUniverseEvidence:
    as_of = timestamp(day)
    universe = MaintainedAssetUniverse(
        universe_id=universe_id,
        version=version,
        name=universe_id,
        as_of=as_of,
        members=tuple(
            AssetUniverseMember(
                instrument=item,
                included_at=as_of,
            )
            for item in instruments
        ),
    )
    provenance = MarketMetadataProvenance(
        source="test_provider",
        source_record_id=(
            source_record_id
            if source_record_id is not None
            else f"{universe_id}-{version}"
        ),
        observed_at=as_of,
        fetched_at=as_of,
        checksum_sha256="a" * 64,
    )
    return MaintainedAssetUniverseEvidence(
        universe=universe,
        provenance=provenance,
        quality=MarketMetadataQualityService.assess(
            provenance,
            checked_at=as_of,
            maximum_age_days=7,
        ),
    )


def repository() -> InMemoryMaintainedAssetUniverseRepository:
    value = InMemoryMaintainedAssetUniverseRepository()
    assert isinstance(value, MaintainedAssetUniverseRepository)
    return value


def test_add_get_require_and_deterministic_order() -> None:
    repo = repository()
    later = evidence("US_LARGE_CAP", 2, 12)
    earlier = evidence("GLOBAL_EQUITY", 1, 11)
    repo.add(later)
    repo.add(earlier)

    assert repo.get(" global_equity@1 ") is earlier
    assert repo.require("US_LARGE_CAP@2") is later
    assert repo.list_all() == (earlier, later)


def test_missing_and_duplicate_identities_fail_closed() -> None:
    repo = repository()
    original = evidence("US_LARGE_CAP", 1, 10)
    repo.add(original)

    with pytest.raises(KeyError, match="No maintained asset universe"):
        repo.require("missing@1")
    with pytest.raises(ValueError, match="universe identity"):
        repo.add(evidence("US_LARGE_CAP", 1, 11))
    with pytest.raises(ValueError, match="source identity"):
        repo.add(evidence(
            "GLOBAL_EQUITY",
            1,
            11,
            source_record_id="US_LARGE_CAP-1",
        ))

    assert repo.require("US_LARGE_CAP@1") is original


def test_half_open_observation_query() -> None:
    repo = repository()
    first = evidence("US_LARGE_CAP", 1, 10)
    second = evidence("GLOBAL_EQUITY", 1, 11)
    third = evidence("US_LARGE_CAP", 2, 12)
    for item in (third, first, second):
        repo.add(item)

    assert repo.list_between(timestamp(10), timestamp(12)) == (
        first,
        second,
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        repo.list_between(datetime(2026, 8, 10), timestamp(12))
    with pytest.raises(ValueError, match="later than"):
        repo.list_between(timestamp(12), timestamp(10))


def test_universe_history_and_latest_are_explicit() -> None:
    repo = repository()
    first = evidence("US_LARGE_CAP", 1, 10)
    unrelated = evidence("GLOBAL_EQUITY", 1, 11)
    second = evidence("US_LARGE_CAP", 2, 12)
    for item in (second, unrelated, first):
        repo.add(item)

    assert repo.list_for_universe(" us_large_cap ") == (first, second)
    assert repo.latest("US_LARGE_CAP") is second
    assert repo.latest("MISSING") is None


def test_instrument_query_uses_canonical_instrument_key() -> None:
    repo = repository()
    microsoft = instrument("MSFT")
    apple = instrument("AAPL")
    first = evidence(
        "US_LARGE_CAP",
        1,
        10,
        instruments=(microsoft, apple),
    )
    second = evidence(
        "GLOBAL_EQUITY",
        1,
        11,
        instruments=(apple,),
    )
    repo.add(second)
    repo.add(first)

    assert repo.list_for_instrument(" xnas:msft ") == (first,)
    assert repo.list_for_instrument("XNAS:AAPL") == (first, second)


def test_same_observation_time_orders_by_identity_and_version() -> None:
    repo = repository()
    version_two = evidence("US_LARGE_CAP", 2, 10)
    global_equity = evidence("GLOBAL_EQUITY", 1, 10)
    version_one = evidence("US_LARGE_CAP", 1, 10)
    for item in (version_two, global_equity, version_one):
        repo.add(item)

    assert repo.list_all() == (
        global_equity,
        version_one,
        version_two,
    )


def test_add_rejects_wrong_type() -> None:
    with pytest.raises(TypeError, match="MaintainedAssetUniverseEvidence"):
        repository().add(object())  # type: ignore[arg-type]
