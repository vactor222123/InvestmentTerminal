from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

import pytest
from yfinance.exceptions import YFPricesMissingError, YFRateLimitError

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_partial_causal_inventory import (
    ManifestPartialCausalInventoryDiagnostic,
)
from investment_terminal.operations.manifest_partial_timeout_retry import (
    ManifestPartialTimeoutRetryService,
    prepare_partial_timeout_retry,
)
from investment_terminal.utils.exceptions import APIError
from tests.test_manifest_collection_sweep import manifest, outcome


NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def api_failure(category, chain):
    value = outcome("FAILED", "APIError")
    value["causal_failure_evidence"] = {
        "category": category,
        "exception_type_chain": chain,
    }
    return value


def evidence():
    value, manifest_checksum = manifest(batch_count=1, items_per_batch=6)
    selection = ManifestBatchSelection.from_manifest(
        value,
        manifest_checksum,
        1,
    )
    symbols = [item.symbol for item in selection.request.items]
    checkpoint = {
        "schema_version": 4,
        "request_checksum": selection.request.checksum,
        "outcomes": {
            symbols[0]: outcome(),
            symbols[1]: api_failure(
                "NO_PRICE_DATA",
                [
                    "investment_terminal.utils.exceptions.APIError",
                    "yfinance.exceptions.YFPricesMissingError",
                ],
            ),
            symbols[2]: {
                **outcome("FAILED", "YahooCandleInvalidResponseError"),
                "causal_failure_evidence": {
                    "category": "RESPONSE_OHLC",
                    "exception_type_chain": [
                        "investment_terminal.clients.yahoo_finance_client.YahooCandleInvalidResponseError"
                    ],
                },
            },
            symbols[3]: api_failure(
                "TIMEOUT",
                [
                    "investment_terminal.utils.exceptions.APIError",
                    "curl_cffi.requests.exceptions.Timeout",
                    "curl_cffi.curl.CurlError",
                ],
            ),
        },
    }
    inventory = ManifestPartialCausalInventoryDiagnostic(
        clock=lambda: NOW
    ).run(selection, checkpoint)
    inventory_bytes = json.dumps(
        inventory,
        indent=2,
        allow_nan=False,
    ).encode("utf-8")
    return (
        value,
        manifest_checksum,
        selection,
        checkpoint,
        symbols,
        inventory_bytes,
        sha256(inventory_bytes).hexdigest(),
    )


@dataclass
class Result:
    downloaded: int = 2
    inserted: int = 2
    duplicates: int = 0
    omitted_trailing_count: int = 0
    omission_types: tuple[str, ...] = ()


class Importer:
    def __init__(self, failure=None):
        self.failure = failure
        self.calls = []

    def import_candles(self, **kwargs):
        self.calls.append(kwargs)
        if self.failure is not None:
            raise self.failure
        return Result()


def wrapped(cause):
    error = APIError("private")
    error.__cause__ = cause
    return error


def service(importer, *times):
    values = iter(times or (NOW, NOW + timedelta(seconds=1)))
    return ManifestPartialTimeoutRetryService(
        importer=importer,
        clock=lambda: next(values),
    )


def test_retries_only_unique_timeout_and_preserves_other_outcomes():
    _, _, selection, checkpoint, symbols, raw, checksum = evidence()
    preserved = {
        symbol: dict(checkpoint["outcomes"][symbol])
        for symbol in symbols[:3]
    }
    importer = Importer()

    updated, report = service(importer).run(
        selection,
        checkpoint,
        inventory_bytes=raw,
        inventory_checksum=checksum,
    )

    assert [call["symbol"] for call in importer.calls] == [symbols[3]]
    assert all(updated["outcomes"][symbol] == value for symbol, value in preserved.items())
    assert set(updated["outcomes"]) == set(symbols[:4])
    assert updated["outcomes"][symbols[3]]["status"] == "SUCCESS"
    assert report["status"] == "READY_FOR_SWEEP"
    assert report["coverage"]["selected_count"] == 1
    assert report["coverage"]["attempted_count"] == 1
    assert report["coverage"]["missing_count"] == 2
    assert report["coverage"]["before"]["deferable_failure_count"] == 2
    assert report["coverage"]["after"]["deferable_failure_count"] == 2
    assert report["coverage"]["after"]["blocking_failure_count"] == 0
    assert report["retry_result"]["sweep_disposition"] == "CLEARED"
    assert all(symbol not in str(report) for symbol in symbols)


@pytest.mark.parametrize(
    "cause, category",
    [
        (TimeoutError("private"), "TIMEOUT"),
        (YFRateLimitError(), "RATE_LIMITED"),
    ],
)
def test_repeated_systemic_failure_remains_blocking(cause, category):
    _, _, selection, checkpoint, symbols, raw, checksum = evidence()
    importer = Importer(wrapped(cause))

    updated, report = service(importer).run(
        selection,
        checkpoint,
        inventory_bytes=raw,
        inventory_checksum=checksum,
    )

    assert [call["symbol"] for call in importer.calls] == [symbols[3]]
    assert updated["outcomes"][symbols[3]]["status"] == "FAILED"
    assert report["status"] == "BLOCKED"
    assert report["retry_result"]["failure_category"] == category
    assert report["retry_result"]["sweep_disposition"] == "BLOCKING"
    assert report["coverage"]["after"]["blocking_failure_count"] == 1


def test_no_price_retry_result_is_deferable_without_touching_other_failures():
    _, _, selection, checkpoint, symbols, raw, checksum = evidence()
    importer = Importer(wrapped(YFPricesMissingError("PRIVATE", "")))

    updated, report = service(importer).run(
        selection,
        checkpoint,
        inventory_bytes=raw,
        inventory_checksum=checksum,
    )

    assert updated["outcomes"][symbols[1]]["status"] == "FAILED"
    assert updated["outcomes"][symbols[2]]["status"] == "FAILED"
    assert report["status"] == "READY_FOR_SWEEP"
    assert report["retry_result"]["failure_category"] == "NO_PRICE_DATA"
    assert report["retry_result"]["sweep_disposition"] == "DEFERABLE"
    assert report["coverage"]["after"]["deferable_failure_count"] == 3


def test_rejects_ambiguous_timeout_before_importer_call():
    _, _, selection, checkpoint, symbols, _, _ = evidence()
    checkpoint["outcomes"][symbols[4]] = dict(
        checkpoint["outcomes"][symbols[3]]
    )
    inventory = ManifestPartialCausalInventoryDiagnostic(
        clock=lambda: NOW
    ).run(selection, checkpoint)
    raw = json.dumps(inventory).encode("utf-8")
    importer = Importer()

    with pytest.raises(ValueError, match="Exactly one blocking timeout"):
        service(importer).run(
            selection,
            checkpoint,
            inventory_bytes=raw,
            inventory_checksum=sha256(raw).hexdigest(),
        )

    assert importer.calls == []


def test_rejects_inventory_binding_and_checksum_mismatch():
    _, _, selection, checkpoint, _, raw, checksum = evidence()
    inventory = json.loads(raw)
    inventory["coverage"]["missing_count"] += 1
    changed = json.dumps(inventory).encode("utf-8")

    with pytest.raises(ValueError, match="binding"):
        prepare_partial_timeout_retry(
            selection,
            checkpoint,
            inventory_bytes=changed,
            inventory_checksum=sha256(changed).hexdigest(),
        )
    with pytest.raises(ValueError, match="does not match"):
        prepare_partial_timeout_retry(
            selection,
            checkpoint,
            inventory_bytes=raw,
            inventory_checksum="0" * 64,
        )


def test_rejects_negative_duration_after_bounded_attempt():
    _, _, selection, checkpoint, _, raw, checksum = evidence()
    with pytest.raises(ValueError, match="completed_at"):
        service(Importer(), NOW, NOW - timedelta(seconds=1)).run(
            selection,
            checkpoint,
            inventory_bytes=raw,
            inventory_checksum=checksum,
        )
