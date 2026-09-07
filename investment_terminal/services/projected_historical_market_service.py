"""Manifest-only historical import with typed Yahoo projection evidence."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ProjectedHistoricalImportResult:
    downloaded: int
    inserted: int
    duplicates: int
    omitted_trailing_count: int
    omission_types: tuple[str, ...]


class ProjectedHistoricalMarketService:
    def __init__(self, client, repository) -> None:
        self.client = client
        self.repository = repository

    def import_candles(
        self,
        symbol: str,
        resolution: str,
        start: datetime,
        end: datetime,
        currency: str = "USD",
    ) -> ProjectedHistoricalImportResult:
        projection = self.client.get_candle_projection(
            symbol=symbol,
            resolution=resolution,
            start=start,
            end=end,
            currency=currency,
            allow_trailing_incomplete=True,
        )
        candles = list(projection.candles)
        downloaded = len(candles)
        inserted = self.repository.save_many(candles)
        if inserted < 0 or inserted > downloaded:
            raise RuntimeError("CandleRepository returned an invalid inserted count.")
        return ProjectedHistoricalImportResult(
            downloaded=downloaded,
            inserted=inserted,
            duplicates=downloaded - inserted,
            omitted_trailing_count=projection.omitted_trailing_count,
            omission_types=projection.omission_types,
        )
