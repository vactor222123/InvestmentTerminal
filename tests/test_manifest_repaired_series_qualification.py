from datetime import datetime, timezone
import json

import pandas as pd
import pytest

from investment_terminal.clients.yahoo_repaired_candle_qualification_client import (
    YahooRepairedFrame,
)
from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_repaired_series_qualification import (
    ManifestRepairedSeriesQualificationService,
)
from investment_terminal.operations.resumable_market_batch import (
    MarketBatchItem,
    MarketBatchRequest,
)


NOW = datetime(2026, 9, 7, tzinfo=timezone.utc)


def selection():
    request = MarketBatchRequest(
        resolution="D",
        start=NOW.replace(year=2016),
        end=NOW,
        items=(MarketBatchItem("AAA", "USD"), MarketBatchItem("BBB", "EUR")),
    )
    return ManifestBatchSelection("a" * 64, 19, 601, request)


def checkpoint(checksum):
    return {
        "schema_version": 1,
        "request_checksum": checksum,
        "outcomes": {
            "AAA": {"status": "SUCCESS", "failure_type": None},
            "BBB": {
                "status": "FAILED",
                "failure_type": "YahooCandleInvalidResponseError",
            },
        },
    }


def valid_frame():
    return pd.DataFrame(
        {
            "Open": [10.0],
            "High": [12.0],
            "Low": [9.0],
            "Close": [11.0],
            "Volume": [100.0],
            "Repaired?": [True],
        },
        index=pd.to_datetime(["2026-09-04T00:00:00Z"]),
    )


class Client:
    def __init__(self, value=None):
        self.value = value if value is not None else valid_frame()
        self.calls = []

    def get_daily_frame(self, **kwargs):
        self.calls.append(kwargs)
        return YahooRepairedFrame(self.value, "1.6.0", 1)


def test_qualifies_only_failed_series_and_redacts_identity():
    selected = selection()
    value = checkpoint(selected.request.checksum)
    before = repr(value)
    client = Client()

    report = ManifestRepairedSeriesQualificationService(
        client=client, clock=lambda: NOW
    ).run(selected, value)

    assert client.calls == [{
        "symbol": "BBB",
        "start": selected.request.start,
        "end": selected.request.end,
    }]
    assert report["status"] == "QUALIFIED"
    assert report["schema_version"] == 2
    assert report["failure"] is None
    assert report["repair"] == {
        "method_identity": "YFINANCE_PRICE_REPAIR_V1",
        "library_identity": "YFINANCE",
        "library_version": "1.6.0",
        "requested": True,
        "repaired_row_count": 1,
        "any_repaired_rows": True,
    }
    assert report["coverage"] == {
        "raw_row_count": 1,
        "projected_candle_count": 1,
        "projection_failure_category": None,
    }
    assert repr(value) == before
    assert "AAA" not in str(report) and "BBB" not in str(report)
    assert "EUR" not in str(report) and "100.0" not in str(report)


def test_rejects_invalid_repaired_frame_with_stable_category():
    selected = selection()
    value = valid_frame()
    value.iloc[-1, value.columns.get_loc("Close")] = float("nan")

    report = ManifestRepairedSeriesQualificationService(
        client=Client(value), clock=lambda: NOW
    ).run(selected, checkpoint(selected.request.checksum))

    assert report["status"] == "REJECTED"
    assert report["schema_version"] == 2
    assert report["failure"] is None
    assert report["coverage"] == {
        "raw_row_count": 1,
        "projected_candle_count": None,
        "projection_failure_category": "RESPONSE_NUMERIC",
    }
    serialized = json.dumps(report, allow_nan=False)
    assert "NaN" not in serialized


def test_rejects_empty_repaired_frame():
    selected = selection()
    report = ManifestRepairedSeriesQualificationService(
        client=Client(valid_frame().iloc[:0]), clock=lambda: NOW
    ).run(selected, checkpoint(selected.request.checksum))

    assert report["status"] == "REJECTED"
    assert report["schema_version"] == 2
    assert report["failure"] is None
    assert report["coverage"]["projected_candle_count"] == 0
    assert report["coverage"]["projection_failure_category"] == "NO_PRICE_DATA"


def test_rejects_non_daily_selection_before_provider_access():
    daily = selection()
    weekly_request = MarketBatchRequest(
        resolution="W",
        start=daily.request.start,
        end=daily.request.end,
        items=daily.request.items,
    )
    selected = ManifestBatchSelection("a" * 64, 19, 601, weekly_request)
    client = Client()

    with pytest.raises(ValueError, match="daily resolution"):
        ManifestRepairedSeriesQualificationService(
            client=client, clock=lambda: NOW
        ).run(selected, checkpoint(selected.request.checksum))

    assert client.calls == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(request_checksum="0" * 64),
        lambda value: value["outcomes"].pop("AAA"),
        lambda value: value["outcomes"]["AAA"].update(
            status="FAILED", failure_type="OtherFailure"
        ),
    ],
)
def test_rejects_invalid_binding_before_provider_access(mutate):
    selected = selection()
    value = checkpoint(selected.request.checksum)
    mutate(value)
    client = Client()

    with pytest.raises(ValueError):
        ManifestRepairedSeriesQualificationService(
            client=client, clock=lambda: NOW
        ).run(selected, value)

    assert client.calls == []
