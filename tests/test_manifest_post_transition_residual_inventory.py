from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import json

import pytest

from investment_terminal.operations.manifest_post_transition_residual_inventory import (
    ManifestPostTransitionResidualInventoryService,
)
from tests.test_manifest_completed_sweep_no_price_transition import (
    NOW,
    evidence as transition_evidence,
    no_price,
    run as run_transition,
)


def evidence():
    manifest, plan, checkpoints, inventory, inventory_checksum, symbols = (
        transition_evidence()
    )
    transition = run_transition(
        checkpoints,
        plan,
        inventory,
        inventory_checksum,
    )
    transition_raw = json.dumps(
        transition, allow_nan=False, sort_keys=True
    ).encode("utf-8")
    return (
        manifest,
        plan,
        checkpoints,
        inventory,
        inventory_checksum,
        transition_raw,
        sha256(transition_raw).hexdigest(),
        symbols,
    )


def service(*times):
    values = iter(times or (NOW, NOW + timedelta(seconds=1)))
    return ManifestPostTransitionResidualInventoryService(
        clock=lambda: next(values)
    )


def run(values):
    _, plan, checkpoints, inventory, inventory_checksum, transition, checksum, _ = (
        values
    )
    return service().run(
        plan,
        checkpoints.get,
        inventory_bytes=inventory,
        inventory_checksum=inventory_checksum,
        transition_report_bytes=transition,
        transition_report_checksum=checksum,
    )


def test_reconciles_residuals_without_identity_or_mutation():
    values = evidence()
    checkpoints = values[2]
    symbols = values[-1]
    original = deepcopy(checkpoints)

    report = run(values)

    assert report["status"] == "SUCCESS"
    assert report["coverage"] == {
        "batch_count": 3,
        "requested_count": 12,
        "checkpoint_outcome_count": 12,
        "missing_count": 0,
        "success_count": 5,
        "empty_count": 1,
        "retryable_failure_count": 2,
        "final_failure_count": 4,
        "transition_policy_final_count": 3,
        "other_final_failure_count": 1,
    }
    assert report["residual_causal_signatures"] == [
        {
            "category": None,
            "exception_type_chain": [],
            "source_disposition": "DEFERABLE",
            "count": 1,
        },
        {
            "category": "RESPONSE_OHLC",
            "exception_type_chain": [
                "investment_terminal.clients.yahoo_finance_client.YahooCandleInvalidResponseError"
            ],
            "source_disposition": "DEFERABLE",
            "count": 1,
        },
    ]
    assert sum(item["count"] for item in report["final_failure_signatures"]) == 4
    assert all(symbol not in str(report) for symbol in symbols)
    assert checkpoints == original


@pytest.mark.parametrize("source", ["inventory", "transition"])
def test_rejects_source_checksum_mismatch(source):
    values = evidence()
    _, plan, checkpoints, inventory, inventory_checksum, transition, checksum, _ = (
        values
    )
    if source == "inventory":
        inventory_checksum = "0" * 64
    else:
        checksum = "0" * 64

    with pytest.raises(ValueError, match="does not match"):
        service().run(
            plan,
            checkpoints.get,
            inventory_bytes=inventory,
            inventory_checksum=inventory_checksum,
            transition_report_bytes=transition,
            transition_report_checksum=checksum,
        )


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda report: report.update(status="FAILED"), "binding"),
        (lambda report: report.update(manifest_checksum="0" * 64), "binding"),
        (lambda report: report.update(inventory_checksum="0" * 64), "binding"),
        (
            lambda report: report["ending_coverage"].update(remaining_count=1),
            "coverage",
        ),
        (
            lambda report: report["current_run"].update(
                processed_checkpoint_count=999
            ),
            "coverage",
        ),
    ],
)
def test_rejects_invalid_transition_report(mutation, match):
    values = list(evidence())
    report = json.loads(values[5])
    mutation(report)
    changed = json.dumps(report, sort_keys=True).encode("utf-8")
    values[5] = changed
    values[6] = sha256(changed).hexdigest()

    with pytest.raises(ValueError, match=match):
        run(tuple(values))


def test_rejects_resurrected_no_price_and_residual_drift():
    values = list(evidence())
    checkpoints = values[2]
    transitioned = next(
        key
        for key, outcome in checkpoints[1]["outcomes"].items()
        if outcome["status"] == "FINAL_FAILED"
    )
    checkpoints[1]["outcomes"][transitioned] = no_price()
    with pytest.raises(ValueError, match="completed transition"):
        run(tuple(values))

    values = list(evidence())
    checkpoints = values[2]
    residual = next(
        outcome
        for outcome in checkpoints[2]["outcomes"].values()
        if outcome["status"] == "FAILED"
        and outcome["causal_failure_evidence"] is not None
    )
    residual["causal_failure_evidence"]["category"] = "RESPONSE_NUMERIC"
    with pytest.raises(ValueError, match="drift"):
        run(tuple(values))


def test_rejects_incomplete_checkpoint_and_negative_duration():
    values = list(evidence())
    values[2][3] = None
    with pytest.raises(ValueError, match="out-of-order|Complete sweep"):
        run(tuple(values))

    values = evidence()
    _, plan, checkpoints, inventory, inventory_checksum, transition, checksum, _ = (
        values
    )
    with pytest.raises(ValueError, match="completed_at"):
        service(NOW, NOW - timedelta(seconds=1)).run(
            plan,
            checkpoints.get,
            inventory_bytes=inventory,
            inventory_checksum=inventory_checksum,
            transition_report_bytes=transition,
            transition_report_checksum=checksum,
        )
