"""
Canonical identity contract for market instruments.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
)

SUPPORTED_INSTRUMENT_TYPES = (
    "ETF",
    "STOCK",
    "BOND",
    "GOLD",
    "OTHER",
)


@dataclass(frozen=True, slots=True)
class InstrumentIdentity:
    """Provider-independent identity for one investable instrument."""

    symbol: str
    name: str
    instrument_type: str
    currency: str
    isin: str | None = None
    exchange_ticker: str | None = None
    exchange_code: str | None = None

    def __post_init__(self) -> None:
        symbol = normalize_required_text(
            self.symbol,
            field_name="symbol",
            uppercase=True,
        )
        if any(character.isspace() for character in symbol):
            raise ValueError("symbol must not contain whitespace")

        instrument_type = normalize_required_text(
            self.instrument_type,
            field_name="instrument_type",
            uppercase=True,
        )
        if instrument_type not in SUPPORTED_INSTRUMENT_TYPES:
            raise ValueError(
                "instrument_type must be one of: "
                + ", ".join(SUPPORTED_INSTRUMENT_TYPES)
            )

        currency = normalize_required_text(
            self.currency,
            field_name="currency",
            uppercase=True,
        )
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a three-letter alphabetic code")

        isin = normalize_optional_text(
            self.isin,
            field_name="isin",
            uppercase=True,
        )
        if isin is not None and (
            len(isin) != 12 or not isin[:2].isalpha() or not isin[2:].isalnum()
        ):
            raise ValueError(
                "isin must contain 12 alphanumeric characters "
                "and start with a two-letter country code"
            )

        exchange_ticker = normalize_optional_text(
            self.exchange_ticker,
            field_name="exchange_ticker",
            uppercase=True,
        )
        if exchange_ticker is not None and any(
            character.isspace() for character in exchange_ticker
        ):
            raise ValueError("exchange_ticker must not contain whitespace")

        exchange_code = normalize_optional_text(
            self.exchange_code,
            field_name="exchange_code",
            uppercase=True,
        )
        if exchange_code is not None and any(
            character.isspace() for character in exchange_code
        ):
            raise ValueError("exchange_code must not contain whitespace")
        if exchange_code is not None and exchange_ticker is None:
            raise ValueError(
                "exchange_code requires exchange_ticker"
            )

        if (
            instrument_type in {"ETF", "BOND", "GOLD"}
            and isin is None
        ):
            raise ValueError(
                "ETF, BOND, and GOLD instruments must provide an ISIN"
            )

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(
            self,
            "name",
            normalize_required_text(
                self.name,
                field_name="name",
            ),
        )
        object.__setattr__(self, "instrument_type", instrument_type)
        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "isin", isin)
        object.__setattr__(self, "exchange_ticker", exchange_ticker)
        object.__setattr__(self, "exchange_code", exchange_code)

    @property
    def instrument_key(self) -> str:
        """Return the strongest available stable instrument identifier."""
        if self.isin is not None:
            return self.isin
        if (
            self.exchange_code is not None
            and self.exchange_ticker is not None
        ):
            return f"{self.exchange_code}:{self.exchange_ticker}"
        return self.exchange_ticker or self.symbol

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "instrument_type": self.instrument_type,
            "currency": self.currency,
            "isin": self.isin,
            "exchange_ticker": self.exchange_ticker,
            "exchange_code": self.exchange_code,
            "instrument_key": self.instrument_key,
        }
