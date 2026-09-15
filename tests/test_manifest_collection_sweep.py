from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from investment_terminal.clients.yahoo_finance_client import (
    YahooCandleFailureCategory,
    YahooCandleInvalidResponseError,
)
from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepPlan,
    ManifestCollectionSweepService,
)
from investment_terminal.operations.market_batch_manifest import _manifest_checksum
from investment_terminal.operations.resumable_market_batch import MarketBatchRequest


NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)


def manifest(*, batch_count=3, items_per_batch=1):
    batches = []
    for batch_index in range(1, batch_count + 1):
        request = MarketBatchRequest.from_dict({
            "schema_version": 1,
            "resolution": "D",
            "start": "2016-09-15T00:00:00+00:00",
            "end": "2026-09-15T00:00:00+00:00",
            "items": [
                {"symbol": f"S{batch_index}_{item}", "currency": "USD"}
                for item in range(1, items_per_batch + 1)
            ],
        })
        batches.append({
            "batch_index": batch_index,
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


def outcome(status="SUCCESS", failure_type=None):
    return {
        "status": status,
        "downloaded": 2 if status == "SUCCESS" else None,
        "inserted": 2 if status == "SUCCESS" else None,
        "duplicates": 0 if status == "SUCCESS" else None,
        "omitted_trailing_count": 0,
        "omission_types": [],
        "failure_type": failure_type,
    }


def checkpoint(request, outcomes=None):
    return {
        "schema_version": 3,
        "request_checksum": request.checksum,
        "outcomes": outcomes or {
            item.symbol: outcome() for item in request.items
        },
    }


@dataclass
class Result:
    downloaded: int = 2
    inserted: int = 2
    duplicates: int = 0
    omitted_trailing_count: int = 0
    omission_types: tuple[str, ...] = ()


class Importer:
    def __init__(self, failures=None):
        self.failures = failures or {}
        self.calls = []

    def import_candles(self, **kwargs):
        symbol = kwargs["symbol"]
        self.calls.append(symbol)
        failure = self.failures.get(symbol)
        if failure is not None:
            raise failure
        return Result()


def service(checkpoints, importer, *, writer=None):
    def write(index, value):
        checkpoints[index] = value

    return ManifestCollectionSweepService(
        importer=importer,
        checkpoint_reader=lambda index: checkpoints.get(index),
        checkpoint_writer=writer or write,
        clock=lambda: NOW,
    )


def invalid_candle():
    return YahooCandleInvalidResponseError(
        YahooCandleFailureCategory.RESPONSE_NUMERIC
    )


def test_resumes_after_preexisting_deferred_batch_without_retrying_it():
    value, checksum = manifest(batch_count=3, items_per_batch=2)
    plan = ManifestCollectionSweepPlan.from_manifest(value, checksum, max_batches=1)
    deferred = {
        plan.requests[1].items[0].symbol: outcome(),
        plan.requests[1].items[1].symbol: outcome(
            "FAILED", "YahooCandleInvalidResponseError"
        ),
    }
    checkpoints = {
        1: checkpoint(plan.requests[0]),
        2: checkpoint(plan.requests[1], deferred),
    }
    importer = Importer()

    report = service(checkpoints, importer).run(plan)

    assert importer.calls == [item.symbol for item in plan.requests[2].items]
    assert report["status"] == "COMPLETE"
    assert report["starting_coverage"] == {
        "batch_count": 3,
        "sweep_covered_batch_count": 2,
        "fully_complete_batch_count": 1,
        "remaining_unswept_batch_count": 1,
        "deferred_failure_count": 1,
        "deferred_failure_types": ["YahooCandleInvalidResponseError"],
    }
    assert report["ending_coverage"]["sweep_covered_batch_count"] == 3
    assert report["ending_coverage"]["fully_complete_batch_count"] == 2
    assert "S3_1" not in str(report)


def test_defers_local_candle_error_and_continues_to_later_batch():
    value, checksum = manifest(batch_count=2)
    plan = ManifestCollectionSweepPlan.from_manifest(value, checksum, max_batches=2)
    failed_symbol = plan.requests[0].items[0].symbol
    importer = Importer({failed_symbol: invalid_candle()})

    report = service({}, importer).run(plan)

    assert importer.calls == ["S1_1", "S2_1"]
    assert report["status"] == "COMPLETE"
    assert report["current_run"]["attempted_batch_count"] == 2
    assert report["current_run"]["deferred_failure_count"] == 1
    assert report["ending_coverage"]["deferred_failure_count"] == 1


def test_systemic_failure_is_checkpointed_and_halts_before_next_item():
    value, checksum = manifest(batch_count=2, items_per_batch=2)
    plan = ManifestCollectionSweepPlan.from_manifest(value, checksum, max_batches=2)
    first = plan.requests[0].items[0].symbol
    checkpoints = {}
    importer = Importer({first: TimeoutError()})

    report = service(checkpoints, importer).run(plan)

    assert importer.calls == [first]
    assert report["status"] == "HALTED"
    assert report["stop_batch_index"] == 1
    assert report["failure_types"] == ["TimeoutError"]
    assert report["current_run"]["attempted_item_count"] == 1
    assert report["current_run"]["deferred_failure_count"] == 0
    assert checkpoints[1]["outcomes"][first]["status"] == "FAILED"


def test_partial_resume_preserves_deferred_failure_and_attempts_only_missing():
    value, checksum = manifest(batch_count=1, items_per_batch=3)
    plan = ManifestCollectionSweepPlan.from_manifest(value, checksum, max_batches=1)
    items = plan.requests[0].items
    checkpoints = {1: checkpoint(plan.requests[0], {
        items[0].symbol: outcome(),
        items[1].symbol: outcome("FAILED", "YahooCandleInvalidResponseError"),
    })}
    importer = Importer()

    report = service(checkpoints, importer).run(plan)

    assert importer.calls == [items[2].symbol]
    assert report["status"] == "COMPLETE"
    assert report["current_run"]["attempted_item_count"] == 1
    assert report["ending_coverage"]["deferred_failure_count"] == 1


def test_preexisting_systemic_failure_halts_without_provider_call():
    value, checksum = manifest()
    plan = ManifestCollectionSweepPlan.from_manifest(value, checksum, max_batches=2)
    item = plan.requests[0].items[0]
    checkpoints = {1: checkpoint(plan.requests[0], {
        item.symbol: outcome("FAILED", "APIError")
    })}
    importer = Importer()

    report = service(checkpoints, importer).run(plan)

    assert importer.calls == []
    assert report["status"] == "HALTED"
    assert report["failure_types"] == ["APIError"]


def test_rejects_out_of_order_checkpoint_and_writer_failure():
    value, checksum = manifest()
    plan = ManifestCollectionSweepPlan.from_manifest(value, checksum, max_batches=1)
    importer = Importer()
    with pytest.raises(ValueError, match="out-of-order"):
        service({2: checkpoint(plan.requests[1])}, importer).run(plan)
    assert importer.calls == []

    with pytest.raises(OSError):
        service({}, Importer(), writer=lambda index, value: (_ for _ in ()).throw(
            OSError()
        )).run(plan)


def test_complete_resume_and_budget_validation():
    value, checksum = manifest(batch_count=2)
    plan = ManifestCollectionSweepPlan.from_manifest(value, checksum, max_batches=2)
    checkpoints = {
        index: checkpoint(request)
        for index, request in enumerate(plan.requests, start=1)
    }
    importer = Importer()
    report = service(checkpoints, importer).run(plan)
    assert report["status"] == "COMPLETE"
    assert report["current_run"]["attempted_batch_count"] == 0
    assert importer.calls == []

    for budget in (0, 3, True):
        with pytest.raises((TypeError, ValueError)):
            ManifestCollectionSweepPlan.from_manifest(
                value, checksum, max_batches=budget
            )
