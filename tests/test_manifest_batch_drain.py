from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from investment_terminal.operations.manifest_batch_drain import (
    ManifestBatchDrainPlan,
    ManifestBatchDrainService,
)
from investment_terminal.operations.market_batch_manifest import _manifest_checksum
from investment_terminal.operations.resumable_market_batch import MarketBatchRequest


NOW = datetime(2026, 9, 5, tzinfo=timezone.utc)


def manifest(count=3):
    batches = []
    for index in range(1, count + 1):
        request = MarketBatchRequest.from_dict({
            "schema_version": 1,
            "resolution": "D",
            "start": "2016-09-05T00:00:00+00:00",
            "end": "2026-09-05T00:00:00+00:00",
            "items": [{"symbol": f"S{index}", "currency": "USD"}],
        })
        batches.append({
            "batch_index": index,
            "request_checksum": request.checksum,
            "request": request.canonical_dict(),
        })
    value = {
        "schema_version": 1,
        "manifest_identity": "QUALIFIED_MARKET_BATCH_MANIFEST",
        "projection_checksum": "a" * 64,
        "currency_request_checksum": "b" * 64,
        "batches": batches,
    }
    return value, _manifest_checksum(value)


def complete_checkpoint(request):
    return {
        "schema_version": 1,
        "request_checksum": request.checksum,
        "outcomes": {
            item.symbol: {
                "status": "SUCCESS",
                "downloaded": 2,
                "inserted": 2,
                "duplicates": 0,
                "failure_type": None,
            }
            for item in request.items
        },
    }


@dataclass
class Result:
    downloaded: int = 2
    inserted: int = 2
    duplicates: int = 0


class Importer:
    def __init__(self, failures=()):
        self.failures = set(failures)
        self.calls = []

    def import_candles(self, **kwargs):
        symbol = kwargs["symbol"]
        self.calls.append(symbol)
        if symbol in self.failures:
            raise TimeoutError()
        return Result()


def service(checkpoints, importer):
    def write(index, value):
        checkpoints[index] = value

    return ManifestBatchDrainService(
        importer=importer,
        checkpoint_reader=lambda index: checkpoints.get(index),
        checkpoint_writer=write,
        clock=lambda: NOW,
    )


def test_runs_first_unfinished_batches_with_explicit_budget():
    value, checksum = manifest()
    plan = ManifestBatchDrainPlan.from_manifest(value, checksum, max_batches=1)
    checkpoints = {1: complete_checkpoint(plan.requests[0])}
    importer = Importer()

    report = service(checkpoints, importer).run(plan)

    assert importer.calls == ["S2"]
    assert report["status"] == "BUDGET_EXHAUSTED"
    assert report["starting_coverage"]["completed_batch_count"] == 1
    assert report["ending_coverage"]["completed_batch_count"] == 2
    assert report["current_run"] == {
        "attempted_batch_count": 1,
        "attempted_item_count": 1,
        "downloaded_total": 2,
        "inserted_total": 2,
        "duplicate_total": 0,
    }


def test_stops_on_first_non_success_batch():
    value, checksum = manifest()
    plan = ManifestBatchDrainPlan.from_manifest(value, checksum, max_batches=2)
    importer = Importer({"S1"})

    report = service({}, importer).run(plan)

    assert importer.calls == ["S1"]
    assert report["status"] == "HALTED"
    assert report["stop_batch_index"] == 1
    assert report["ending_coverage"]["completed_batch_count"] == 0
    assert report["failure_types"] == ["TimeoutError"]


def test_complete_resume_makes_zero_provider_calls():
    value, checksum = manifest(2)
    plan = ManifestBatchDrainPlan.from_manifest(value, checksum, max_batches=2)
    checkpoints = {
        index: complete_checkpoint(request)
        for index, request in enumerate(plan.requests, start=1)
    }
    importer = Importer()

    report = service(checkpoints, importer).run(plan)

    assert importer.calls == []
    assert report["status"] == "COMPLETE"
    assert report["current_run"]["attempted_batch_count"] == 0


def test_rejects_out_of_order_or_mismatched_checkpoint_before_import():
    value, checksum = manifest()
    plan = ManifestBatchDrainPlan.from_manifest(value, checksum, max_batches=1)
    importer = Importer()
    with pytest.raises(ValueError, match="out-of-order"):
        service({2: complete_checkpoint(plan.requests[1])}, importer).run(plan)
    bad = complete_checkpoint(plan.requests[0])
    bad["request_checksum"] = "0" * 64
    with pytest.raises(ValueError, match="does not match"):
        service({1: bad}, importer).run(plan)
    assert importer.calls == []


@pytest.mark.parametrize("budget", [0, 26, True])
def test_plan_rejects_invalid_budget(budget):
    value, checksum = manifest()
    with pytest.raises((TypeError, ValueError)):
        ManifestBatchDrainPlan.from_manifest(value, checksum, max_batches=budget)
