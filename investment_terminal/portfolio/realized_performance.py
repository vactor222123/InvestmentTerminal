"""Deterministic realised performance from portfolio SELL transactions."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.portfolio.transaction_ledger_models import (
    PortfolioTransaction,
    PortfolioTransactionLedger,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
)


@dataclass(frozen=True, slots=True)
class RealizedSale:
    """Average-cost result attributable to one immutable SELL transaction."""

    sell_transaction_id: str
    occurred_at: datetime
    instrument: InstrumentIdentity
    quantity: float
    proceeds: float
    allocated_cost_basis: float
    realized_gain_loss: float
    currency: str
    realized_return_percent: float | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "sell_transaction_id",
            normalize_required_text(
                self.sell_transaction_id,
                field_name="sell_transaction_id",
            ),
        )
        validate_aware_datetime(self.occurred_at, field_name="occurred_at")
        if not isinstance(self.instrument, InstrumentIdentity):
            raise TypeError("instrument must be an InstrumentIdentity")
        for field_name in (
            "quantity",
            "proceeds",
            "allocated_cost_basis",
            "realized_gain_loss",
        ):
            value = validate_finite_number(
                getattr(self, field_name),
                field_name=field_name,
            )
            object.__setattr__(self, field_name, value)
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        if self.proceeds < 0:
            raise ValueError("proceeds must be non-negative")
        if self.allocated_cost_basis < 0:
            raise ValueError("allocated_cost_basis must be non-negative")
        if self.realized_return_percent is not None:
            object.__setattr__(
                self,
                "realized_return_percent",
                validate_finite_number(
                    self.realized_return_percent,
                    field_name="realized_return_percent",
                ),
            )
        object.__setattr__(
            self,
            "currency",
            normalize_required_text(
                self.currency,
                field_name="currency",
                uppercase=True,
            ),
        )

    @property
    def instrument_key(self) -> str:
        return self.instrument.instrument_key

    def to_dict(self) -> dict[str, Any]:
        return {
            "sell_transaction_id": self.sell_transaction_id,
            "occurred_at": self.occurred_at.isoformat(),
            "instrument": self.instrument.to_dict(),
            "quantity": self.quantity,
            "proceeds": self.proceeds,
            "allocated_cost_basis": self.allocated_cost_basis,
            "realized_gain_loss": self.realized_gain_loss,
            "currency": self.currency,
            "realized_return_percent": self.realized_return_percent,
        }


@dataclass(frozen=True, slots=True)
class RealizedCurrencySummary:
    """Realised totals that are safe to aggregate in one currency."""

    currency: str
    proceeds: float
    allocated_cost_basis: float
    realized_gain_loss: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "currency",
            normalize_required_text(
                self.currency,
                field_name="currency",
                uppercase=True,
            ),
        )
        for field_name in (
            "proceeds",
            "allocated_cost_basis",
            "realized_gain_loss",
        ):
            object.__setattr__(
                self,
                field_name,
                validate_finite_number(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )
        if self.proceeds < 0:
            raise ValueError("proceeds must be non-negative")
        if self.allocated_cost_basis < 0:
            raise ValueError("allocated_cost_basis must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "currency": self.currency,
            "proceeds": self.proceeds,
            "allocated_cost_basis": self.allocated_cost_basis,
            "realized_gain_loss": self.realized_gain_loss,
        }


@dataclass(frozen=True, slots=True)
class RealizedPerformance:
    """Immutable sale-level and currency-safe realised performance projection."""

    ledger_id: str
    portfolio_name: str
    sales: tuple[RealizedSale, ...]
    currency_summaries: tuple[RealizedCurrencySummary, ...]

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
        if not isinstance(self.sales, tuple):
            raise TypeError("sales must be a tuple")
        if any(not isinstance(item, RealizedSale) for item in self.sales):
            raise TypeError("sales must contain only RealizedSale objects")
        sale_keys = tuple(
            (item.occurred_at, item.sell_transaction_id) for item in self.sales
        )
        if sale_keys != tuple(sorted(sale_keys)):
            raise ValueError("sales must be ordered by occurrence and identity")
        if not isinstance(self.currency_summaries, tuple):
            raise TypeError("currency_summaries must be a tuple")
        if any(
            not isinstance(item, RealizedCurrencySummary)
            for item in self.currency_summaries
        ):
            raise TypeError(
                "currency_summaries must contain only RealizedCurrencySummary objects"
            )
        currencies = tuple(item.currency for item in self.currency_summaries)
        if currencies != tuple(sorted(currencies)):
            raise ValueError("currency_summaries must be ordered by currency")
        if len(currencies) != len(set(currencies)):
            raise ValueError("currency_summaries must contain unique currencies")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "portfolio_name": self.portfolio_name,
            "sale_count": len(self.sales),
            "sales": [sale.to_dict() for sale in self.sales],
            "currency_summaries": [
                summary.to_dict() for summary in self.currency_summaries
            ],
        }


@dataclass(slots=True)
class _CostState:
    instrument: InstrumentIdentity
    currency: str
    quantity: Decimal
    cost_basis: Decimal


class RealizedPerformanceCalculator:
    """Calculate average-cost realised results without mutating the ledger."""

    @classmethod
    def calculate(
        cls,
        ledger: PortfolioTransactionLedger,
    ) -> RealizedPerformance:
        if not isinstance(ledger, PortfolioTransactionLedger):
            raise TypeError("ledger must be a PortfolioTransactionLedger")

        states: dict[str, _CostState] = {}
        known_instruments: dict[str, InstrumentIdentity] = {}
        sales: list[RealizedSale] = []
        for transaction in ledger.transactions:
            if transaction.transaction_type not in {"BUY", "SELL"}:
                continue
            assert transaction.instrument is not None
            assert transaction.quantity is not None
            assert transaction.unit_price is not None
            instrument_key = transaction.instrument.instrument_key
            cls._validate_identity(
                known_instruments,
                instrument_key,
                transaction.instrument,
            )
            quantity = Decimal(str(transaction.quantity))
            unit_price = Decimal(str(transaction.unit_price))
            state = states.get(instrument_key)

            if state is None:
                if transaction.transaction_type == "SELL":
                    cls._raise_oversell(transaction, instrument_key)
                states[instrument_key] = _CostState(
                    instrument=transaction.instrument,
                    currency=transaction.settlement_currency,
                    quantity=quantity,
                    cost_basis=quantity * unit_price,
                )
                continue

            if transaction.settlement_currency != state.currency:
                raise ValueError(f"settlement currency changed for {instrument_key}")
            if transaction.transaction_type == "BUY":
                state.quantity += quantity
                state.cost_basis += quantity * unit_price
                continue

            if quantity > state.quantity:
                cls._raise_oversell(transaction, instrument_key)
            average_cost = state.cost_basis / state.quantity
            allocated_cost_basis = average_cost * quantity
            proceeds = unit_price * quantity
            realized_gain_loss = proceeds - allocated_cost_basis
            return_percent = (
                None
                if allocated_cost_basis == 0
                else realized_gain_loss / allocated_cost_basis * Decimal("100")
            )
            sales.append(
                RealizedSale(
                    sell_transaction_id=transaction.transaction_id,
                    occurred_at=transaction.occurred_at,
                    instrument=transaction.instrument,
                    quantity=float(quantity),
                    proceeds=float(proceeds),
                    allocated_cost_basis=float(allocated_cost_basis),
                    realized_gain_loss=float(realized_gain_loss),
                    currency=state.currency,
                    realized_return_percent=(
                        None if return_percent is None else float(return_percent)
                    ),
                )
            )
            state.quantity -= quantity
            state.cost_basis -= allocated_cost_basis
            if state.quantity == 0:
                del states[instrument_key]

        return RealizedPerformance(
            ledger_id=ledger.ledger_id,
            portfolio_name=ledger.portfolio_name,
            sales=tuple(sales),
            currency_summaries=cls._summaries(sales),
        )

    @staticmethod
    def _validate_identity(
        known_instruments: dict[str, InstrumentIdentity],
        instrument_key: str,
        instrument: InstrumentIdentity,
    ) -> None:
        known = known_instruments.get(instrument_key)
        if known is not None and instrument != known:
            raise ValueError(f"instrument identity changed for {instrument_key}")
        known_instruments[instrument_key] = instrument

    @staticmethod
    def _raise_oversell(
        transaction: PortfolioTransaction,
        instrument_key: str,
    ) -> None:
        raise ValueError(
            f"SELL transaction {transaction.transaction_id} exceeds "
            f"available quantity for {instrument_key}"
        )

    @staticmethod
    def _summaries(
        sales: list[RealizedSale],
    ) -> tuple[RealizedCurrencySummary, ...]:
        totals: dict[str, tuple[Decimal, Decimal]] = {}
        for sale in sales:
            proceeds, cost_basis = totals.get(
                sale.currency,
                (Decimal("0"), Decimal("0")),
            )
            totals[sale.currency] = (
                proceeds + Decimal(str(sale.proceeds)),
                cost_basis + Decimal(str(sale.allocated_cost_basis)),
            )
        return tuple(
            RealizedCurrencySummary(
                currency=currency,
                proceeds=float(totals[currency][0]),
                allocated_cost_basis=float(totals[currency][1]),
                realized_gain_loss=float(totals[currency][0] - totals[currency][1]),
            )
            for currency in sorted(totals)
        )
