from datetime import datetime, timezone

import pytest
from yfinance.exceptions import YFRateLimitError

from investment_terminal.clients.yahoo_finance_client import (
    YahooCandleFailureCategory,
    YahooCandleInvalidResponseError,
    YahooCandleProjection,
)
from investment_terminal.models.candle import Candle
from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepPlan,
)
from investment_terminal.operations.manifest_partial_failure_qualification import (
    ManifestPartialFailureQualificationService,
    select_partial_api_failure,
)
from investment_terminal.utils.exceptions import APIError
from tests.test_manifest_collection_sweep import manifest, outcome


NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


def evidence():
    value, checksum = manifest(batch_count=1, items_per_batch=3)
    plan = ManifestCollectionSweepPlan.from_manifest(
        value, checksum, max_batches=1
    )
    selection = ManifestBatchSelection.from_manifest(value, checksum, 1)
    first, second = plan.requests[0].items[:2]
    checkpoint = {
        "schema_version": 3,
        "request_checksum": selection.request.checksum,
        "outcomes": {
            first.symbol: outcome(),
            second.symbol: outcome("FAILED", "APIError"),
        },
    }
    return value, checksum, selection, checkpoint, second


def candle(item, selection, *, timestamp=None):
    return Candle(
        symbol=item.symbol,
        resolution=selection.request.resolution,
        timestamp=timestamp or NOW.replace(day=14),
        open_price=1,
        high_price=1,
        low_price=1,
        close_price=1,
        volume=1,
        currency=item.currency,
    )


class Client:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def get_candle_projection(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def service(client):
    return ManifestPartialFailureQualificationService(
        client=client, clock=lambda: NOW
    )


def test_qualifies_one_partial_api_failure_without_mutation():
    _, _, selection, checkpoint, selected = evidence()
    original = {key: dict(value) for key, value in checkpoint["outcomes"].items()}
    client = Client(YahooCandleProjection((candle(selected, selection),), 0, ()))

    report = service(client).run(selection, checkpoint)

    assert report["status"] == "QUALIFIED"
    assert report["coverage"] == {
        "candle_count": 1,
        "omitted_trailing_count": 0,
        "omission_types": [],
    }
    assert report["selection"] == {
        "requested_count": 3,
        "checkpoint_outcome_count": 2,
        "missing_count": 1,
        "failed_candidate_count": 1,
        "selected_count": 1,
        "checkpoint_failure_types": ["APIError"],
    }
    assert checkpoint["outcomes"] == original
    assert client.calls[0]["allow_trailing_incomplete"] is True
    assert selected.symbol not in str(report)


def test_empty_projection_is_a_completed_qualification():
    _, _, selection, checkpoint, _ = evidence()
    report = service(Client(YahooCandleProjection((), 0, ()))).run(
        selection, checkpoint
    )
    assert report["status"] == "EMPTY"
    assert report["coverage"]["candle_count"] == 0
    assert report["failure"] is None


def test_provider_failure_preserves_privacy_safe_causal_evidence():
    _, _, selection, checkpoint, _ = evidence()
    try:
        raise YFRateLimitError()
    except YFRateLimitError as exc:
        failure = APIError("private provider detail")
        failure.__cause__ = exc

    report = service(Client(failure)).run(selection, checkpoint)

    assert report["status"] == "FAILED"
    assert report["coverage"] is None
    assert report["failure"]["category"] == "RATE_LIMITED"
    assert report["failure"]["exception_type_chain"] == [
        "investment_terminal.utils.exceptions.APIError",
        "yfinance.exceptions.YFRateLimitError",
    ]
    assert "private provider detail" not in str(report)


def test_local_projection_failure_uses_existing_category():
    _, _, selection, checkpoint, _ = evidence()
    failure = YahooCandleInvalidResponseError(
        YahooCandleFailureCategory.RESPONSE_NUMERIC
    )
    report = service(Client(failure)).run(selection, checkpoint)
    assert report["status"] == "FAILED"
    assert report["failure"]["category"] == "RESPONSE_NUMERIC"


def test_mismatched_projection_fails_closed_without_private_values():
    _, _, selection, checkpoint, selected = evidence()
    wrong = candle(selected, selection)
    wrong.currency = "EUR"
    report = service(Client(YahooCandleProjection((wrong,), 0, ()))).run(
        selection, checkpoint
    )
    assert report["status"] == "FAILED"
    assert report["failure"]["category"] == "INVALID_RESPONSE"
    assert selected.symbol not in str(report)


def test_selector_rejects_nonpartial_or_ambiguous_evidence():
    _, _, selection, checkpoint, _ = evidence()
    with pytest.raises(ValueError, match="partial"):
        complete = {**checkpoint, "outcomes": {
            **checkpoint["outcomes"],
            selection.request.items[2].symbol: outcome(),
        }}
        select_partial_api_failure(selection, complete)

    with pytest.raises(ValueError, match="exactly one"):
        no_failure = {**checkpoint, "outcomes": {
            key: outcome() for key in checkpoint["outcomes"]
        }}
        select_partial_api_failure(selection, no_failure)

    with pytest.raises(ValueError, match="not eligible"):
        other = {**checkpoint, "outcomes": {
            **checkpoint["outcomes"],
        }}
        failed_key = next(
            key for key, value in other["outcomes"].items()
            if value["status"] == "FAILED"
        )
        other["outcomes"][failed_key] = outcome("FAILED", "TimeoutError")
        select_partial_api_failure(selection, other)


def test_selector_rejects_mismatch_before_provider_access():
    _, _, selection, checkpoint, _ = evidence()
    checkpoint["request_checksum"] = "0" * 64
    client = Client(YahooCandleProjection((), 0, ()))
    with pytest.raises(ValueError, match="does not match"):
        service(client).run(selection, checkpoint)
    assert client.calls == []
