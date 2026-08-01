"""
Historical market-data download and persistence service.
"""

from dataclasses import dataclass
from datetime import datetime

from investment_terminal.clients.historical_data_client import (
    HistoricalDataClient,
)
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)


@dataclass(frozen=True, slots=True)
class HistoricalImportResult:
    """
    Statistics produced by one historical-data import.
    """

    symbol: str
    resolution: str
    downloaded: int
    inserted: int
    duplicates: int
    stored_total: int
    start: datetime
    end: datetime


class HistoricalMarketService:
    """
    Coordinate historical market-data downloads and persistence.
    """

    def __init__(
        self,
        client: HistoricalDataClient,
        repository: CandleRepository,
    ) -> None:
        self.client = client
        self.repository = repository

    def import_candles(
        self,
        symbol: str,
        resolution: str,
        start: datetime,
        end: datetime,
        currency: str = "USD",
    ) -> HistoricalImportResult:
        """
        Download candles and store only previously unseen records.
        """
        candles = self.client.get_candles(
            symbol=symbol,
            resolution=resolution,
            start=start,
            end=end,
            currency=currency,
        )

        normalized_symbol = symbol.strip().upper()
        normalized_resolution = resolution.strip().upper()

        downloaded = len(candles)
        inserted = self.repository.save_many(candles)

        if inserted < 0 or inserted > downloaded:
            raise RuntimeError(
                "CandleRepository returned an invalid inserted count."
            )

        duplicates = downloaded - inserted
        stored_total = self.repository.count(
            normalized_symbol,
            normalized_resolution,
        )

        return HistoricalImportResult(
            symbol=normalized_symbol,
            resolution=normalized_resolution,
            downloaded=downloaded,
            inserted=inserted,
            duplicates=duplicates,
            stored_total=stored_total,
            start=start,
            end=end,
        )