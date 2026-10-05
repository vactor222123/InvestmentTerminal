"""Bounded normalized Yahoo action retrieval; no direct chart collector."""

from investment_terminal.clients.yahoo_price_basis_client import YahooPriceBasisClient


class YahooCorporateActionsClient(YahooPriceBasisClient):
    def get_action_history(self, *, symbol, start, end):
        ticker = self._ticker_factory(symbol)
        frame = ticker.history(
            start=start, end=end, interval="1d", actions=True,
            auto_adjust=False, back_adjust=False, repair=False,
            keepna=True, rounding=False, timeout=20, raise_errors=True,
        )
        # Public API may make an auxiliary bounded metadata request in yfinance.
        # Do not inspect private library caches or claim one HTTP request.
        metadata = ticker.get_history_metadata()
        return frame, metadata
