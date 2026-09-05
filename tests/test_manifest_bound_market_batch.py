from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
    ManifestBoundMarketBatchService,
)
from investment_terminal.operations.market_batch_manifest import _manifest_checksum


NOW = datetime(2026, 9, 5, tzinfo=timezone.utc)


def manifest():
    requests = [
        {
            "schema_version": 1,
            "resolution": "D",
            "start": "2016-09-05T00:00:00+00:00",
            "end": "2026-09-05T00:00:00+00:00",
            "items": [{"symbol": symbol, "currency": "USD"}],
        }
        for symbol in ("AAA", "BBB")
    ]
    from investment_terminal.operations.resumable_market_batch import MarketBatchRequest

    value = {
        "schema_version": 1,
        "manifest_identity": "QUALIFIED_MARKET_BATCH_MANIFEST",
        "projection_checksum": "a" * 64,
        "currency_request_checksum": "b" * 64,
        "batches": [
            {
                "batch_index": index,
                "request_checksum": MarketBatchRequest.from_dict(request).checksum,
                "request": request,
            }
            for index, request in enumerate(requests, start=1)
        ],
    }
    return value, _manifest_checksum(value)


@dataclass
class Result:
    downloaded: int = 2
    inserted: int = 2
    duplicates: int = 0


class Importer:
    def __init__(self):
        self.calls = []

    def import_candles(self, **kwargs):
        self.calls.append(kwargs["symbol"])
        return Result()


def test_selects_and_executes_exact_bound_request_with_provenance():
    value, checksum = manifest()
    selection = ManifestBatchSelection.from_manifest(value, checksum, 2)
    importer = Importer()

    report = ManifestBoundMarketBatchService(
        importer=importer,
        checkpoint_writer=lambda value: None,
        clock=lambda: NOW,
    ).run(selection)

    assert importer.calls == ["BBB"]
    assert report["status"] == "SUCCESS"
    assert report["manifest_checksum"] == checksum
    assert report["batch_index"] == 2
    assert report["batch_count"] == 2
    assert report["request_checksum"] == selection.request.checksum
    assert "BBB" not in str(report)


@pytest.mark.parametrize("change, message", [
    (lambda value: value.update(manifest_identity="OTHER"), "Unsupported"),
    (lambda value: value["batches"][1].update(batch_index=3), "ordered and contiguous"),
    (lambda value: value["batches"][0].update(request_checksum="0" * 64), "request checksum"),
])
def test_manifest_validation_fails_closed(change, message):
    value, _ = manifest()
    change(value)
    checksum = _manifest_checksum(value)
    with pytest.raises(ValueError, match=message):
        ManifestBatchSelection.from_manifest(value, checksum, 1)


def test_rejects_checksum_mismatch_and_out_of_range_index():
    value, checksum = manifest()
    with pytest.raises(ValueError, match="Manifest checksum"):
        ManifestBatchSelection.from_manifest(value, "0" * 64, 1)
    with pytest.raises(ValueError, match="outside"):
        ManifestBatchSelection.from_manifest(value, checksum, 3)


def test_exact_resume_preserves_bound_zero_work_report():
    value, checksum = manifest()
    selection = ManifestBatchSelection.from_manifest(value, checksum, 1)
    outcome = {
        "status": "SUCCESS",
        "downloaded": 2,
        "inserted": 2,
        "duplicates": 0,
        "failure_type": None,
    }
    checkpoint = {
        "schema_version": 1,
        "request_checksum": selection.request.checksum,
        "outcomes": {"AAA": outcome},
    }
    importer = Importer()

    report = ManifestBoundMarketBatchService(
        importer=importer,
        checkpoint_writer=lambda value: None,
        clock=lambda: NOW,
    ).run(selection, checkpoint)

    assert importer.calls == []
    assert report["coverage"]["current_run"]["attempted_count"] == 0
    assert report["coverage"]["current_run"]["skipped_count"] == 1
