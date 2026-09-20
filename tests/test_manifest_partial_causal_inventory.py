from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_partial_causal_inventory import (
    ManifestPartialCausalInventoryDiagnostic,
)
from tests.test_manifest_collection_sweep import manifest, outcome


NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def api_failure(category, exception_type):
    value = outcome("FAILED", "APIError")
    value["causal_failure_evidence"] = (
        None
        if category is None
        else {
            "category": category,
            "exception_type_chain": [
                "investment_terminal.utils.exceptions.APIError",
                exception_type,
            ],
        }
    )
    return value


def evidence():
    value, checksum = manifest(batch_count=1, items_per_batch=6)
    selection = ManifestBatchSelection.from_manifest(value, checksum, 1)
    symbols = [item.symbol for item in selection.request.items]
    checkpoint = {
        "schema_version": 4,
        "request_checksum": selection.request.checksum,
        "outcomes": {
            symbols[0]: outcome(),
            symbols[1]: api_failure(
                "NO_PRICE_DATA",
                "yfinance.exceptions.YFPricesMissingError",
            ),
            symbols[2]: api_failure(
                "NO_PRICE_DATA",
                "yfinance.exceptions.YFPricesMissingError",
            ),
            symbols[3]: api_failure("TIMEOUT", "builtins.TimeoutError"),
        },
    }
    return value, checksum, selection, checkpoint, symbols


def diagnostic(*times):
    values = iter(times or (NOW, NOW + timedelta(seconds=1)))
    return ManifestPartialCausalInventoryDiagnostic(clock=lambda: next(values))


def test_aggregates_multiple_signatures_without_identity_or_mutation():
    _, _, selection, checkpoint, symbols = evidence()
    original = {
        key: dict(value) for key, value in checkpoint["outcomes"].items()
    }

    report = diagnostic().run(selection, checkpoint)

    assert report["status"] == "SUCCESS"
    assert report["coverage"] == {
        "requested_count": 6,
        "checkpoint_outcome_count": 4,
        "missing_count": 2,
        "success_count": 1,
        "empty_count": 0,
        "retryable_failure_count": 3,
        "final_failure_count": 0,
        "deferable_failure_count": 2,
        "blocking_failure_count": 1,
    }
    assert report["causal_signatures"] == [
        {
            "category": "TIMEOUT",
            "exception_type_chain": [
                "investment_terminal.utils.exceptions.APIError",
                "builtins.TimeoutError",
            ],
            "sweep_disposition": "BLOCKING",
            "count": 1,
        },
        {
            "category": "NO_PRICE_DATA",
            "exception_type_chain": [
                "investment_terminal.utils.exceptions.APIError",
                "yfinance.exceptions.YFPricesMissingError",
            ],
            "sweep_disposition": "DEFERABLE",
            "count": 2,
        },
    ]
    assert all(symbol not in str(report) for symbol in symbols)
    assert checkpoint["outcomes"] == original


def test_legacy_null_and_local_candle_failure_have_explicit_dispositions():
    _, _, selection, checkpoint, symbols = evidence()
    checkpoint["outcomes"] = {
        symbols[0]: api_failure(None, "builtins.TimeoutError"),
        symbols[1]: {
            **outcome("FAILED", "YahooCandleInvalidResponseError"),
            "causal_failure_evidence": {
                "category": "RESPONSE_NUMERIC",
                "exception_type_chain": [
                    "investment_terminal.clients.yahoo_finance_client.YahooCandleInvalidResponseError"
                ],
            },
        },
    }

    report = diagnostic().run(selection, checkpoint)

    assert report["coverage"]["deferable_failure_count"] == 1
    assert report["coverage"]["blocking_failure_count"] == 1
    assert report["causal_signatures"][0]["category"] is None
    assert report["causal_signatures"][0]["exception_type_chain"] == []
    assert report["causal_signatures"][0]["sweep_disposition"] == "BLOCKING"
    assert report["causal_signatures"][1]["sweep_disposition"] == "DEFERABLE"


def test_does_not_copy_private_outer_failure_type_to_report():
    _, _, selection, checkpoint, symbols = evidence()
    checkpoint["outcomes"] = {
        symbols[0]: {
            **api_failure(None, "builtins.TimeoutError"),
            "failure_type": "PRIVATE_IDENTITY",
        }
    }

    report = diagnostic().run(selection, checkpoint)

    assert "PRIVATE_IDENTITY" not in str(report)
    assert report["coverage"]["blocking_failure_count"] == 1


def test_rejects_nonpartial_and_out_of_request_checkpoints():
    _, _, selection, checkpoint, symbols = evidence()
    for item in selection.request.items[4:]:
        checkpoint["outcomes"][item.symbol] = outcome()
    with pytest.raises(ValueError, match="proper partial"):
        diagnostic().run(selection, checkpoint)

    _, _, selection, checkpoint, _ = evidence()
    checkpoint["outcomes"]["PRIVATE"] = checkpoint["outcomes"].pop(symbols[0])
    with pytest.raises(ValueError, match="request subset"):
        diagnostic().run(selection, checkpoint)


def test_rejects_partial_checkpoint_without_retryable_failure():
    _, _, selection, checkpoint, symbols = evidence()
    checkpoint["outcomes"] = {symbols[0]: outcome()}

    with pytest.raises(ValueError, match="no retryable failures"):
        diagnostic().run(selection, checkpoint)


def test_rejects_invalid_selection_and_negative_duration():
    _, _, selection, checkpoint, _ = evidence()
    with pytest.raises(TypeError, match="ManifestBatchSelection"):
        diagnostic().run(object(), checkpoint)
    with pytest.raises(ValueError, match="completed_at"):
        diagnostic(NOW, NOW - timedelta(seconds=1)).run(selection, checkpoint)
