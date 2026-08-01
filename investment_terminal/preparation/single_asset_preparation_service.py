"""
Prepare historical data for one asset.
"""

from collections.abc import Callable
from datetime import datetime, timezone

from investment_terminal.preparation.preparation_models import (
    PreparationAssetResult,
)
from investment_terminal.services.historical_market_service import (
    HistoricalMarketService,
)


class SingleAssetPreparationService:
    """
    Run one historical import and convert it into a preparation result.
    """

    def __init__(
        self,
        historical_service: HistoricalMarketService,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.historical_service = historical_service
        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

    def prepare(
        self,
        symbol: str,
        resolution: str,
        start: datetime,
        end: datetime,
        currency: str = "USD",
    ) -> PreparationAssetResult:
        """
        Prepare historical data for one symbol.

        Provider and persistence errors are converted into a failed
        PreparationAssetResult instead of being raised.
        """
        normalized_symbol = self._normalize_text(
            symbol,
            field_name="symbol",
        )
        normalized_resolution = self._normalize_text(
            resolution,
            field_name="resolution",
        )
        normalized_currency = self._normalize_text(
            currency,
            field_name="currency",
        )

        self._validate_datetime(
            start,
            field_name="start",
        )
        self._validate_datetime(
            end,
            field_name="end",
        )

        if end <= start:
            raise ValueError(
                "end must be after start"
            )

        started_at = self._now()

        try:
            import_result = (
                self.historical_service.import_candles(
                    symbol=normalized_symbol,
                    resolution=normalized_resolution,
                    start=start,
                    end=end,
                    currency=normalized_currency,
                )
            )
        except Exception as exc:
            finished_at = self._now()

            return PreparationAssetResult(
                symbol=normalized_symbol,
                success=False,
                downloaded=0,
                inserted=0,
                duplicates=0,
                started_at=started_at,
                finished_at=finished_at,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

        finished_at = self._now()

        return PreparationAssetResult(
            symbol=import_result.symbol,
            success=True,
            downloaded=import_result.downloaded,
            inserted=import_result.inserted,
            duplicates=import_result.duplicates,
            started_at=started_at,
            finished_at=finished_at,
        )

    def _now(self) -> datetime:
        value = self._clock()

        if not isinstance(value, datetime):
            raise TypeError(
                "clock must return a datetime"
            )

        return value

    @staticmethod
    def _validate_datetime(
        value: object,
        field_name: str,
    ) -> None:
        if not isinstance(value, datetime):
            raise TypeError(
                f"{field_name} must be a datetime"
            )

    @staticmethod
    def _normalize_text(
        value: str,
        field_name: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} must be a non-empty string"
            )

        return value.strip().upper()