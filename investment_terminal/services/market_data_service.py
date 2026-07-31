"""
Market data download and persistence service.
"""

from dataclasses import dataclass

from investment_terminal.clients.finnhub_client import FinnhubClient
from investment_terminal.models.quote import Quote
from investment_terminal.repositories.quote_repository import QuoteRepository


@dataclass(frozen=True, slots=True)
class SavedQuoteResult:
    """
    Result of downloading, saving and reading back a quote.
    """

    quote_id: int
    quote: Quote


class MarketDataService:
    """
    Coordinate market-data clients and repositories.
    """

    def __init__(
        self,
        client: FinnhubClient,
        repository: QuoteRepository,
    ) -> None:
        self.client = client
        self.repository = repository

    def download_and_save_quote(
        self,
        symbol: str,
        currency: str = "USD",
    ) -> SavedQuoteResult:
        """
        Download a quote, save it and verify it can be read back.
        """
        quote = self.client.get_quote(
            symbol=symbol,
            currency=currency,
        )

        quote_id = self.repository.save(quote)
        saved_quote = self.repository.get(quote_id)

        if saved_quote is None:
            raise RuntimeError(
                f"Quote {quote_id} was saved but could not be read back."
            )

        if saved_quote != quote:
            raise RuntimeError(
                f"Quote {quote_id} changed during database persistence."
            )

        return SavedQuoteResult(
            quote_id=quote_id,
            quote=saved_quote,
        )