from datetime import datetime, timezone

import pandas as pd
import pytest

from investment_terminal.clients.yahoo_raw_candle_diagnostic_client import (
    YahooRawCandleDiagnosticClient,
)
from investment_terminal.utils.exceptions import APIError


NOW = datetime(2026, 8, 30, tzinfo=timezone.utc)


class Ticker:
    def __init__(self, frame=None, error=None):
        self.frame = frame
        self.error = error
        self.kwargs = None

    def history(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.frame


def test_client_uses_exact_production_history_options(tmp_path):
    frame = pd.DataFrame({"Open": [1]})
    ticker = Ticker(frame)
    cache_calls = []
    client = YahooRawCandleDiagnosticClient(
        ticker_factory=lambda symbol: ticker,
        cache_directory=tmp_path / "cache",
        cache_location_setter=cache_calls.append,
    )
    assert client.get_daily_frame(symbol="PRIVATE", start=NOW, end=NOW) is frame
    assert ticker.kwargs == {"start": NOW, "end": NOW, "interval": "1d",
                             "auto_adjust": False, "actions": False, "repair": False,
                             "raise_errors": True}
    assert cache_calls == [str((tmp_path / "cache").resolve())]


def test_client_wraps_provider_failure_without_provider_text():
    client = YahooRawCandleDiagnosticClient(
        ticker_factory=lambda symbol: Ticker(error=RuntimeError("private provider text"))
    )
    with pytest.raises(APIError, match="raw candle diagnostic") as captured:
        client.get_daily_frame(symbol="PRIVATE", start=NOW, end=NOW)
    assert "private provider text" not in str(captured.value)


def test_client_rejects_non_dataframe():
    client = YahooRawCandleDiagnosticClient(
        ticker_factory=lambda symbol: Ticker(frame=[])
    )
    with pytest.raises(ValueError, match="invalid data type"):
        client.get_daily_frame(symbol="PRIVATE", start=NOW, end=NOW)
