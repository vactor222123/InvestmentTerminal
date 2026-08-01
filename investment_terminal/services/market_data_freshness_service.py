"""
Historical market-data freshness evaluation.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)


FRESHNESS_STATUSES = (
    "FRESH",
    "STALE",
    "MISSING",
)


@dataclass(frozen=True, slots=True)
class MarketDataFreshnessResult:
    """
    Freshness state for one symbol and candle resolution.
    """

    symbol: str
    resolution: str
    checked_at: datetime
    maximum_age_hours: float
    status: str
    last_candle_at: datetime | None
    age_hours: float | None

    def __post_init__(self) -> None:
        normalized_symbol = self._normalize_text(
            self.symbol,
            field_name="symbol",
        )
        normalized_resolution = self._normalize_text(
            self.resolution,
            field_name="resolution",
        )
        normalized_status = self._normalize_status(
            self.status
        )

        self._validate_aware_datetime(
            self.checked_at,
            field_name="checked_at",
        )

        if (
            isinstance(self.maximum_age_hours, bool)
            or not isinstance(
                self.maximum_age_hours,
                (int, float),
            )
            or self.maximum_age_hours <= 0
        ):
            raise ValueError(
                "maximum_age_hours must be greater than zero"
            )

        if self.last_candle_at is not None:
            self._validate_aware_datetime(
                self.last_candle_at,
                field_name="last_candle_at",
            )

        if self.age_hours is not None:
            if (
                isinstance(self.age_hours, bool)
                or not isinstance(
                    self.age_hours,
                    (int, float),
                )
                or self.age_hours < 0
            ):
                raise ValueError(
                    "age_hours must be a non-negative number "
                    "or None"
                )

        if normalized_status == "MISSING":
            if (
                self.last_candle_at is not None
                or self.age_hours is not None
            ):
                raise ValueError(
                    "MISSING freshness results must not contain "
                    "last_candle_at or age_hours"
                )
        else:
            if (
                self.last_candle_at is None
                or self.age_hours is None
            ):
                raise ValueError(
                    "FRESH and STALE results must contain "
                    "last_candle_at and age_hours"
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
        object.__setattr__(
            self,
            "status",
            normalized_status,
        )
        object.__setattr__(
            self,
            "maximum_age_hours",
            float(self.maximum_age_hours),
        )

        if self.age_hours is not None:
            object.__setattr__(
                self,
                "age_hours",
                round(
                    float(self.age_hours),
                    4,
                ),
            )

    @property
    def is_fresh(self) -> bool:
        return self.status == "FRESH"

    @property
    def is_stale(self) -> bool:
        return self.status == "STALE"

    @property
    def is_missing(self) -> bool:
        return self.status == "MISSING"

    @property
    def requires_refresh(self) -> bool:
        return self.status in {
            "STALE",
            "MISSING",
        }

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the freshness result to JSON-ready data.
        """
        return {
            "symbol": self.symbol,
            "resolution": self.resolution,
            "checked_at": self.checked_at.isoformat(),
            "maximum_age_hours": self.maximum_age_hours,
            "status": self.status,
            "last_candle_at": (
                self.last_candle_at.isoformat()
                if self.last_candle_at is not None
                else None
            ),
            "age_hours": self.age_hours,
            "is_fresh": self.is_fresh,
            "requires_refresh": self.requires_refresh,
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
    def _normalize_status(
        value: object,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                "status must be a non-empty string"
            )

        normalized = value.strip().upper()

        if normalized not in FRESHNESS_STATUSES:
            supported = ", ".join(
                FRESHNESS_STATUSES
            )
            raise ValueError(
                f"Unsupported freshness status '{normalized}'. "
                f"Supported values: {supported}."
            )

        return normalized

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


class MarketDataFreshnessService:
    """
    Evaluate whether stored historical candles are sufficiently recent.
    """

    DEFAULT_MAXIMUM_AGE = timedelta(
        hours=24
    )

    def __init__(
        self,
        repository: CandleRepository,
        maximum_age: timedelta = DEFAULT_MAXIMUM_AGE,
    ) -> None:
        if not isinstance(
            repository,
            CandleRepository,
        ):
            raise TypeError(
                "repository must be a CandleRepository"
            )

        if not isinstance(
            maximum_age,
            timedelta,
        ):
            raise TypeError(
                "maximum_age must be a timedelta"
            )

        if maximum_age <= timedelta(0):
            raise ValueError(
                "maximum_age must be greater than zero"
            )

        self.repository = repository
        self.maximum_age = maximum_age

    def check(
        self,
        symbol: str,
        resolution: str,
        checked_at: datetime | None = None,
    ) -> MarketDataFreshnessResult:
        """
        Evaluate freshness for one stored candle series.
        """
        normalized_symbol = self._normalize_text(
            symbol,
            field_name="symbol",
        )
        normalized_resolution = self._normalize_text(
            resolution,
            field_name="resolution",
        )
        resolved_checked_at = self._resolve_checked_at(
            checked_at
        )

        latest_candle = self.repository.get_latest(
            symbol=normalized_symbol,
            resolution=normalized_resolution,
        )

        maximum_age_hours = (
            self.maximum_age.total_seconds()
            / 3600.0
        )

        if latest_candle is None:
            return MarketDataFreshnessResult(
                symbol=normalized_symbol,
                resolution=normalized_resolution,
                checked_at=resolved_checked_at,
                maximum_age_hours=maximum_age_hours,
                status="MISSING",
                last_candle_at=None,
                age_hours=None,
            )

        last_candle_at = self._normalize_datetime(
            latest_candle.timestamp,
            field_name="latest candle timestamp",
        )

        if last_candle_at > resolved_checked_at:
            raise ValueError(
                "latest candle timestamp must not be "
                "later than checked_at"
            )

        age = (
            resolved_checked_at
            - last_candle_at
        )
        age_hours = (
            age.total_seconds()
            / 3600.0
        )

        status = (
            "FRESH"
            if age <= self.maximum_age
            else "STALE"
        )

        return MarketDataFreshnessResult(
            symbol=normalized_symbol,
            resolution=normalized_resolution,
            checked_at=resolved_checked_at,
            maximum_age_hours=maximum_age_hours,
            status=status,
            last_candle_at=last_candle_at,
            age_hours=age_hours,
        )

    def check_many(
        self,
        symbols: list[str] | tuple[str, ...],
        resolution: str,
        checked_at: datetime | None = None,
    ) -> tuple[
        MarketDataFreshnessResult,
        ...,
    ]:
        """
        Evaluate freshness for every symbol in a universe.
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
        resolved_checked_at = self._resolve_checked_at(
            checked_at
        )

        return tuple(
            self.check(
                symbol=symbol,
                resolution=normalized_resolution,
                checked_at=resolved_checked_at,
            )
            for symbol in normalized_symbols
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

        return cls._normalize_datetime(
            checked_at,
            field_name="checked_at",
        )

    @staticmethod
    def _normalize_datetime(
        value: object,
        field_name: str,
    ) -> datetime:
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

        return value.astimezone(
            timezone.utc
        )