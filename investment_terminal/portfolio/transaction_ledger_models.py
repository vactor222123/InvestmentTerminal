"""Immutable portfolio transaction-ledger domain contracts."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
)


TRANSACTION_TYPES = (
    "BUY",
    "SELL",
    "DIVIDEND",
    "FEE",
)
TRADE_TRANSACTION_TYPES = ("BUY", "SELL")
CASH_TRANSACTION_TYPES = ("DIVIDEND", "FEE")


@dataclass(frozen=True, slots=True)
class PortfolioTransaction:
    """One immutable economic event in a portfolio lifecycle."""

    transaction_id: str
    transaction_type: str
    occurred_at: datetime
    settlement_currency: str
    instrument: InstrumentIdentity | None = None
    quantity: float | None = None
    unit_price: float | None = None
    cash_amount: float | None = None
    source_reference: str | None = None

    def __post_init__(self) -> None:
        transaction_type = normalize_required_text(
            self.transaction_type,
            field_name="transaction_type",
            uppercase=True,
        )
        if transaction_type not in TRANSACTION_TYPES:
            raise ValueError(
                "transaction_type must be one of: "
                + ", ".join(TRANSACTION_TYPES)
            )
        validate_aware_datetime(self.occurred_at, field_name="occurred_at")
        if self.instrument is not None and not isinstance(
            self.instrument, InstrumentIdentity
        ):
            raise TypeError("instrument must be an InstrumentIdentity or None")

        object.__setattr__(
            self,
            "transaction_id",
            normalize_required_text(
                self.transaction_id,
                field_name="transaction_id",
            ),
        )
        object.__setattr__(self, "transaction_type", transaction_type)
        object.__setattr__(
            self,
            "settlement_currency",
            normalize_required_text(
                self.settlement_currency,
                field_name="settlement_currency",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "source_reference",
            normalize_optional_text(
                self.source_reference,
                field_name="source_reference",
            ),
        )

        if transaction_type in TRADE_TRANSACTION_TYPES:
            self._validate_trade()
        else:
            self._validate_cash_event()

    def _validate_trade(self) -> None:
        if self.instrument is None:
            raise ValueError("trade transactions require an instrument")
        if self.cash_amount is not None:
            raise ValueError("trade transactions must not define cash_amount")
        object.__setattr__(
            self,
            "quantity",
            _positive_number(self.quantity, field_name="quantity"),
        )
        object.__setattr__(
            self,
            "unit_price",
            _non_negative_number(self.unit_price, field_name="unit_price"),
        )

    def _validate_cash_event(self) -> None:
        if self.quantity is not None or self.unit_price is not None:
            raise ValueError(
                "cash transactions must not define quantity or unit_price"
            )
        if self.transaction_type == "DIVIDEND" and self.instrument is None:
            raise ValueError("dividend transactions require an instrument")
        object.__setattr__(
            self,
            "cash_amount",
            _positive_number(self.cash_amount, field_name="cash_amount"),
        )

    @property
    def gross_amount(self) -> float:
        if self.transaction_type in TRADE_TRANSACTION_TYPES:
            assert self.quantity is not None
            assert self.unit_price is not None
            return round(self.quantity * self.unit_price, 8)
        assert self.cash_amount is not None
        return self.cash_amount

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "transaction_type": self.transaction_type,
            "occurred_at": self.occurred_at.isoformat(),
            "settlement_currency": self.settlement_currency,
            "instrument": (
                self.instrument.to_dict()
                if self.instrument is not None
                else None
            ),
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "cash_amount": self.cash_amount,
            "gross_amount": self.gross_amount,
            "source_reference": self.source_reference,
        }


@dataclass(frozen=True, slots=True)
class PortfolioTransactionLedger:
    """Deterministically ordered immutable portfolio transaction sequence."""

    ledger_id: str
    portfolio_name: str
    base_currency: str
    transactions: tuple[PortfolioTransaction, ...]

    def __post_init__(self) -> None:
        for field_name in ("ledger_id", "portfolio_name"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )
        object.__setattr__(
            self,
            "base_currency",
            normalize_required_text(
                self.base_currency,
                field_name="base_currency",
                uppercase=True,
            ),
        )
        if not isinstance(self.transactions, tuple):
            raise TypeError("transactions must be a tuple")
        if any(
            not isinstance(item, PortfolioTransaction)
            for item in self.transactions
        ):
            raise TypeError(
                "transactions must contain only PortfolioTransaction objects"
            )

        transaction_ids = tuple(
            item.transaction_id for item in self.transactions
        )
        if len(transaction_ids) != len(set(transaction_ids)):
            raise ValueError("transactions must contain unique transaction IDs")

        order_keys = tuple(
            (item.occurred_at, item.transaction_id)
            for item in self.transactions
        )
        if order_keys != tuple(sorted(order_keys)):
            raise ValueError(
                "transactions must be ordered by occurred_at and transaction_id"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "portfolio_name": self.portfolio_name,
            "base_currency": self.base_currency,
            "transaction_count": len(self.transactions),
            "transactions": [
                transaction.to_dict()
                for transaction in self.transactions
            ],
        }


def _positive_number(value: object, *, field_name: str) -> float:
    normalized = _non_negative_number(value, field_name=field_name)
    if normalized <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return normalized


def _non_negative_number(value: object, *, field_name: str) -> float:
    normalized = validate_finite_number(value, field_name=field_name)
    if normalized < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return normalized
