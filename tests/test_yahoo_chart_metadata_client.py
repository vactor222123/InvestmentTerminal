import pytest

from investment_terminal.clients.yahoo_chart_metadata_client import YahooChartMetadataClient


class Ticker:
    def __init__(self, value): self.value=value
    def get_history_metadata(self): return self.value


def test_returns_explicit_normalized_currency():
    assert YahooChartMetadataClient(ticker_factory=lambda symbol:Ticker({"currency":" usd "})).get_currency("abc")=="USD"


@pytest.mark.parametrize("value", [{}, {"currency":None}, {"currency":"US"}])
def test_fails_closed_without_valid_currency(value):
    with pytest.raises(ValueError):
        YahooChartMetadataClient(ticker_factory=lambda symbol:Ticker(value)).get_currency("ABC")
