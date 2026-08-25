"""Tests for provenance-aware detached instrument metadata enrichment."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.market.market_metadata_quality import MarketMetadataProvenance
from investment_terminal.portfolio.instrument_metadata_enrichment import (
    InstrumentMetadataDocument,
    InstrumentMetadataEnrichmentService,
    InstrumentMetadataEvidence,
    InstrumentMetadataJsonLoader,
)
from investment_terminal.portfolio.position_reconstruction import (
    PositionReconstruction,
    ReconstructedPosition,
)

NOW = datetime(2026, 8, 25, 18, tzinfo=timezone.utc)
IDENTITY = InstrumentIdentity("ACME", "Acme", "STOCK", "USD", isin="US0000000001")


def evidence(*, key=IDENTITY.instrument_key, ticker="ACME", days_old=1,
             checksum="a" * 64, exchange_code="XNYS"):
    observed = NOW - timedelta(days=days_old)
    return InstrumentMetadataEvidence(
        key, ticker, exchange_code,
        MarketMetadataProvenance(
            "EXCHANGE_REFERENCE", observed, observed,
            source_record_id="record-1", checksum_sha256=checksum,
        ),
    )


def reconstruction(identity=IDENTITY):
    return PositionReconstruction(
        "main", "Personal", 1,
        (ReconstructedPosition(identity, 2, 100, 50, "USD"),),
    )


def enrich(item=None, *, maximum_age=7):
    return InstrumentMetadataEnrichmentService.enrich(
        reconstruction(), InstrumentMetadataDocument((item or evidence(),)),
        checked_at=NOW, maximum_age_days=maximum_age,
    )


def payload(**item_overrides):
    item = {
        "instrument_key": IDENTITY.instrument_key,
        "exchange_ticker": "ACME",
        "exchange_code": "XNYS",
        "provenance": {
            "source": "EXCHANGE_REFERENCE",
            "source_record_id": "record-1",
            "observed_at": (NOW - timedelta(days=1)).isoformat(),
            "fetched_at": (NOW - timedelta(days=1)).isoformat(),
            "checksum_sha256": "a" * 64,
        },
    }
    item.update(item_overrides)
    return {"schema_version": 1, "instruments": [item]}


def test_enrichment_is_detached_and_preserves_position_values():
    original = reconstruction()
    result = enrich()
    position = result.reconstruction.positions[0]
    assert original.positions[0].instrument.exchange_ticker is None
    assert position.instrument.exchange_ticker == "ACME"
    assert position.instrument.exchange_code == "XNYS"
    assert (position.quantity, position.cost_basis, position.average_cost,
            position.cost_currency) == (2, 100, 50, "USD")
    assert result.quality[0].status == "READY"
    assert result.evidence == (evidence(),)


@pytest.mark.parametrize("document", [
    InstrumentMetadataDocument(()),
    InstrumentMetadataDocument((
        evidence(),
        evidence(key="US0000000002", ticker="OTHER"),
    )),
])
def test_enrichment_requires_exact_coverage(document):
    with pytest.raises(ValueError, match="exactly match"):
        InstrumentMetadataEnrichmentService.enrich(
            reconstruction(), document, checked_at=NOW, maximum_age_days=7
        )


def test_stale_partial_future_and_conflicting_evidence_fail_closed():
    cases = (
        evidence(days_old=8),
        evidence(checksum=None),
        InstrumentMetadataEvidence(
            IDENTITY.instrument_key, "ACME", "XNYS",
            MarketMetadataProvenance(
                "TEST", NOW + timedelta(seconds=1), NOW + timedelta(seconds=1),
                source_record_id="future", checksum_sha256="a" * 64,
            ),
        ),
    )
    for item in cases:
        with pytest.raises(ValueError):
            enrich(item)

    original = InstrumentIdentity(
        "ACME", "Acme", "STOCK", "USD", isin=IDENTITY.isin,
        exchange_ticker="OTHER",
    )
    with pytest.raises(ValueError, match="conflicts"):
        InstrumentMetadataEnrichmentService.enrich(
            reconstruction(original), InstrumentMetadataDocument((evidence(),)),
            checked_at=NOW, maximum_age_days=7,
        )


def test_non_isin_identity_must_keep_canonical_key():
    original = InstrumentIdentity("ACME", "Acme", "STOCK", "USD")
    document = InstrumentMetadataDocument((evidence(key="ACME"),))
    with pytest.raises(ValueError, match="must not change instrument_key"):
        InstrumentMetadataEnrichmentService.enrich(
            reconstruction(original), document, checked_at=NOW,
            maximum_age_days=7,
        )


def test_json_loader_normalizes_order_and_round_trips(tmp_path: Path):
    second = payload()["instruments"][0] | {
        "instrument_key": "US0000000002", "exchange_ticker": "OTHER"
    }
    value = payload()
    value["instruments"] = [second, value["instruments"][0]]
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    loaded = InstrumentMetadataJsonLoader.load(path)
    assert tuple(item.instrument_key for item in loaded.instruments) == (
        "US0000000001", "US0000000002"
    )
    assert loaded.to_dict()["schema_version"] == 1
    path.write_text(json.dumps(loaded.to_dict()), encoding="utf-8")
    assert InstrumentMetadataJsonLoader.load(path) == loaded


@pytest.mark.parametrize("value,match", [
    ({"schema_version": 2, "instruments": []}, "schema_version"),
    ({"schema_version": 1, "instruments": [], "extra": True}, "unknown fields"),
    ({"schema_version": 1, "instruments": [{"instrument_key": "A"}]}, "missing fields"),
])
def test_json_loader_rejects_unsupported_unknown_and_missing_fields(
    tmp_path: Path, value, match
):
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        InstrumentMetadataJsonLoader.load(path)


def test_json_loader_rejects_duplicate_keys(tmp_path: Path):
    value = payload()
    value["instruments"].append(dict(value["instruments"][0]))
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        InstrumentMetadataJsonLoader.load(path)
