from datetime import datetime, timezone

import pandas as pd
import pytest

from investment_terminal.operations.single_series_candle_diagnostic import (
    SingleSeriesCandleDiagnosticService,
    _analyze_frame,
)
from investment_terminal.operations.universe_eligibility_scan import EligibilityScanRequest


NOW = datetime(2026, 8, 30, tzinfo=timezone.utc)


def _universe():
    return {
        "schema_version": 1,
        "universe_identity": "BROAD_US_LISTED_SECURITIES",
        "source_identity": "NASDAQ_TRADER_SYMBOL_DIRECTORY",
        "archive_sha256": {"NASDAQ_LISTED": "a" * 64, "OTHER_LISTED": "b" * 64},
        "members": [
            {"source": "NASDAQ_LISTED", "source_symbol": symbol,
             "yahoo_symbol": symbol, "security_name": f"Private {symbol}",
             "listing_code": "Q", "is_etf": False}
            for symbol in ("BBB", "AAA")
        ],
    }


def _request():
    return EligibilityScanRequest.from_universe(_universe(), requested_end=NOW)


def _outcome(symbol, category="RESPONSE_NUMERIC"):
    return {
        "source": "NASDAQ_LISTED", "source_symbol": symbol, "yahoo_symbol": symbol,
        "status": "FINAL_FAILED", "attempt_count": 3,
        "provider_instrument_type": None, "observed_start": None,
        "observed_end": None, "candle_count": None,
        "positive_volume_day_count": None, "median_daily_traded_value": None,
        "measured_at": NOW.isoformat(), "failure_category": category,
    }


def _checkpoint():
    request = _request()
    return {
        "schema_version": 3,
        "request_checksum": request.checksum,
        "universe_checksum": request.universe_checksum,
        "requested_start": request.requested_start.isoformat(),
        "requested_end": request.requested_end.isoformat(),
        "outcomes": {
            "NASDAQ_LISTED:BBB": _outcome("BBB"),
            "NASDAQ_LISTED:AAA": _outcome("AAA"),
        },
    }


class Client:
    def __init__(self, frame):
        self.frame = frame
        self.calls = []

    def get_daily_frame(self, **kwargs):
        self.calls.append(kwargs)
        return self.frame


def test_selects_first_private_numeric_failure_and_emits_no_identity_or_values():
    frame = pd.DataFrame(
        {"Open": [10.0, float("nan")], "High": [11.0, 12.0],
         "Low": [9.0, 8.0], "Close": [10.5, 9.0], "Volume": [100.0, 200.0]},
        index=pd.to_datetime(["2026-08-27T00:00:00Z", "2026-08-28T00:00:00Z"]),
    )
    client = Client(frame)
    report = SingleSeriesCandleDiagnosticService(
        client=client, clock=lambda: NOW
    ).run(_request(), _checkpoint())

    assert client.calls[0]["symbol"] == "AAA"
    assert report["selection"] == {
        "failure_category": "RESPONSE_NUMERIC",
        "eligible_candidate_count": 2,
        "selected_count": 1,
    }
    assert report["coverage"]["invalid_reason_counts"] == {"OPEN_NON_FINITE": 1}
    assert report["coverage"]["invalid_rows"] == [{
        "observed_at": "2026-08-28T00:00:00+00:00",
        "reasons": ["OPEN_NON_FINITE"],
    }]
    serialized = str(report)
    assert "AAA" not in serialized and "BBB" not in serialized and "200.0" not in serialized


def test_analyzer_counts_numeric_and_ohlc_failure_paths_without_values():
    frame = pd.DataFrame(
        {"Open": [0.0, "bad", 10.0], "High": [2.0, 2.0, 9.0],
         "Low": [1.0, 1.0, 11.0], "Close": [1.5, 1.5, 10.0],
         "Volume": [-1.0, 1.0, 1.0]},
        index=["invalid", pd.Timestamp("2026-08-27"), pd.Timestamp("2026-08-28", tz="UTC")],
    )
    result = _analyze_frame(frame)
    assert result["raw_row_count"] == 3
    assert result["invalid_row_count"] == 3
    assert result["invalid_reason_counts"] == {
        "HIGH_INCONSISTENT": 1,
        "LOW_INCONSISTENT": 1,
        "OPEN_NON_POSITIVE": 1,
        "OPEN_NOT_REAL": 1,
        "VOLUME_NEGATIVE": 1,
    }
    assert result["invalid_rows"][0]["observed_at"] is None


def test_schema2_or_missing_candidate_fails_closed_without_provider_call():
    client = Client(pd.DataFrame())
    checkpoint = _checkpoint()
    checkpoint["schema_version"] = 2
    with pytest.raises(ValueError, match="schema-version-3"):
        SingleSeriesCandleDiagnosticService(client=client, clock=lambda: NOW).run(
            _request(), checkpoint
        )
    assert client.calls == []

    checkpoint = _checkpoint()
    for outcome in checkpoint["outcomes"].values():
        outcome["failure_category"] = "RESPONSE_OHLC"
    with pytest.raises(ValueError, match="no RESPONSE_NUMERIC"):
        SingleSeriesCandleDiagnosticService(client=client, clock=lambda: NOW).run(
            _request(), checkpoint
        )
    assert client.calls == []


def test_mismatched_checkpoint_fails_before_provider_call():
    client = Client(pd.DataFrame())
    checkpoint = _checkpoint()
    checkpoint["request_checksum"] = "0" * 64
    with pytest.raises(ValueError, match="does not match"):
        SingleSeriesCandleDiagnosticService(client=client, clock=lambda: NOW).run(
            _request(), checkpoint
        )
    assert client.calls == []
