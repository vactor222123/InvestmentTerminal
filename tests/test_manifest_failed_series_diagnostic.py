from datetime import datetime, timezone

import pandas as pd
import pytest

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_failed_series_diagnostic import (
    ManifestFailedSeriesDiagnosticService,
)
from investment_terminal.operations.resumable_market_batch import (
    MarketBatchItem,
    MarketBatchRequest,
)


NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


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


class Client:
    def __init__(self):
        self.calls = []

    def get_daily_frame(self, **kwargs):
        self.calls.append(kwargs)
        return pd.DataFrame(
            {
                "Open": [10.0, float("nan")],
                "High": [11.0, 12.0],
                "Low": [9.0, 8.0],
                "Close": [10.5, 9.0],
                "Volume": [100.0, 200.0],
            },
            index=pd.to_datetime(["2026-09-04T00:00:00Z", "2026-09-05T00:00:00Z"]),
        )


def test_selects_only_failed_item_over_exact_window_and_redacts_identity():
    selected = selection()
    value = checkpoint(selected.request.checksum)
    before = repr(value)
    client = Client()

    report = ManifestFailedSeriesDiagnosticService(
        client=client,
        clock=lambda: NOW,
    ).run(selected, value)

    assert client.calls == [{
        "symbol": "BBB",
        "start": selected.request.start,
        "end": selected.request.end,
    }]
    assert report["selection"]["checkpoint_failure_types"] == [
        "YahooCandleInvalidResponseError"
    ]
    assert report["coverage"]["invalid_reason_counts"] == {
        "OPEN_NON_FINITE": 1
    }
    assert report["schema_version"] == 3
    assert report["coverage"]["projection_assessment"] == {
        "policy_identity": "DAILY_SINGLE_TRAILING_NON_FINITE_NUMERIC_V1",
        "status": "ELIGIBLE",
        "rejection_reason": None,
        "omitted_trailing_count": 1,
        "omission_types": ["TRAILING_NON_FINITE_NUMERIC"],
    }
    assert report["coverage"]["strict_projection"] == {
        "status": "REJECTED",
        "projected_candle_count": None,
        "failure_category": "RESPONSE_NUMERIC",
    }
    assert repr(value) == before
    assert "AAA" not in str(report) and "BBB" not in str(report)
    assert "EUR" not in str(report) and "200.0" not in str(report)


def test_reports_exact_shared_partial_ohlc_rejection_without_values():
    selected = selection()
    client = Client()
    frame = client.get_daily_frame()
    frame.iloc[-1, frame.columns.get_loc("Open")] = 20.0
    frame.iloc[-1, frame.columns.get_loc("Close")] = float("nan")
    client.get_daily_frame = lambda **kwargs: frame

    report = ManifestFailedSeriesDiagnosticService(
        client=client, clock=lambda: NOW
    ).run(selected, checkpoint(selected.request.checksum))

    assessment = report["coverage"]["projection_assessment"]
    assert assessment["status"] == "REJECTED"
    assert assessment["rejection_reason"] == "TRAILING_PARTIAL_OHLC_INCONSISTENT"
    assert "20.0" not in str(report)


def test_reports_qualified_strict_projection_for_complete_valid_frame():
    selected = selection()
    client = Client()
    frame = client.get_daily_frame().iloc[:1].copy()
    client.calls.clear()
    client.get_daily_frame = lambda **kwargs: frame

    report = ManifestFailedSeriesDiagnosticService(
        client=client, clock=lambda: NOW
    ).run(selected, checkpoint(selected.request.checksum))

    assert report["coverage"]["projection_assessment"]["status"] == "REJECTED"
    assert (
        report["coverage"]["projection_assessment"]["rejection_reason"]
        == "NO_INVALID_ROW"
    )
    assert report["coverage"]["strict_projection"] == {
        "status": "QUALIFIED",
        "projected_candle_count": 1,
        "failure_category": None,
    }


def test_reports_empty_strict_projection_without_inventing_failure():
    selected = selection()
    client = Client()
    frame = client.get_daily_frame().iloc[:0].copy()
    client.get_daily_frame = lambda **kwargs: frame

    report = ManifestFailedSeriesDiagnosticService(
        client=client, clock=lambda: NOW
    ).run(selected, checkpoint(selected.request.checksum))

    assert report["coverage"]["strict_projection"] == {
        "status": "EMPTY",
        "projected_candle_count": 0,
        "failure_category": None,
    }


def test_reports_strict_ohlc_rejection_without_private_values():
    selected = selection()
    client = Client()
    frame = client.get_daily_frame().iloc[:1].copy()
    frame.iloc[0, frame.columns.get_loc("High")] = 8.0
    client.get_daily_frame = lambda **kwargs: frame

    report = ManifestFailedSeriesDiagnosticService(
        client=client, clock=lambda: NOW
    ).run(selected, checkpoint(selected.request.checksum))

    assert report["coverage"]["strict_projection"] == {
        "status": "REJECTED",
        "projected_candle_count": None,
        "failure_category": "RESPONSE_OHLC",
    }
    assert "8.0" not in str(report)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(request_checksum="0" * 64),
        lambda value: value["outcomes"].pop("AAA"),
        lambda value: value["outcomes"]["AAA"].update(
            status="FAILED", failure_type="AnotherFailure"
        ),
        lambda value: value["outcomes"]["BBB"].update(status="PENDING"),
        lambda value: value["outcomes"]["BBB"].update(failure_type=""),
    ],
)
def test_rejects_invalid_selection_before_provider_access(mutate):
    selected = selection()
    value = checkpoint(selected.request.checksum)
    mutate(value)
    client = Client()

    with pytest.raises(ValueError):
        ManifestFailedSeriesDiagnosticService(
            client=client,
            clock=lambda: NOW,
        ).run(selected, value)

    assert client.calls == []
