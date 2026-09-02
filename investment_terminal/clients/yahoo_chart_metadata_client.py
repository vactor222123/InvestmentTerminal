"""Yahoo chart-history metadata adapter."""

import yfinance as yf

from investment_terminal.utils.validation import normalize_required_text


class YahooChartMetadataClient:
    def __init__(self, *, ticker_factory=None) -> None:
        self.ticker_factory = ticker_factory or yf.Ticker

    def get_currency(self, symbol: str) -> str:
        normalized_symbol = normalize_required_text(
            symbol, field_name="symbol", uppercase=True
        )
        try:
            metadata = self.ticker_factory(normalized_symbol).get_history_metadata()
        except Exception as exc:
            raise RuntimeError("Yahoo chart metadata request failed") from exc
        if not isinstance(metadata, dict):
            raise RuntimeError("Yahoo chart metadata returned invalid data")
        currency = metadata.get("currency")
        if not isinstance(currency, str):
            raise ValueError("Yahoo chart metadata currency is missing")
        normalized_currency = currency.strip().upper()
        if len(normalized_currency) != 3 or not normalized_currency.isalpha():
            raise ValueError("Yahoo chart metadata currency is invalid")
        return normalized_currency
