"""Tests for provider-neutral maintained-universe ingestion."""

from datetime import datetime, timezone

import pytest

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.market.market_metadata_quality import (
    MarketMetadataProvenance,
)
from investment_terminal.universe.maintained_universe_ingestion import (
    MaintainedAssetUniverseIngestionService,
    MaintainedAssetUniverseQuery,
    MaintainedAssetUniverseSourceItem,
)
from investment_terminal.universe.maintained_universe_models import (
    AssetUniverseMember,
    MaintainedAssetUniverse,
)


def timestamp(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def query(**overrides) -> MaintainedAssetUniverseQuery:
    values = {
        "universe_ids": ("us_large_cap", "global_etf"),
        "observed_from": timestamp(1),
        "observed_until": timestamp(10),
        "maximum_age_days": 7,
        "limit": 10,
    }
    values.update(overrides)
    return MaintainedAssetUniverseQuery(**values)


def source_item(
    universe_id: str,
    version: int,
    *,
    observed_at: datetime,
    source: str = "test_provider",
    source_record_id: str | None = None,
    checksum: str | None = "a" * 64,
) -> MaintainedAssetUniverseSourceItem:
    symbol = "SPY" if universe_id.upper() == "GLOBAL_ETF" else "MSFT"
    instrument = InstrumentIdentity(
        symbol=symbol,
        name=f"{symbol} Asset",
        instrument_type="STOCK",
        currency="USD",
        exchange_ticker=symbol,
        exchange_code="XNAS",
    )
    universe = MaintainedAssetUniverse(
        universe_id=universe_id,
        version=version,
        name=universe_id,
        as_of=observed_at,
        members=(AssetUniverseMember(
            instrument=instrument,
            included_at=observed_at,
        ),),
    )
    provenance = MarketMetadataProvenance(
        source=source,
        source_record_id=(
            source_record_id
            if source_record_id is not None
            else f"{universe_id}-{version}"
        ),
        observed_at=observed_at,
        fetched_at=observed_at,
        checksum_sha256=checksum,
    )
    return MaintainedAssetUniverseSourceItem(
        universe=universe,
        provenance=provenance,
    )


class StubProvider:
    def __init__(self, items: tuple[MaintainedAssetUniverseSourceItem, ...]):
        self.items = items
        self.queries: list[MaintainedAssetUniverseQuery] = []

    def fetch(
        self,
        value: MaintainedAssetUniverseQuery,
    ) -> tuple[MaintainedAssetUniverseSourceItem, ...]:
        self.queries.append(value)
        return self.items


def test_ingestion_assesses_quality_and_sorts_deterministically() -> None:
    later = source_item("US_LARGE_CAP", 2, observed_at=timestamp(8))
    earlier = source_item("GLOBAL_ETF", 1, observed_at=timestamp(7))
    provider = StubProvider((later, earlier))
    request = query()

    result = MaintainedAssetUniverseIngestionService(
        provider,
        clock=lambda: timestamp(9),
    ).ingest(request)

    assert provider.queries == [request]
    assert tuple(
        item.universe.universe_key for item in result.evidence
    ) == ("GLOBAL_ETF@1", "US_LARGE_CAP@2")
    assert result.status_counts == {
        "READY": 2,
        "PARTIAL": 0,
        "STALE": 0,
    }
    assert result.all_ready is True
    assert result.to_dict()["evidence_count"] == 2


def test_ingestion_preserves_partial_and_stale_quality() -> None:
    partial = source_item(
        "US_LARGE_CAP",
        1,
        observed_at=timestamp(8),
        checksum=None,
    )
    stale = source_item("GLOBAL_ETF", 1, observed_at=timestamp(1))

    result = MaintainedAssetUniverseIngestionService(
        StubProvider((partial, stale)),
        clock=lambda: timestamp(9),
    ).ingest(query(maximum_age_days=3))

    assert result.status_counts == {
        "READY": 0,
        "PARTIAL": 1,
        "STALE": 1,
    }
    assert result.all_ready is False


def test_empty_provider_result_is_explicitly_not_all_ready() -> None:
    result = MaintainedAssetUniverseIngestionService(
        StubProvider(()),
        clock=lambda: timestamp(9),
    ).ingest(query())

    assert result.evidence == ()
    assert result.all_ready is False


@pytest.mark.parametrize(
    ("items", "message"),
    [
        (
            (source_item("OTHER", 1, observed_at=timestamp(7)),),
            "universe_id",
        ),
        (
            (source_item("US_LARGE_CAP", 1, observed_at=timestamp(10)),),
            "query window",
        ),
    ],
)
def test_ingestion_rejects_provider_items_outside_query(
    items: tuple[MaintainedAssetUniverseSourceItem, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        MaintainedAssetUniverseIngestionService(
            StubProvider(items),
            clock=lambda: timestamp(11),
        ).ingest(query())


def test_ingestion_rejects_future_observation() -> None:
    with pytest.raises(ValueError, match="future observation"):
        MaintainedAssetUniverseIngestionService(
            StubProvider((source_item(
                "US_LARGE_CAP", 1, observed_at=timestamp(8)
            ),)),
            clock=lambda: timestamp(7),
        ).ingest(query())


def test_ingestion_rejects_duplicate_universe_identity() -> None:
    first = source_item("US_LARGE_CAP", 1, observed_at=timestamp(7))
    second = source_item(
        "US_LARGE_CAP",
        1,
        observed_at=timestamp(7),
        source="other_provider",
        source_record_id="other",
    )

    with pytest.raises(ValueError, match="duplicate universe identity"):
        MaintainedAssetUniverseIngestionService(
            StubProvider((first, second)),
            clock=lambda: timestamp(9),
        ).ingest(query())


def test_ingestion_rejects_duplicate_source_identity() -> None:
    first = source_item("US_LARGE_CAP", 1, observed_at=timestamp(7))
    second = source_item(
        "GLOBAL_ETF",
        1,
        observed_at=timestamp(7),
        source_record_id="US_LARGE_CAP-1",
    )

    with pytest.raises(ValueError, match="duplicate source identity"):
        MaintainedAssetUniverseIngestionService(
            StubProvider((first, second)),
            clock=lambda: timestamp(9),
        ).ingest(query())


def test_ingestion_rejects_result_above_explicit_limit() -> None:
    items = (
        source_item("US_LARGE_CAP", 1, observed_at=timestamp(7)),
        source_item("GLOBAL_ETF", 1, observed_at=timestamp(8)),
    )
    with pytest.raises(ValueError, match="query limit"):
        MaintainedAssetUniverseIngestionService(
            StubProvider(items),
            clock=lambda: timestamp(9),
        ).ingest(query(limit=1))


def test_query_normalizes_ids_and_rejects_duplicates() -> None:
    value = query(universe_ids=(" us_large_cap ",))
    assert value.universe_ids == ("US_LARGE_CAP",)

    with pytest.raises(ValueError, match="unique"):
        query(universe_ids=("us_large_cap", "US_LARGE_CAP"))


@pytest.mark.parametrize("maximum_age", [0, -1, float("inf"), float("nan")])
def test_query_rejects_invalid_freshness(maximum_age: float) -> None:
    with pytest.raises(ValueError, match="maximum_age_days"):
        query(maximum_age_days=maximum_age)


def test_ingestion_rejects_non_tuple_provider_result() -> None:
    provider = StubProvider(())
    provider.fetch = lambda value: []  # type: ignore[method-assign]

    with pytest.raises(TypeError, match="provider result"):
        MaintainedAssetUniverseIngestionService(
            provider,
            clock=lambda: timestamp(9),
        ).ingest(query())
