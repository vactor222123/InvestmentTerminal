"""
Historical market candle model.
"""

from dataclasses import dataclass
from datetime import datetime

from investment_terminal.models.base_model import BaseModel


@dataclass(slots=True)
class Candle(BaseModel):
    """
    One historical OHLCV market-data candle.
    """

    symbol: str = ""
    resolution: str = "D"
    timestamp: datetime | None = None

    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    close_price: float = 0.0

    volume: float = 0.0
    currency: str = "USD"