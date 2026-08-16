"""
Provider-independent exchange, calendar, and currency metadata contracts.
"""

from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class CurrencyMetadata:
    """Normalized metadata for one monetary currency."""

    code: str
    name: str
    minor_unit: int

    def __post_init__(self) -> None:
        code = normalize_required_text(
            self.code,
            field_name="code",
            uppercase=True,
        )
        if len(code) != 3 or not code.isalpha():
            raise ValueError(
                "code must be a three-letter alphabetic currency code"
            )
        if (
            isinstance(self.minor_unit, bool)
            or not isinstance(self.minor_unit, int)
            or not 0 <= self.minor_unit <= 9
        ):
            raise ValueError(
                "minor_unit must be an integer between 0 and 9"
            )

        object.__setattr__(self, "code", code)
        object.__setattr__(
            self,
            "name",
            normalize_required_text(
                self.name,
                field_name="name",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "minor_unit": self.minor_unit,
        }


@dataclass(frozen=True, slots=True)
class TradingCalendarMetadata:
    """Versioned identity and provenance for a trading calendar."""

    calendar_id: str
    timezone: str
    version: int
    source: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or self.version <= 0
        ):
            raise ValueError("version must be a positive integer")

        timezone = normalize_required_text(
            self.timezone,
            field_name="timezone",
        )
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError(
                "timezone must be a valid IANA timezone"
            ) from error

        object.__setattr__(
            self,
            "calendar_id",
            _normalize_code(
                self.calendar_id,
                field_name="calendar_id",
            ),
        )
        object.__setattr__(self, "timezone", timezone)
        object.__setattr__(
            self,
            "source",
            _normalize_code(
                self.source,
                field_name="source",
            ),
        )

    @property
    def identity_key(self) -> str:
        return f"{self.calendar_id}@{self.version}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "calendar_id": self.calendar_id,
            "version": self.version,
            "identity_key": self.identity_key,
            "timezone": self.timezone,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class ExchangeMetadata:
    """Normalized exchange identity and its market-data conventions."""

    exchange_code: str
    name: str
    country_code: str
    calendar: TradingCalendarMetadata
    currency_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        country_code = _normalize_code(
            self.country_code,
            field_name="country_code",
        )
        if len(country_code) != 2 or not country_code.isalpha():
            raise ValueError(
                "country_code must be a two-letter alphabetic code"
            )
        if not isinstance(self.calendar, TradingCalendarMetadata):
            raise TypeError(
                "calendar must be a TradingCalendarMetadata"
            )
        if not isinstance(self.currency_codes, tuple):
            raise TypeError("currency_codes must be a tuple")
        if not self.currency_codes:
            raise ValueError("currency_codes must not be empty")

        currency_codes = tuple(
            _normalize_currency_code(code)
            for code in self.currency_codes
        )
        if len(currency_codes) != len(set(currency_codes)):
            raise ValueError(
                "currency_codes must contain unique values"
            )

        object.__setattr__(
            self,
            "exchange_code",
            _normalize_code(
                self.exchange_code,
                field_name="exchange_code",
            ),
        )
        object.__setattr__(
            self,
            "name",
            normalize_required_text(
                self.name,
                field_name="name",
            ),
        )
        object.__setattr__(self, "country_code", country_code)
        object.__setattr__(self, "currency_codes", currency_codes)

    def supports_currency(self, code: str) -> bool:
        return _normalize_currency_code(code) in self.currency_codes

    def to_dict(self) -> dict[str, Any]:
        return {
            "exchange_code": self.exchange_code,
            "name": self.name,
            "country_code": self.country_code,
            "calendar": self.calendar.to_dict(),
            "currency_codes": list(self.currency_codes),
        }


def _normalize_code(
    value: object,
    *,
    field_name: str,
) -> str:
    code = normalize_required_text(
        value,
        field_name=field_name,
        uppercase=True,
    )
    if any(character.isspace() for character in code):
        raise ValueError(f"{field_name} must not contain whitespace")
    return code


def _normalize_currency_code(value: object) -> str:
    code = _normalize_code(
        value,
        field_name="currency code",
    )
    if len(code) != 3 or not code.isalpha():
        raise ValueError(
            "currency code must contain three alphabetic characters"
        )
    return code
