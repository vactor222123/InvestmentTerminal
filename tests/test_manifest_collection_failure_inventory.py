from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from copy import deepcopy

import pytest

from investment_terminal.operations.manifest_collection_failure_inventory import (
    ManifestCollectionFailureInventoryService,
)
from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepPlan,
    ManifestCollectionSweepService,
)
from tests.test_manifest_collection_sweep import manifest, outcome


NOW = datetime(2026, 9, 21, 19, 0, tzinfo=timezone.utc)


def final_failure():
    return {
        "status": "FINAL_FAILED",
        "downloaded": None,
        "inserted": None,
        "duplicates": None,
        "omitted_trailing_count": 0,
        "omission_types": [],
        "failure_type": "APIError",
        "failure_category": "NO_PRICE_DATA",
        "isolation_policy_identity": "STORED_YAHOO_NO_PRICE_DATA_V1",
        "isolation_evidence": {
            "causal_evidence_diagnostic_checksum": "a" * 64,
        },
    }


def evidence():
    value, checksum = manifest(batch_count=2, items_per_batch=2)
    plan = ManifestCollectionSweepPlan.from_manifest(
        value, checksum, max_batches=2
    )
    first = plan.requests[0]
    second = plan.requests[1]
    first_symbols = [item.symbol for item in first.items]
    second_symbols = [item.symbol for item in second.items]
    retryable = outcome("FAILED", "APIError")
    retryable["causal_failure_evidence"] = {
        "category": "NO_PRICE_DATA",
        "exception_type_chain": [
            "investment_terminal.utils.exceptions.APIError",
            "yfinance.exceptions.YFPricesMissingError",
        ],
    }
    checkpoints = {
        1: {
            "schema_version": 4,
            "request_checksum": first.checksum,
            "outcomes": {
                first_symbols[0]: outcome(),
                first_symbols[1]: retryable,
            },
        },
        2: {
            "schema_version": 4,
            "request_checksum": second.checksum,
            "outcomes": {
                second_symbols[0]: final_failure(),
                second_symbols[1]: outcome("EMPTY"),
            },
        },
    }
    states = [
        ManifestCollectionSweepService._checkpoint_state(
            checkpoints[index], request
        )
        for index, request in enumerate(plan.requests, start=1)
    ]
    sweep = {
        "schema_version": 2,
        "operation_identity": "MANIFEST_COLLECTION_SWEEP",
        "provider_identity": "YAHOO_FINANCE",
        "status": "COMPLETE",
        "manifest_checksum": checksum,
        "ending_coverage": ManifestCollectionSweepService._coverage(states),
        "stop_batch_index": None,
        "failure_types": [],
    }
    raw = json.dumps(sweep, allow_nan=False).encode("utf-8")
    return value, plan, checkpoints, raw, sha256(raw).hexdigest(), first_symbols + second_symbols


def service(*times):
    values = iter(times or (NOW, NOW + timedelta(seconds=1)))
    return ManifestCollectionFailureInventoryService(
        clock=lambda: next(values)
    )


def test_aggregates_complete_collection_without_identity_or_mutation():
    _, plan, checkpoints, raw, checksum, symbols = evidence()
    original = deepcopy(checkpoints)

    report = service().run(
        plan,
        checkpoints.get,
        sweep_report_bytes=raw,
        sweep_report_checksum=checksum,
    )

    assert report["status"] == "SUCCESS"
    assert report["coverage"] == {
        "batch_count": 2,
        "sweep_covered_batch_count": 2,
        "fully_complete_batch_count": 1,
        "requested_count": 4,
        "checkpoint_outcome_count": 4,
        "missing_count": 0,
        "success_count": 1,
        "empty_count": 1,
        "retryable_failure_count": 1,
        "final_failure_count": 1,
        "deferable_failure_count": 1,
        "blocking_failure_count": 0,
    }
    assert report["retryable_causal_signatures"][0]["category"] == "NO_PRICE_DATA"
    assert report["retryable_causal_signatures"][0]["count"] == 1
    assert report["final_failure_signatures"] == [{
        "category": "NO_PRICE_DATA",
        "isolation_policy_identity": "STORED_YAHOO_NO_PRICE_DATA_V1",
        "count": 1,
    }]
    assert all(symbol not in str(report) for symbol in symbols)
    assert checkpoints == original


@pytest.mark.parametrize(
    "mutation",
    [
        lambda report: report.update(status="HALTED"),
        lambda report: report.update(manifest_checksum="0" * 64),
        lambda report: report["ending_coverage"].update(
            deferred_failure_count=999
        ),
    ],
)
def test_rejects_sweep_report_contract_or_coverage_mismatch(mutation):
    _, plan, checkpoints, raw, _, _ = evidence()
    report = json.loads(raw)
    mutation(report)
    changed = json.dumps(report).encode("utf-8")

    with pytest.raises(ValueError, match="binding"):
        service().run(
            plan,
            checkpoints.get,
            sweep_report_bytes=changed,
            sweep_report_checksum=sha256(changed).hexdigest(),
        )


def test_rejects_checksum_mismatch_and_incomplete_checkpoint_coverage():
    _, plan, checkpoints, raw, checksum, _ = evidence()
    with pytest.raises(ValueError, match="does not match"):
        service().run(
            plan,
            checkpoints.get,
            sweep_report_bytes=raw,
            sweep_report_checksum="0" * 64,
        )

    checkpoints[2] = None
    with pytest.raises(ValueError, match="out-of-order|Complete sweep"):
        service().run(
            plan,
            checkpoints.get,
            sweep_report_bytes=raw,
            sweep_report_checksum=checksum,
        )


def test_rejects_blocking_failure_and_negative_duration():
    _, plan, checkpoints, raw, checksum, _ = evidence()
    failed = next(
        item
        for item in checkpoints[1]["outcomes"].values()
        if item["status"] == "FAILED"
    )
    failed["causal_failure_evidence"] = None
    with pytest.raises(ValueError, match="out-of-order|Complete sweep"):
        service().run(
            plan,
            checkpoints.get,
            sweep_report_bytes=raw,
            sweep_report_checksum=checksum,
        )

    _, plan, checkpoints, raw, checksum, _ = evidence()
    with pytest.raises(ValueError, match="completed_at"):
        service(NOW, NOW - timedelta(seconds=1)).run(
            plan,
            checkpoints.get,
            sweep_report_bytes=raw,
            sweep_report_checksum=checksum,
        )
