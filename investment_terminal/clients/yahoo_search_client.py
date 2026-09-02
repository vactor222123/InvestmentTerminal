"""Bounded Yahoo Finance instrument-search adapter."""

import yfinance as yf

from investment_terminal.utils.validation import normalize_required_text


class YahooSearchClient:
    """Search Yahoo Finance for one private ISIN without unrelated content."""

    def __init__(self, *, timeout_seconds: float = 30) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        self.timeout_seconds = float(timeout_seconds)

    def search_isin(self, isin: str) -> list[dict[str, object]]:
        query = normalize_required_text(isin, field_name="isin", uppercase=True)
        try:
            result = yf.Search(
                query,
                max_results=25,
                news_count=0,
                lists_count=0,
                include_cb=False,
                include_nav_links=False,
                include_research=False,
                include_cultural_assets=False,
                enable_fuzzy_query=False,
                recommended=0,
                timeout=self.timeout_seconds,
                raise_errors=True,
            ).quotes
        except Exception as exc:
            raise RuntimeError("Yahoo Finance ISIN search failed") from exc
        if not isinstance(result, list) or any(not isinstance(item, dict) for item in result):
            raise RuntimeError("Yahoo Finance ISIN search returned invalid data")
        return result

    def search_symbol(self, symbol: str) -> list[dict[str, object]]:
        """Search Yahoo Finance for one exact caller-supplied symbol."""
        query = normalize_required_text(symbol, field_name="symbol", uppercase=True)
        try:
            result = yf.Search(
                query,
                max_results=25,
                news_count=0,
                lists_count=0,
                include_cb=False,
                include_nav_links=False,
                include_research=False,
                include_cultural_assets=False,
                enable_fuzzy_query=False,
                recommended=0,
                timeout=self.timeout_seconds,
                raise_errors=True,
            ).quotes
        except Exception as exc:
            raise RuntimeError("Yahoo Finance symbol search failed") from exc
        if not isinstance(result, list) or any(
            not isinstance(item, dict) for item in result
        ):
            raise RuntimeError("Yahoo Finance symbol search returned invalid data")
        return result
