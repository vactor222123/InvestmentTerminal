from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

import pytest

from investment_terminal.operations.manifest_collection_failure_inventory import (
    ManifestCollectionFailureInventoryService,
)
from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepPlan,
    ManifestCollectionSweepService,
)
from investment_terminal.operations.manifest_completed_sweep_no_price_transition import (
    ManifestCompletedSweepNoPriceTransitionService,
)
from tests.test_manifest_collection_failure_inventory import final_failure
from tests.test_manifest_collection_sweep import manifest, outcome


NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)
CHAIN = [
    "investment_terminal.utils.exceptions.APIError",
    "yfinance.exceptions.YFPricesMissingError",
]


def no_price():
    value = outcome("FAILED", "APIError")
    value["causal_failure_evidence"] = {
        "category": "NO_PRICE_DATA",
        "exception_type_chain": list(CHAIN),
    }
    return value


def local_failure(category="RESPONSE_OHLC"):
    value = outcome("FAILED", "YahooCandleInvalidResponseError")
    value["causal_failure_evidence"] = {
        "category": category,
        "exception_type_chain": [
            "investment_terminal.clients.yahoo_finance_client.YahooCandleInvalidResponseError"
        ],
    }
    return value


def evidence():
    manifest_value, manifest_checksum = manifest(
        batch_count=3, items_per_batch=4
    )
    plan = ManifestCollectionSweepPlan.from_manifest(
        manifest_value, manifest_checksum, max_batches=3
    )
    symbols = [
        [item.symbol for item in request.items] for request in plan.requests
    ]
    checkpoints = {
        1: {
            "schema_version": 4,
            "request_checksum": plan.requests[0].checksum,
            "outcomes": {
                symbols[0][0]: no_price(),
                symbols[0][1]: no_price(),
                symbols[0][2]: outcome(),
                symbols[0][3]: outcome(),
            },
        },
        2: {
            "schema_version": 4,
            "request_checksum": plan.requests[1].checksum,
            "outcomes": {
                symbols[1][0]: local_failure(),
                symbols[1][1]: {
                    **outcome("FAILED", "YahooCandleInvalidResponseError"),
                    "causal_failure_evidence": None,
                },
                symbols[1][2]: outcome(),
                symbols[1][3]: outcome("EMPTY"),
            },
        },
        3: {
            "schema_version": 4,
            "request_checksum": plan.requests[2].checksum,
            "outcomes": {
                symbols[2][0]: no_price(),
                symbols[2][1]: final_failure(),
                symbols[2][2]: outcome(),
                symbols[2][3]: outcome(),
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
        "manifest_checksum": manifest_checksum,
        "ending_coverage": ManifestCollectionSweepService._coverage(states),
        "stop_batch_index": None,
        "failure_types": [],
    }
    sweep_raw = json.dumps(sweep, allow_nan=False).encode("utf-8")
    inventory = ManifestCollectionFailureInventoryService(
        clock=lambda: NOW
    ).run(
        plan,
        checkpoints.get,
        sweep_report_bytes=sweep_raw,
        sweep_report_checksum=sha256(sweep_raw).hexdigest(),
    )
    inventory_raw = json.dumps(inventory, allow_nan=False).encode("utf-8")
    return (
        manifest_value,
        plan,
        checkpoints,
        inventory_raw,
        sha256(inventory_raw).hexdigest(),
        [symbol for group in symbols for symbol in group],
    )


def service(checkpoints, *times, writer=None):
    def write(index, value):
        checkpoints[index] = value

    values = iter(times or (NOW, NOW + timedelta(seconds=1)))
    return ManifestCompletedSweepNoPriceTransitionService(
        checkpoint_writer=writer or write,
        clock=lambda: next(values),
    )


def run(checkpoints, plan, raw, checksum, *, budget=3, writer=None):
    return service(checkpoints, writer=writer).run(
        plan,
        checkpoints.get,
        inventory_bytes=raw,
        inventory_checksum=checksum,
        max_checkpoints=budget,
    )


def test_transitions_all_eligible_outcomes_in_one_atomic_checkpoint_write():
    _, plan, checkpoints, raw, checksum, symbols = evidence()
    preserved_local = deepcopy(checkpoints[2])
    writes = []

    def write(index, value):
        writes.append((index, deepcopy(value)))
        checkpoints[index] = value

    report = run(checkpoints, plan, raw, checksum, budget=1, writer=write)

    assert report["status"] == "BUDGET_EXHAUSTED"
    assert report["current_run"] == {
        "processed_checkpoint_count": 1,
        "eligible_count": 3,
        "transitioned_count": 2,
        "already_final_count": 0,
        "remaining_count": 1,
    }
    assert report["ending_coverage"]["remaining_count"] == 1
    assert len(writes) == 1 and writes[0][0] == 1
    assert checkpoints[2] == preserved_local
    for value in checkpoints[1]["outcomes"].values():
        if value["status"] == "FINAL_FAILED":
            assert value["isolation_evidence"] == {
                "collection_failure_inventory_checksum": checksum
            }
    assert all(symbol not in str(report) for symbol in symbols)


def test_exact_bounded_resume_and_completed_zero_write_resume():
    _, plan, checkpoints, raw, checksum, _ = evidence()
    first = run(checkpoints, plan, raw, checksum, budget=1)
    second = run(checkpoints, plan, raw, checksum, budget=1)
    writes = []
    third = run(
        checkpoints,
        plan,
        raw,
        checksum,
        budget=1,
        writer=lambda index, value: writes.append((index, value)),
    )

    assert first["status"] == "BUDGET_EXHAUSTED"
    assert second["status"] == "COMPLETE"
    assert second["starting_coverage"]["already_final_count"] == 2
    assert second["current_run"]["transitioned_count"] == 1
    assert third["status"] == "COMPLETE"
    assert third["starting_coverage"]["already_final_count"] == 3
    assert third["current_run"]["processed_checkpoint_count"] == 0
    assert writes == []


def test_preserves_local_and_legacy_failures_and_rejects_checkpoint_drift():
    _, plan, checkpoints, raw, checksum, _ = evidence()
    local_before = deepcopy(checkpoints[2])
    run(checkpoints, plan, raw, checksum)
    assert checkpoints[2] == local_before

    _, plan, checkpoints, raw, checksum, _ = evidence()
    failed = next(
        value
        for value in checkpoints[2]["outcomes"].values()
        if value["status"] == "FAILED"
    )
    failed["causal_failure_evidence"] = None
    with pytest.raises(ValueError, match="drift|coverage"):
        run(checkpoints, plan, raw, checksum)


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda report: report.update(manifest_checksum="0" * 64), "binding"),
        (
            lambda report: report["coverage"].update(blocking_failure_count=1),
            "coverage",
        ),
        (
            lambda report: report["retryable_causal_signatures"][0].update(
                exception_type_chain=[
                    "investment_terminal.utils.exceptions.APIError",
                    "UNRECOGNIZED_EXCEPTION_TYPE",
                ]
            ),
            "signature|no eligible|drift",
        ),
    ],
)
def test_rejects_unbound_or_ineligible_inventory_before_write(mutation, match):
    _, plan, checkpoints, raw, _, _ = evidence()
    inventory = json.loads(raw)
    mutation(inventory)
    changed = json.dumps(inventory).encode("utf-8")
    writes = []

    with pytest.raises(ValueError, match=match):
        run(
            checkpoints,
            plan,
            changed,
            sha256(changed).hexdigest(),
            writer=lambda index, value: writes.append((index, value)),
        )
    assert writes == []


def test_rejects_checksum_conflict_and_invalid_budget_before_write():
    _, plan, checkpoints, raw, checksum, _ = evidence()
    writes = []
    with pytest.raises(ValueError, match="does not match"):
        run(
            checkpoints,
            plan,
            raw,
            "0" * 64,
            writer=lambda index, value: writes.append((index, value)),
        )
    assert writes == []
    for budget in (0, 4, True):
        with pytest.raises((TypeError, ValueError)):
            run(checkpoints, plan, raw, checksum, budget=budget)


def test_checkpoint_write_failure_is_visible_and_preserves_later_checkpoints():
    _, plan, checkpoints, raw, checksum, _ = evidence()
    original = deepcopy(checkpoints)

    report = run(
        checkpoints,
        plan,
        raw,
        checksum,
        writer=lambda index, value: (_ for _ in ()).throw(OSError("private")),
    )

    assert report["status"] == "FAILED"
    assert report["failure"] == {
        "type": "OSError",
        "reason": "Completed-sweep no-price checkpoint write failed",
    }
    assert report["current_run"]["transitioned_count"] == 0
    assert checkpoints == original
    assert "private" not in str(report)
