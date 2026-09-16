from datetime import datetime, timezone
from hashlib import sha256
import json

import pytest

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_partial_no_price_isolation import (
    ManifestPartialNoPriceIsolationService,
)
from investment_terminal.operations.resumable_market_batch import (
    MarketBatchItem,
    MarketBatchRequest,
)


NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


def selection():
    request = MarketBatchRequest(
        resolution="D",
        start=NOW.replace(year=2016),
        end=NOW,
        items=(
            MarketBatchItem("AAA", "USD"),
            MarketBatchItem("PRIVATE", "EUR"),
            MarketBatchItem("ZZZ", "USD"),
        ),
    )
    return ManifestBatchSelection("a" * 64, 106, 601, request)


def checkpoint(selected):
    return {
        "schema_version": 3,
        "request_checksum": selected.request.checksum,
        "outcomes": {
            "AAA": {
                "status": "SUCCESS", "downloaded": 100, "inserted": 100,
                "duplicates": 0, "omitted_trailing_count": 0,
                "omission_types": [], "failure_type": None,
            },
            "PRIVATE": {
                "status": "FAILED", "downloaded": None, "inserted": None,
                "duplicates": None, "omitted_trailing_count": 0,
                "omission_types": [], "failure_type": "APIError",
            },
        },
    }


def qualification(selected, **changes):
    report = {
        "schema_version": 1,
        "provider_identity": "YAHOO_FINANCE",
        "qualification_identity": "MANIFEST_PARTIAL_FAILURE_QUALIFICATION",
        "status": "FAILED",
        "manifest_checksum": selected.manifest_checksum,
        "batch_index": selected.batch_index,
        "batch_count": selected.batch_count,
        "request_checksum": selected.request.checksum,
        "requested_start": selected.request.start.isoformat(),
        "requested_end": selected.request.end.isoformat(),
        "selection": {
            "requested_count": 3,
            "checkpoint_outcome_count": 2,
            "missing_count": 1,
            "failed_candidate_count": 1,
            "selected_count": 1,
            "checkpoint_failure_types": ["APIError"],
        },
        "coverage": None,
        "failure": {
            "category": "NO_PRICE_DATA",
            "exception_type_chain": [
                "investment_terminal.utils.exceptions.APIError",
                "yfinance.exceptions.YFPricesMissingError",
            ],
            "reason": "Manifest partial-failure qualification failed",
        },
    }
    report.update(changes)
    raw = json.dumps(report, sort_keys=True).encode("utf-8")
    return raw, sha256(raw).hexdigest()


def run(selected, value, evidence):
    return ManifestPartialNoPriceIsolationService(clock=lambda: NOW).run(
        selected,
        value,
        qualification_bytes=evidence[0],
        qualification_checksum=evidence[1],
    )


def test_transitions_only_bound_failure_and_preserves_missing_request_item():
    selected = selection()
    evidence = qualification(selected)

    updated, report = run(selected, checkpoint(selected), evidence)

    final = updated["outcomes"]["PRIVATE"]
    assert updated["schema_version"] == 4
    assert set(updated["outcomes"]) == {"AAA", "PRIVATE"}
    assert final["status"] == "FINAL_FAILED"
    assert final["failure_type"] == "APIError"
    assert final["failure_category"] == "NO_PRICE_DATA"
    assert final["isolation_policy_identity"] == "REPRODUCED_YAHOO_NO_PRICE_DATA_V1"
    assert final["isolation_evidence"] == {
        "partial_failure_qualification_checksum": evidence[1]
    }
    assert report["coverage"]["missing_count"] == 1
    assert report["coverage"]["transitioned_count"] == 1
    assert "PRIVATE" not in str(report) and "EUR" not in str(report)


def test_exact_repeat_is_idempotent():
    selected = selection()
    evidence = qualification(selected)
    updated, _ = run(selected, checkpoint(selected), evidence)

    repeated, report = run(selected, updated, evidence)

    assert repeated == updated
    assert report["coverage"]["already_final_count"] == 1
    assert report["coverage"]["transitioned_count"] == 0


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda selected, evidence: (evidence[0], "0" * 64), "checksum"),
        (lambda selected, evidence: qualification(selected, batch_index=107), "binding"),
        (lambda selected, evidence: qualification(selected, coverage={}), "binding"),
        (
            lambda selected, evidence: qualification(
                selected,
                failure={
                    "category": "TIMEOUT",
                    "exception_type_chain": [
                        "investment_terminal.utils.exceptions.APIError",
                        "builtins.TimeoutError",
                    ],
                    "reason": "Manifest partial-failure qualification failed",
                },
            ),
            "no-price",
        ),
        (
            lambda selected, evidence: qualification(
                selected,
                failure={
                    "category": "NO_PRICE_DATA",
                    "exception_type_chain": [
                        "investment_terminal.utils.exceptions.APIError"
                    ],
                    "reason": "Manifest partial-failure qualification failed",
                },
            ),
            "type chain",
        ),
        (
            lambda selected, evidence: qualification(
                selected,
                failure={
                    "category": "NO_PRICE_DATA",
                    "exception_type_chain": [
                        "investment_terminal.utils.exceptions.APIError",
                        "private.SecretError",
                        "yfinance.exceptions.YFPricesMissingError",
                    ],
                    "reason": "Manifest partial-failure qualification failed",
                },
            ),
            "causal type chain",
        ),
    ],
)
def test_rejects_unbound_or_ineligible_evidence(mutation, match):
    selected = selection()
    evidence = mutation(selected, qualification(selected))

    with pytest.raises(ValueError, match=match):
        run(selected, checkpoint(selected), evidence)


def test_rejects_conflicting_existing_final_evidence():
    selected = selection()
    evidence = qualification(selected)
    updated, _ = run(selected, checkpoint(selected), evidence)
    updated["outcomes"]["PRIVATE"]["isolation_evidence"][
        "partial_failure_qualification_checksum"
    ] = "b" * 64

    with pytest.raises(ValueError, match="does not match"):
        run(selected, updated, evidence)


def test_rejects_complete_checkpoint_before_transition():
    selected = selection()
    value = checkpoint(selected)
    value["outcomes"]["ZZZ"] = dict(value["outcomes"]["AAA"])

    with pytest.raises(ValueError, match="proper partial"):
        run(selected, value, qualification(selected))


def test_rejects_duplicate_json_keys_before_transition():
    selected = selection()
    raw = qualification(selected)[0]
    duplicated = raw[:-1] + b',"schema_version":1}'

    with pytest.raises(ValueError, match="duplicate"):
        run(selected, checkpoint(selected), (duplicated, sha256(duplicated).hexdigest()))
