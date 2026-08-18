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
from investment_terminal.universe.screening_pipeline import (
    ScreeningCriterion,
    ScreeningMetricEvidence,
    ScreeningPipeline,
    ScreeningPolicy,
)


def ts(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def stock(symbol: str) -> InstrumentIdentity:
    return InstrumentIdentity(symbol, symbol, "STOCK", "USD", exchange_ticker=symbol, exchange_code="XNAS")


def universe() -> MaintainedAssetUniverseEvidence:
    source = MarketMetadataProvenance(
        source="test", observed_at=ts(10), fetched_at=ts(10),
        source_record_id="u1", checksum_sha256="a" * 64,
    )
    return MaintainedAssetUniverseEvidence(
        MaintainedAssetUniverse("GLOBAL", 1, "Global", ts(10), tuple(
            AssetUniverseMember(stock(symbol), ts(10)) for symbol in ("MSFT", "SMALL", "UNKNOWN")
        )),
        source,
        MarketMetadataQualityService.assess(source, checked_at=ts(11), maximum_age_days=7),
    )


def policy(missing: str = "REVIEW") -> ScreeningPolicy:
    return ScreeningPolicy("quality", 1, ts(11), (
        ScreeningCriterion("market-cap", "market_cap", "GTE", 1_000_000_000, "USD", missing),
        ScreeningCriterion("roe", "return_on_equity", "GTE", 0.10, "FRACTION", missing),
    ))


def metric(symbol: str, name: str, value: float, unit: str) -> ScreeningMetricEvidence:
    return ScreeningMetricEvidence(stock(symbol), name, value, unit, ts(11), f"fundamentals:{symbol}:{name}")


def test_evaluates_every_member_in_canonical_order_without_ranking() -> None:
    result = ScreeningPipeline.evaluate(universe(), policy(), (
        metric("MSFT", "market_cap", 2_000_000_000, "USD"),
        metric("MSFT", "return_on_equity", 0.20, "FRACTION"),
        metric("SMALL", "market_cap", 500_000_000, "USD"),
        metric("SMALL", "return_on_equity", 0.20, "FRACTION"),
    ), evaluated_at=ts(12))
    assert tuple(item.instrument.symbol for item in result.candidates) == ("MSFT", "SMALL", "UNKNOWN")
    assert tuple(item.status for item in result.candidates) == ("PASS", "FAIL", "REVIEW")
    assert result.passing_instrument_keys == ("XNAS:MSFT",)
    assert result.status_counts == {"PASS": 1, "FAIL": 1, "REVIEW": 1}
    assert result.to_dict()["recommendation_authorized"] is False


def test_missing_action_and_unit_mismatch_are_explicit() -> None:
    failed = ScreeningPipeline.evaluate(universe(), policy("FAIL"), (), evaluated_at=ts(12))
    assert failed.candidates[0].criteria[0].reason == "METRIC_MISSING"
    mismatch = ScreeningPipeline.evaluate(universe(), policy(), (
        metric("MSFT", "market_cap", 2, "EUR"),
    ), evaluated_at=ts(12))
    assert mismatch.candidates[0].status == "FAIL"
    assert mismatch.candidates[0].criteria[0].reason == "UNIT_MISMATCH"


def test_rejects_duplicate_out_of_scope_and_future_metrics() -> None:
    item = metric("MSFT", "market_cap", 2_000_000_000, "USD")
    with pytest.raises(ValueError, match="unique"):
        ScreeningPipeline.evaluate(universe(), policy(), (item, item), evaluated_at=ts(12))
    with pytest.raises(ValueError, match="outside universe"):
        ScreeningPipeline.evaluate(universe(), policy(), (
            metric("AAPL", "market_cap", 2, "USD"),
        ), evaluated_at=ts(12))
    future = ScreeningMetricEvidence(stock("MSFT"), "market_cap", 2, "USD", ts(13), "future")
    with pytest.raises(ValueError, match="after evaluated_at"):
        ScreeningPipeline.evaluate(universe(), policy(), (future,), evaluated_at=ts(12))


def test_policy_rejects_hidden_ambiguity() -> None:
    first = ScreeningCriterion("a", "size", "GTE", 1, "USD", "REVIEW")
    with pytest.raises(ValueError, match="unique ids and metrics"):
        ScreeningPolicy("p", 1, ts(11), (first, ScreeningCriterion("b", "size", "LTE", 2, "USD", "REVIEW")))
