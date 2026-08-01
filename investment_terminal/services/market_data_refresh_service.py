"""
Automatic historical market-data freshness and refresh coordination.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from investment_terminal.services.historical_market_service import (
    HistoricalImportResult,
    HistoricalMarketService,
)
from investment_terminal.services.market_data_freshness_service import (
    MarketDataFreshnessResult,
    MarketDataFreshnessService,
)


@dataclass(frozen=True, slots=True)
class MarketDataRefreshResult:
    """
    Refresh outcome for one symbol and resolution.
    """

    symbol: str
    resolution: str
    checked_at: datetime
    freshness_before: MarketDataFreshnessResult
    freshness_after: MarketDataFreshnessResult
    import_result: HistoricalImportResult | None

    def __post_init__(self) -> None:
        normalized_symbol = self._normalize_text(
            self.symbol,
            field_name="symbol",
        )
        normalized_resolution = self._normalize_text(
            self.resolution,
            field_name="resolution",
        )

        self._validate_aware_datetime(
            self.checked_at,
            field_name="checked_at",
        )

        if not isinstance(
            self.freshness_before,
            MarketDataFreshnessResult,
        ):
            raise TypeError(
                "freshness_before must be a "
                "MarketDataFreshnessResult"
            )

        if not isinstance(
            self.freshness_after,
            MarketDataFreshnessResult,
        ):
            raise TypeError(
                "freshness_after must be a "
                "MarketDataFreshnessResult"
            )

        if (
            self.import_result is not None
            and not isinstance(
                self.import_result,
                HistoricalImportResult,
            )
        ):
            raise TypeError(
                "import_result must be a "
                "HistoricalImportResult or None"
            )

        if (
            self.freshness_before.symbol
            != normalized_symbol
            or self.freshness_after.symbol
            != normalized_symbol
        ):
            raise ValueError(
                "freshness results must match symbol"
            )

        if (
            self.freshness_before.resolution
            != normalized_resolution
            or self.freshness_after.resolution
            != normalized_resolution
        ):
            raise ValueError(
                "freshness results must match resolution"
            )

        if (
            not self.freshness_before.requires_refresh
            and self.import_result is not None
        ):
            raise ValueError(
                "fresh data must not contain an import result"
            )

        if (
            self.freshness_before.requires_refresh
            and self.import_result is None
        ):
            raise ValueError(
                "stale or missing data must contain "
                "an import result"
            )

        object.__setattr__(
            self,
            "symbol",
            normalized_symbol,
        )
        object.__setattr__(
            self,
            "resolution",
            normalized_resolution,
        )

    @property
    def refresh_attempted(self) -> bool:
        return self.import_result is not None

    @property
    def is_ready(self) -> bool:
        return self.freshness_after.is_fresh

    @property
    def downloaded(self) -> int:
        if self.import_result is None:
            return 0

        return self.import_result.downloaded

    @property
    def inserted(self) -> int:
        if self.import_result is None:
            return 0

        return self.import_result.inserted

    @property
    def duplicates(self) -> int:
        if self.import_result is None:
            return 0

        return self.import_result.duplicates

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the refresh result to JSON-ready data.
        """
        return {
            "symbol": self.symbol,
            "resolution": self.resolution,
            "checked_at": self.checked_at.isoformat(),
            "refresh_attempted": self.refresh_attempted,
            "is_ready": self.is_ready,
            "downloaded": self.downloaded,
            "inserted": self.inserted,
            "duplicates": self.duplicates,
            "freshness_before": (
                self.freshness_before.to_dict()
            ),
            "freshness_after": (
                self.freshness_after.to_dict()
            ),
            "import": (
                self._import_to_dict(
                    self.import_result
                )
                if self.import_result is not None
                else None
            ),
        }

    @staticmethod
    def _import_to_dict(
        result: HistoricalImportResult,
    ) -> dict[str, Any]:
        return {
            "symbol": result.symbol,
            "resolution": result.resolution,
            "downloaded": result.downloaded,
            "inserted": result.inserted,
            "duplicates": result.duplicates,
            "stored_total": result.stored_total,
            "start": result.start.isoformat(),
            "end": result.end.isoformat(),
        }

    @staticmethod
    def _normalize_text(
        value: object,
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

    @staticmethod
    def _validate_aware_datetime(
        value: object,
        field_name: str,
    ) -> None:
        if not isinstance(value, datetime):
            raise TypeError(
                f"{field_name} must be a datetime"
            )

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                f"{field_name} must be timezone-aware"
            )


@dataclass(frozen=True, slots=True)
class UniverseMarketDataRefreshResult:
    """
    Refresh outcome for a complete asset universe.
    """

    checked_at: datetime
    results: tuple[
        MarketDataRefreshResult,
        ...,
    ]

    def __post_init__(self) -> None:
        MarketDataRefreshResult._validate_aware_datetime(
            self.checked_at,
            field_name="checked_at",
        )

        if not isinstance(
            self.results,
            tuple,
        ):
            raise TypeError(
                "results must be a tuple"
            )

        if not self.results:
            raise ValueError(
                "results must not be empty"
            )

        if any(
            not isinstance(
                result,
                MarketDataRefreshResult,
            )
            for result in self.results
        ):
            raise TypeError(
                "results must contain only "
                "MarketDataRefreshResult objects"
            )

        symbols = [
            result.symbol
            for result in self.results
        ]

        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "results must contain unique symbols"
            )

    @property
    def universe_size(self) -> int:
        return len(self.results)

    @property
    def ready_count(self) -> int:
        return sum(
            result.is_ready
            for result in self.results
        )

    @property
    def failed_count(self) -> int:
        return (
            self.universe_size
            - self.ready_count
        )

    @property
    def refreshed_count(self) -> int:
        return sum(
            result.refresh_attempted
            for result in self.results
        )

    @property
    def all_ready(self) -> bool:
        return self.failed_count == 0

    @property
    def failed_symbols(self) -> tuple[str, ...]:
        return tuple(
            result.symbol
            for result in self.results
            if not result.is_ready
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the universe result to JSON-ready data.
        """
        return {
            "checked_at": self.checked_at.isoformat(),
            "universe_size": self.universe_size,
            "ready_count": self.ready_count,
            "failed_count": self.failed_count,
            "refreshed_count": self.refreshed_count,
            "all_ready": self.all_ready,
            "failed_symbols": list(
                self.failed_symbols
            ),
            "results": [
                result.to_dict()
                for result in self.results
            ],
        }


class MarketDataRefreshService:
    """
    Refresh stale or missing historical market data.
    """

    DEFAULT_INITIAL_LOOKBACK = timedelta(
        days=3 * 365
    )
    DEFAULT_STALE_OVERLAP = timedelta(
        days=7
    )
    DEFAULT_END_BUFFER = timedelta(
        days=1
    )

    def __init__(
        self,
        freshness_service: MarketDataFreshnessService,
        historical_market_service: HistoricalMarketService,
        initial_lookback: timedelta = DEFAULT_INITIAL_LOOKBACK,
        stale_overlap: timedelta = DEFAULT_STALE_OVERLAP,
        end_buffer: timedelta = DEFAULT_END_BUFFER,
    ) -> None:
        if not isinstance(
            freshness_service,
            MarketDataFreshnessService,
        ):
            raise TypeError(
                "freshness_service must be a "
                "MarketDataFreshnessService"
            )

        if not isinstance(
            historical_market_service,
            HistoricalMarketService,
        ):
            raise TypeError(
                "historical_market_service must be a "
                "HistoricalMarketService"
            )

        self._validate_positive_timedelta(
            initial_lookback,
            field_name="initial_lookback",
        )
        self._validate_positive_timedelta(
            stale_overlap,
            field_name="stale_overlap",
        )
        self._validate_positive_timedelta(
            end_buffer,
            field_name="end_buffer",
        )

        self.freshness_service = (
            freshness_service
        )
        self.historical_market_service = (
            historical_market_service
        )
        self.initial_lookback = (
            initial_lookback
        )
        self.stale_overlap = stale_overlap
        self.end_buffer = end_buffer

    def ensure_fresh(
        self,
        symbol: str,
        resolution: str,
        currency: str = "USD",
        checked_at: datetime | None = None,
    ) -> MarketDataRefreshResult:
        """
        Ensure one candle series is fresh enough for analysis.
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
        resolved_checked_at = self._resolve_checked_at(
            checked_at
        )

        freshness_before = (
            self.freshness_service.check(
                symbol=normalized_symbol,
                resolution=normalized_resolution,
                checked_at=resolved_checked_at,
            )
        )

        if not freshness_before.requires_refresh:
            return MarketDataRefreshResult(
                symbol=normalized_symbol,
                resolution=normalized_resolution,
                checked_at=resolved_checked_at,
                freshness_before=freshness_before,
                freshness_after=freshness_before,
                import_result=None,
            )

        start = self._resolve_import_start(
            freshness=freshness_before,
            checked_at=resolved_checked_at,
        )
        end = (
            resolved_checked_at
            + self.end_buffer
        )

        import_result = (
            self.historical_market_service
            .import_candles(
                symbol=normalized_symbol,
                resolution=normalized_resolution,
                start=start,
                end=end,
                currency=normalized_currency,
            )
        )

        freshness_after = (
            self.freshness_service.check(
                symbol=normalized_symbol,
                resolution=normalized_resolution,
                checked_at=resolved_checked_at,
            )
        )

        return MarketDataRefreshResult(
            symbol=normalized_symbol,
            resolution=normalized_resolution,
            checked_at=resolved_checked_at,
            freshness_before=freshness_before,
            freshness_after=freshness_after,
            import_result=import_result,
        )

    def ensure_many(
        self,
        symbols: list[str] | tuple[str, ...],
        resolution: str,
        currency: str = "USD",
        checked_at: datetime | None = None,
    ) -> UniverseMarketDataRefreshResult:
        """
        Ensure every symbol in an asset universe is fresh.
        """
        if not isinstance(
            symbols,
            (list, tuple),
        ):
            raise TypeError(
                "symbols must be a list or tuple"
            )

        if not symbols:
            raise ValueError(
                "symbols must not be empty"
            )

        normalized_symbols = tuple(
            self._normalize_text(
                symbol,
                field_name="symbol",
            )
            for symbol in symbols
        )

        if len(normalized_symbols) != len(
            set(normalized_symbols)
        ):
            raise ValueError(
                "symbols must contain unique values"
            )

        normalized_resolution = self._normalize_text(
            resolution,
            field_name="resolution",
        )
        normalized_currency = self._normalize_text(
            currency,
            field_name="currency",
        )
        resolved_checked_at = self._resolve_checked_at(
            checked_at
        )

        results = tuple(
            self.ensure_fresh(
                symbol=symbol,
                resolution=normalized_resolution,
                currency=normalized_currency,
                checked_at=resolved_checked_at,
            )
            for symbol in normalized_symbols
        )

        return UniverseMarketDataRefreshResult(
            checked_at=resolved_checked_at,
            results=results,
        )

    def _resolve_import_start(
        self,
        freshness: MarketDataFreshnessResult,
        checked_at: datetime,
    ) -> datetime:
        if freshness.is_missing:
            return (
                checked_at
                - self.initial_lookback
            )

        if freshness.last_candle_at is None:
            raise RuntimeError(
                "stale freshness result is missing "
                "last_candle_at"
            )

        return (
            freshness.last_candle_at
            - self.stale_overlap
        )

    @staticmethod
    def _normalize_text(
        value: object,
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

    @classmethod
    def _resolve_checked_at(
        cls,
        checked_at: datetime | None,
    ) -> datetime:
        if checked_at is None:
            return datetime.now(
                timezone.utc
            )

        if not isinstance(
            checked_at,
            datetime,
        ):
            raise TypeError(
                "checked_at must be a datetime"
            )

        if (
            checked_at.tzinfo is None
            or checked_at.utcoffset() is None
        ):
            raise ValueError(
                "checked_at must be timezone-aware"
            )

        return checked_at.astimezone(
            timezone.utc
        )

    @staticmethod
    def _validate_positive_timedelta(
        value: object,
        field_name: str,
    ) -> None:
        if not isinstance(
            value,
            timedelta,
        ):
            raise TypeError(
                f"{field_name} must be a timedelta"
            )

        if value <= timedelta(0):
            raise ValueError(
                f"{field_name} must be greater than zero"
            )