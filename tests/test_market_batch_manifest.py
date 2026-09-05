from datetime import datetime, timezone

import pytest

from investment_terminal.operations.market_batch_manifest import (
    MarketBatchManifestService,
    _manifest_checksum,
)
from investment_terminal.operations.symbol_currency_qualification import _checksum


NOW = datetime(2026, 9, 5, tzinfo=timezone.utc)
START = datetime(2016, 9, 5, tzinfo=timezone.utc)


def evidence(count=21):
    symbols = [f"S{index:03d}" for index in range(count)]
    projection = {
        "schema_version": 1,
        "projection_identity": "ELIGIBILITY_SUCCESS_UNIVERSE",
        "request_checksum": "a" * 64,
        "universe_checksum": "b" * 64,
        "members": [
            {"source": "NASDAQ_LISTED", "source_symbol": symbol, "yahoo_symbol": symbol}
            for symbol in reversed(symbols)
        ],
    }
    projection_checksum = _checksum(projection)
    request_checksum = _checksum({
        "schema_version": 2,
        "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION",
        "projection_checksum": projection_checksum,
    })
    checkpoint = {
        "schema_version": 2,
        "request_checksum": request_checksum,
        "projection_checksum": projection_checksum,
        "outcomes": {
            symbol: {
                "status": "SUCCESS",
                "attempt_count": 1,
                "currency": "USD" if index % 2 else "EUR",
                "failure_category": None,
            }
            for index, symbol in enumerate(symbols)
        },
    }
    return projection, projection_checksum, checkpoint


def test_builds_deterministic_bounded_manifest_and_redacted_report():
    projection, checksum, checkpoint = evidence()
    checkpoint["outcomes"]["S020"] = {
        "status": "FINAL_FAILED",
        "attempt_count": 3,
        "currency": None,
        "failure_category": "INVALID_RESPONSE",
    }

    manifest, report = MarketBatchManifestService(clock=lambda: NOW).run(
        projection,
        checksum,
        checkpoint,
        resolution="d",
        start=START,
        end=NOW,
    )

    assert [len(batch["request"]["items"]) for batch in manifest["batches"]] == [20]
    assert manifest["batches"][0]["request"]["items"][0] == {
        "symbol": "S000", "currency": "EUR"
    }
    assert report["manifest_checksum"] == _manifest_checksum(manifest)
    assert report["coverage"] == {
        "member_count": 21,
        "included_count": 20,
        "excluded_count": 1,
        "batch_count": 1,
        "maximum_batch_size": 20,
        "minimum_batch_size": 20,
        "excluded_categories": {"INVALID_RESPONSE": 1},
    }
    assert "S000" not in str(report)
    assert "EUR" not in str(report)


def test_partitions_all_successes_at_existing_twenty_item_limit():
    projection, checksum, checkpoint = evidence()

    manifest, report = MarketBatchManifestService(clock=lambda: NOW).run(
        projection, checksum, checkpoint, resolution="D", start=START, end=NOW
    )

    assert [len(batch["request"]["items"]) for batch in manifest["batches"]] == [20, 1]
    assert [batch["batch_index"] for batch in manifest["batches"]] == [1, 2]
    assert report["coverage"]["included_count"] == 21
    assert report["coverage"]["minimum_batch_size"] == 1


@pytest.mark.parametrize("mutation, message", [
    (lambda projection, checkpoint: checkpoint["outcomes"].pop("S020"), "symbol set"),
    (lambda projection, checkpoint: checkpoint["outcomes"]["S020"].update(status="RETRY_PENDING"), "not complete"),
    (lambda projection, checkpoint: checkpoint["outcomes"]["S020"].update(currency="US"), "three-letter"),
])
def test_fails_closed_for_invalid_currency_evidence(mutation, message):
    projection, checksum, checkpoint = evidence()
    mutation(projection, checkpoint)
    with pytest.raises(ValueError, match=message):
        MarketBatchManifestService(clock=lambda: NOW).run(
            projection, checksum, checkpoint, resolution="D", start=START, end=NOW
        )


def test_rejects_projection_checksum_mismatch_and_legacy_checkpoint():
    projection, checksum, checkpoint = evidence()
    service = MarketBatchManifestService(clock=lambda: NOW)
    with pytest.raises(ValueError, match="Projection checksum"):
        service.run(projection, "0" * 64, checkpoint, resolution="D", start=START, end=NOW)
    checkpoint["schema_version"] = 1
    with pytest.raises(ValueError, match="schema-version-2"):
        service.run(projection, checksum, checkpoint, resolution="D", start=START, end=NOW)


def test_reuses_market_batch_request_validation():
    projection, checksum, checkpoint = evidence(1)
    with pytest.raises(ValueError, match="Unsupported resolution"):
        MarketBatchManifestService(clock=lambda: NOW).run(
            projection, checksum, checkpoint, resolution="H", start=START, end=NOW
        )
