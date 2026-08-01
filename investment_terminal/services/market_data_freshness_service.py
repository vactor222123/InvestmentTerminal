"""
Trading-session-aware historical market-data freshness evaluation.
"""

from dataclasses import dataclass
from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone,
)
from typing import Any
from zoneinfo import ZoneInfo

from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)


FRESHNESS_STATUSES = (
    "FRESH",
    "STALE",
    "MISSING",
)

FRESHNESS_POLICIES = (
    "AGE",
    "TRADING_SESSION",
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
    policy: str = "AGE"
    expected_session_date: date | None = None
    last_candle_session_date: date | None = None

    def __post_init__(self) -> None:
        normalized_symbol = self._normalize_text(
            self.symbol,
            field_name="symbol",
        )
        normalized_resolution = self._normalize_text(
            self.resolution,
            field_name="resolution",
        )
        normalized_status = self._normalize_choice(
            self.status,
            field_name="status",
            supported=FRESHNESS_STATUSES,
        )
        normalized_policy = self._normalize_choice(
            self.policy,
            field_name="policy",
            supported=FRESHNESS_POLICIES,
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

        for field_name in (
            "expected_session_date",
            "last_candle_session_date",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                value is not None
                and not isinstance(value, date)
            ):
                raise TypeError(
                    f"{field_name} must be a date or None"
                )

        if normalized_status == "MISSING":
            if (
                self.last_candle_at is not None
                or self.age_hours is not None
                or self.last_candle_session_date is not None
            ):
                raise ValueError(
                    "MISSING freshness results must not contain "
                    "last-candle information"
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

        if normalized_policy == "TRADING_SESSION":
            if self.expected_session_date is None:
                raise ValueError(
                    "TRADING_SESSION results must contain "
                    "expected_session_date"
                )

            if (
                normalized_status != "MISSING"
                and self.last_candle_session_date is None
            ):
                raise ValueError(
                    "non-missing TRADING_SESSION results must "
                    "contain last_candle_session_date"
                )
        elif (
            self.expected_session_date is not None
            or self.last_candle_session_date is not None
        ):
            raise ValueError(
                "AGE results must not contain session dates"
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
            "policy",
            normalized_policy,
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
            "policy": self.policy,
            "status": self.status,
            "last_candle_at": (
                self.last_candle_at.isoformat()
                if self.last_candle_at is not None
                else None
            ),
            "age_hours": self.age_hours,
            "expected_session_date": (
                self.expected_session_date.isoformat()
                if self.expected_session_date is not None
                else None
            ),
            "last_candle_session_date": (
                self.last_candle_session_date.isoformat()
                if self.last_candle_session_date is not None
                else None
            ),
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
    def _normalize_choice(
        value: object,
        field_name: str,
        supported: tuple[str, ...],
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} must be a non-empty string"
            )

        normalized = value.strip().upper()

        if normalized not in supported:
            supported_text = ", ".join(
                supported
            )
            raise ValueError(
                f"Unsupported {field_name} '{normalized}'. "
                f"Supported values: {supported_text}."
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


class UnitedStatesMarketCalendar:
    """
    Lightweight calendar for regular US equity sessions.

    It covers weekends and the standard recurring NYSE holidays.
    It does not attempt to predict unscheduled emergency closures.
    """

    MARKET_TIMEZONE = ZoneInfo(
        "America/New_York"
    )

    DAILY_PUBLICATION_CUTOFF = time(
        hour=18,
        minute=0,
    )

    def expected_latest_session(
        self,
        checked_at: datetime,
    ) -> date:
        """
        Return the latest daily session expected to be available.
        """
        checked_at_utc = self._normalize_datetime(
            checked_at
        )
        local_time = checked_at_utc.astimezone(
            self.MARKET_TIMEZONE
        )
        candidate = local_time.date()

        if (
            self.is_trading_day(candidate)
            and local_time.time()
            >= self.DAILY_PUBLICATION_CUTOFF
        ):
            return candidate

        return self.previous_trading_day(
            candidate
        )

    def previous_trading_day(
        self,
        value: date,
    ) -> date:
        """
        Return the trading day strictly before the supplied date.
        """
        candidate = (
            value
            - timedelta(days=1)
        )

        while not self.is_trading_day(
            candidate
        ):
            candidate -= timedelta(
                days=1
            )

        return candidate

    def is_trading_day(
        self,
        value: date,
    ) -> bool:
        """
        Return whether the date is a regular US equity session.
        """
        if not isinstance(value, date):
            raise TypeError(
                "value must be a date"
            )

        if value.weekday() >= 5:
            return False

        return value not in self.holidays(
            value.year
        )

    def holidays(
        self,
        year: int,
    ) -> set[date]:
        """
        Return recurring full-day US equity holidays.
        """
        holidays: set[date] = set()

        for holiday_year in (
            year - 1,
            year,
            year + 1,
        ):
            holidays.update(
                self._holidays_for_year(
                    holiday_year
                )
            )

        return {
            holiday
            for holiday in holidays
            if holiday.year == year
        }

    def _holidays_for_year(
        self,
        year: int,
    ) -> set[date]:
        holidays = {
            self._observed_fixed_holiday(
                date(
                    year,
                    1,
                    1,
                )
            ),
            self._nth_weekday(
                year=year,
                month=1,
                weekday=0,
                occurrence=3,
            ),
            self._nth_weekday(
                year=year,
                month=2,
                weekday=0,
                occurrence=3,
            ),
            self._easter_sunday(
                year
            ) - timedelta(days=2),
            self._last_weekday(
                year=year,
                month=5,
                weekday=0,
            ),
            self._observed_fixed_holiday(
                date(
                    year,
                    7,
                    4,
                )
            ),
            self._nth_weekday(
                year=year,
                month=9,
                weekday=0,
                occurrence=1,
            ),
            self._nth_weekday(
                year=year,
                month=11,
                weekday=3,
                occurrence=4,
            ),
            self._observed_fixed_holiday(
                date(
                    year,
                    12,
                    25,
                )
            ),
        }

        if year >= 2022:
            holidays.add(
                self._observed_fixed_holiday(
                    date(
                        year,
                        6,
                        19,
                    )
                )
            )

        return holidays

    @staticmethod
    def _observed_fixed_holiday(
        holiday: date,
    ) -> date:
        if holiday.weekday() == 5:
            return holiday - timedelta(
                days=1
            )

        if holiday.weekday() == 6:
            return holiday + timedelta(
                days=1
            )

        return holiday

    @staticmethod
    def _nth_weekday(
        *,
        year: int,
        month: int,
        weekday: int,
        occurrence: int,
    ) -> date:
        first = date(
            year,
            month,
            1,
        )
        offset = (
            weekday
            - first.weekday()
        ) % 7

        return first + timedelta(
            days=(
                offset
                + 7 * (
                    occurrence - 1
                )
            )
        )

    @staticmethod
    def _last_weekday(
        *,
        year: int,
        month: int,
        weekday: int,
    ) -> date:
        if month == 12:
            next_month = date(
                year + 1,
                1,
                1,
            )
        else:
            next_month = date(
                year,
                month + 1,
                1,
            )

        candidate = (
            next_month
            - timedelta(days=1)
        )

        while candidate.weekday() != weekday:
            candidate -= timedelta(
                days=1
            )

        return candidate

    @staticmethod
    def _easter_sunday(
        year: int,
    ) -> date:
        """
        Calculate Gregorian Easter Sunday.
        """
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (
            b + 8
        ) // 25
        g = (
            b - f + 1
        ) // 3
        h = (
            19 * a
            + b
            - d
            - g
            + 15
        ) % 30
        i = c // 4
        k = c % 4
        l = (
            32
            + 2 * e
            + 2 * i
            - h
            - k
        ) % 7
        m = (
            a
            + 11 * h
            + 22 * l
        ) // 451
        month = (
            h
            + l
            - 7 * m
            + 114
        ) // 31
        day = (
            (
                h
                + l
                - 7 * m
                + 114
            ) % 31
            + 1
        )

        return date(
            year,
            month,
            day,
        )

    @staticmethod
    def _normalize_datetime(
        value: object,
    ) -> datetime:
        if not isinstance(value, datetime):
            raise TypeError(
                "checked_at must be a datetime"
            )

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "checked_at must be timezone-aware"
            )

        return value.astimezone(
            timezone.utc
        )


class MarketDataFreshnessService:
    """
    Evaluate whether stored historical candles are current enough.
    """

    DEFAULT_MAXIMUM_AGE = timedelta(
        hours=24
    )

    def __init__(
        self,
        repository: CandleRepository,
        maximum_age: timedelta = DEFAULT_MAXIMUM_AGE,
        market_calendar: UnitedStatesMarketCalendar | None = None,
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

        if (
            market_calendar is not None
            and not isinstance(
                market_calendar,
                UnitedStatesMarketCalendar,
            )
        ):
            raise TypeError(
                "market_calendar must be a "
                "UnitedStatesMarketCalendar or None"
            )

        self.repository = repository
        self.maximum_age = maximum_age
        self.market_calendar = (
            market_calendar
            or UnitedStatesMarketCalendar()
        )

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

        if normalized_resolution == "D":
            return self._check_daily(
                symbol=normalized_symbol,
                resolution=normalized_resolution,
                checked_at=resolved_checked_at,
                maximum_age_hours=maximum_age_hours,
                latest_candle=latest_candle,
            )

        return self._check_by_age(
            symbol=normalized_symbol,
            resolution=normalized_resolution,
            checked_at=resolved_checked_at,
            maximum_age_hours=maximum_age_hours,
            latest_candle=latest_candle,
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

    def _check_daily(
        self,
        *,
        symbol: str,
        resolution: str,
        checked_at: datetime,
        maximum_age_hours: float,
        latest_candle,
    ) -> MarketDataFreshnessResult:
        expected_session = (
            self.market_calendar
            .expected_latest_session(
                checked_at
            )
        )

        if latest_candle is None:
            return MarketDataFreshnessResult(
                symbol=symbol,
                resolution=resolution,
                checked_at=checked_at,
                maximum_age_hours=maximum_age_hours,
                status="MISSING",
                last_candle_at=None,
                age_hours=None,
                policy="TRADING_SESSION",
                expected_session_date=expected_session,
                last_candle_session_date=None,
            )

        last_candle_at = self._normalize_datetime(
            latest_candle.timestamp,
            field_name="latest candle timestamp",
        )

        self._reject_future_candle(
            last_candle_at=last_candle_at,
            checked_at=checked_at,
        )

        age_hours = (
            checked_at
            - last_candle_at
        ).total_seconds() / 3600.0

        candle_session = (
            last_candle_at.astimezone(
                self.market_calendar
                .MARKET_TIMEZONE
            ).date()
        )

        status = (
            "FRESH"
            if candle_session >= expected_session
            else "STALE"
        )

        return MarketDataFreshnessResult(
            symbol=symbol,
            resolution=resolution,
            checked_at=checked_at,
            maximum_age_hours=maximum_age_hours,
            status=status,
            last_candle_at=last_candle_at,
            age_hours=age_hours,
            policy="TRADING_SESSION",
            expected_session_date=expected_session,
            last_candle_session_date=candle_session,
        )

    def _check_by_age(
        self,
        *,
        symbol: str,
        resolution: str,
        checked_at: datetime,
        maximum_age_hours: float,
        latest_candle,
    ) -> MarketDataFreshnessResult:
        if latest_candle is None:
            return MarketDataFreshnessResult(
                symbol=symbol,
                resolution=resolution,
                checked_at=checked_at,
                maximum_age_hours=maximum_age_hours,
                status="MISSING",
                last_candle_at=None,
                age_hours=None,
                policy="AGE",
            )

        last_candle_at = self._normalize_datetime(
            latest_candle.timestamp,
            field_name="latest candle timestamp",
        )

        self._reject_future_candle(
            last_candle_at=last_candle_at,
            checked_at=checked_at,
        )

        age = (
            checked_at
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
            symbol=symbol,
            resolution=resolution,
            checked_at=checked_at,
            maximum_age_hours=maximum_age_hours,
            status=status,
            last_candle_at=last_candle_at,
            age_hours=age_hours,
            policy="AGE",
        )

    @staticmethod
    def _reject_future_candle(
        *,
        last_candle_at: datetime,
        checked_at: datetime,
    ) -> None:
        if last_candle_at > checked_at:
            raise ValueError(
                "latest candle timestamp must not be "
                "later than checked_at"
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