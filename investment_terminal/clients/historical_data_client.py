"""
Contract for historical market-data providers.
"""

from datetime import datetime
from typing import Protocol
from investment_terminal.models.candle import Candle    
from investment_terminal.clients.finnhub_client import FinnhubClient


class HistoricalDataClient(Protocol):
    """
    Interface implemented by historical market-data clients.
    """

    def get_candles(
        self,
        symbol: str,
        resolution: str,
        start: datetime,
        end: datetime,
        currency: str = "USD",
    ) -> list[Candle]:
        """
        Return historical OHLCV candles.
        """
        ...