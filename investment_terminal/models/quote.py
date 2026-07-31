from dataclasses import dataclass
from datetime import datetime

from investment_terminal.models.base_model import BaseModel


@dataclass(slots=True)
class Quote(BaseModel):
    """
    Market quote.
    """

    symbol: str = ""

    price: float = 0.0

    currency: str = "USD"

    timestamp: datetime | None = None