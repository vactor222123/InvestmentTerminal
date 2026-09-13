from datetime import datetime, timezone
from hashlib import sha256
import json

import pytest

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_terminal_series_isolation import (
    ManifestTerminalSeriesIsolationService,
)
from investment_terminal.operations.resumable_market_batch import (
    MarketBatchItem,
    MarketBatchRequest,
)


NOW = datetime(2026, 9, 13, tzinfo=timezone.utc)
FAILURE_TYPE = "YahooCandleInvalidResponseError"


def selection():
    request = MarketBatchRequest(
        resolution="D",
        start=NOW.replace(year=2016),
        end=NOW,
        items=(MarketBatchItem("AAA", "USD"), MarketBatchItem("PRIVATE", "EUR")),
    )
    return ManifestBatchSelection("a" * 64, 41, 601, request)


def checkpoint(selected):
    return {
        "schema_version": 1,
        "request_checksum": selected.request.checksum,
        "outcomes": {
            "AAA": {"status": "SUCCESS", "failure_type": None},
            "PRIVATE": {"status": "FAILED", "failure_type": FAILURE_TYPE},
        },
    }


def reports(selected, category="RESPONSE_NUMERIC"):
    common = {
        "provider_identity": "YAHOO_FINANCE",
        "manifest_checksum": selected.manifest_checksum,
        "batch_index": selected.batch_index,
        "batch_count": selected.batch_count,
        "request_checksum": selected.request.checksum,
        "requested_start": selected.request.start.isoformat(),
        "requested_end": selected.request.end.isoformat(),
        "selection": {
            "requested_count": len(selected.request.items),
            "failed_candidate_count": 1,
            "selected_count": 1,
            "checkpoint_failure_types": [FAILURE_TYPE],
        },
        "failure": None,
    }
    normal = dict(common)
    normal.update({
        "schema_version": 3,
        "diagnostic_identity": "MANIFEST_FAILED_SERIES_RAW_CANDLE_DIAGNOSTIC",
        "status": "SUCCESS",
        "coverage": {"strict_projection": {
            "status": "REJECTED",
            "projected_candle_count": None,
            "failure_category": category,
        }},
    })
    repaired = dict(common)
    repaired.update({
        "schema_version": 2,
        "qualification_identity": "MANIFEST_REPAIRED_SERIES_QUALIFICATION",
        "status": "REJECTED",
        "repair": {
            "method_identity": "YFINANCE_PRICE_REPAIR_V1",
            "requested": True,
        },
        "coverage": {
            "projected_candle_count": None,
            "projection_failure_category": category,
        },
    })
    return encoded(normal), encoded(repaired)


def encoded(value):
    raw = json.dumps(value, sort_keys=True).encode("utf-8")
    return raw, sha256(raw).hexdigest()


def run(selected, value, normal, repaired):
    return ManifestTerminalSeriesIsolationService(clock=lambda: NOW).run(
        selected,
        value,
        normal_diagnostic_bytes=normal[0],
        normal_diagnostic_checksum=normal[1],
        repaired_qualification_bytes=repaired[0],
        repaired_qualification_checksum=repaired[1],
    )


def test_transitions_only_failed_series_with_bound_evidence_and_redacted_report():
    selected = selection()
    normal, repaired = reports(selected)

    updated, report = run(
        selected, checkpoint(selected), normal, repaired
    )

    outcome = updated["outcomes"]["PRIVATE"]
    assert updated["schema_version"] == 3
    assert outcome["status"] == "FINAL_FAILED"
    assert outcome["failure_category"] == "RESPONSE_NUMERIC"
    assert outcome["isolation_evidence"] == {
        "normal_diagnostic_checksum": normal[1],
        "repaired_qualification_checksum": repaired[1],
    }
    assert updated["outcomes"]["AAA"]["status"] == "SUCCESS"
    assert report["coverage"] == {
        "requested_count": 2,
        "success_count": 1,
        "empty_count": 0,
        "retryable_failure_count": 0,
        "final_failure_count": 1,
        "transitioned_count": 1,
        "already_final_count": 0,
    }
    assert "PRIVATE" not in str(report) and "EUR" not in str(report)


def test_exact_repeat_is_idempotent():
    selected = selection()
    normal, repaired = reports(selected)
    updated, _ = run(selected, checkpoint(selected), normal, repaired)

    repeated, report = run(selected, updated, normal, repaired)

    assert repeated == updated
    assert report["coverage"]["transitioned_count"] == 0
    assert report["coverage"]["already_final_count"] == 1


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda normal, repaired: (normal, (repaired[0], "0" * 64)), "checksum"),
        (
            lambda normal, repaired: (
                normal,
                encoded({**json.loads(repaired[0]), "batch_index": 42}),
            ),
            "binding",
        ),
        (
            lambda normal, repaired: (
                normal,
                encoded({
                    **json.loads(repaired[0]),
                    "coverage": {
                        "projected_candle_count": None,
                        "projection_failure_category": "RESPONSE_OHLC",
                    },
                }),
            ),
            "categories",
        ),
    ],
)
def test_rejects_unbound_or_inconsistent_evidence(mutation, match):
    selected = selection()
    normal, repaired = mutation(*reports(selected))

    with pytest.raises(ValueError, match=match):
        run(selected, checkpoint(selected), normal, repaired)


def test_rejects_unsupported_terminal_category():
    selected = selection()
    normal, repaired = reports(selected, "NO_PRICE_DATA")

    with pytest.raises(ValueError, match="not eligible"):
        run(selected, checkpoint(selected), normal, repaired)


def test_rejects_conflicting_existing_final_evidence():
    selected = selection()
    normal, repaired = reports(selected)
    updated, _ = run(selected, checkpoint(selected), normal, repaired)
    updated["outcomes"]["PRIVATE"]["isolation_evidence"][
        "normal_diagnostic_checksum"
    ] = "c" * 64

    with pytest.raises(ValueError, match="does not match"):
        run(selected, updated, normal, repaired)
