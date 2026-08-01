"""
Portfolio market-price provider protocol and in-memory implementation.
"""

from collections.abc import Mapping
from typing import Protocol

from investment_terminal.portfolio.portfolio_market_value_models import (
    PortfolioPriceQuote,
)


class PortfolioPriceProvider(Protocol):
    """Provide one latest market quote for an instrument."""

    def get_quote(
        self,
        *,
        instrument_key: str,
        exchange_ticker: str,
    ) -> PortfolioPriceQuote:
        ...


class InMemoryPortfolioPriceProvider:
    """Deterministic quote provider used by tests and offline runs."""

    def __init__(
        self,
        quotes: Mapping[
            str,
            PortfolioPriceQuote,
        ],
    ) -> None:
        self._quotes = {
            key.strip().upper(): value
            for key, value in quotes.items()
        }

    def get_quote(
        self,
        *,
        instrument_key: str,
        exchange_ticker: str,
    ) -> PortfolioPriceQuote:
        normalized_key = (
            instrument_key.strip().upper()
        )

        try:
            return self._quotes[
                normalized_key
            ]
        except KeyError as exc:
            raise KeyError(
                "No portfolio price quote found for "
                f"{normalized_key}"
            ) from exc