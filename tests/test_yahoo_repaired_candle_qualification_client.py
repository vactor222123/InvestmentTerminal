from datetime import datetime, timezone

import pandas as pd
import pytest

from investment_terminal.clients.yahoo_finance_client import (
    YahooCandleFailureCategory,
    YahooCandleInvalidResponseError,
    YahooFinanceClient,
)
from investment_terminal.clients.yahoo_repaired_candle_qualification_client import (
    YahooRepairedCandleQualificationClient,
)


NOW = datetime(2026, 9, 7, tzinfo=timezone.utc)


def frame():
    return pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [12.0, 13.0],
            "Low": [9.0, 10.0],
            "Close": [11.0, 12.0],
            "Volume": [100.0, 200.0],
            "Repaired?": [False, True],
        },
        index=pd.to_datetime(["2026-09-03T00:00:00Z", "2026-09-04T00:00:00Z"]),
    )


def test_requests_exact_explicit_repair_and_counts_marked_rows(tmp_path):
    calls = []

    class Ticker:
        def history(self, **kwargs):
            calls.append(kwargs)
            return frame()

    cache_locations = []
    client = YahooRepairedCandleQualificationClient(
        ticker_factory=lambda symbol: Ticker(),
        cache_directory=tmp_path / "cache",
        cache_location_setter=cache_locations.append,
        library_version="1.6.0",
    )

    result = client.get_daily_frame(
        symbol="PRIVATE",
        start=NOW.replace(year=2016),
        end=NOW,
    )

    assert calls == [{
        "start": NOW.replace(year=2016),
        "end": NOW,
        "interval": "1d",
        "auto_adjust": False,
        "actions": False,
        "repair": True,
        "raise_errors": True,
    }]
    assert result.library_version == "1.6.0"
    assert result.repaired_row_count == 1
    assert len(cache_locations) == 1


def test_strict_public_projection_never_omits_invalid_trailing_row():
    value = frame()
    value.iloc[-1, value.columns.get_loc("Close")] = float("nan")

    with pytest.raises(YahooCandleInvalidResponseError) as exc_info:
        YahooFinanceClient.project_history_frame_strict(
            value,
            symbol="PRIVATE",
            resolution="D",
            currency="EUR",
        )

    assert exc_info.value.category is YahooCandleFailureCategory.RESPONSE_NUMERIC


def test_rejects_non_frame_provider_value():
    class Ticker:
        def history(self, **kwargs):
            return []

    client = YahooRepairedCandleQualificationClient(
        ticker_factory=lambda symbol: Ticker(), library_version="1.6.0"
    )
    with pytest.raises(ValueError, match="invalid data"):
        client.get_daily_frame(
            symbol="PRIVATE", start=NOW.replace(year=2016), end=NOW
        )
