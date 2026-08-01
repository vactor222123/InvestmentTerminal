"""
Contract for fundamental-data providers.
"""

from typing import Protocol

from investment_terminal.models.fundamental_snapshot import (
    FundamentalSnapshot,
)


class FundamentalDataClient(Protocol):
    """
    Interface implemented by fundamental-data providers.
    """

    def get_fundamentals(
        self,
        symbol: str,
        currency: str = "USD",
    ) -> FundamentalSnapshot:
        """
        Return normalized fundamental data for one asset.
        """
        ...