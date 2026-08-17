"""Explicit acquisition-lot attribution for portfolio sales."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.portfolio.transaction_ledger_models import (
    PortfolioTransaction,
    PortfolioTransactionLedger,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
)


def _positive_number(value: object, *, field_name: str) -> float:
    normalized = validate_finite_number(value, field_name=field_name)
    if normalized <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return normalized


def _non_negative_number(value: object, *, field_name: str) -> float:
    normalized = validate_finite_number(value, field_name=field_name)
    if normalized < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return normalized


@dataclass(frozen=True, slots=True)
class TaxLotSelection:
    """One explicit quantity mapping from a sale to an acquisition."""

    sell_transaction_id: str
    acquisition_transaction_id: str
    quantity: float

    def __post_init__(self) -> None:
        for field_name in (
            "sell_transaction_id",
            "acquisition_transaction_id",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name), field_name=field_name
                ),
            )
        object.__setattr__(
            self,
            "quantity",
            _positive_number(self.quantity, field_name="quantity"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sell_transaction_id": self.sell_transaction_id,
            "acquisition_transaction_id": self.acquisition_transaction_id,
            "quantity": self.quantity,
        }


@dataclass(frozen=True, slots=True)
class AcquisitionTaxLot:
    """Remaining quantity and cost evidence from one BUY transaction."""

    acquisition_transaction_id: str
    acquired_at: datetime
    instrument: InstrumentIdentity
    original_quantity: float
    remaining_quantity: float
    unit_cost: float
    currency: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "acquisition_transaction_id",
            normalize_required_text(
                self.acquisition_transaction_id,
                field_name="acquisition_transaction_id",
            ),
        )
        validate_aware_datetime(self.acquired_at, field_name="acquired_at")
        if not isinstance(self.instrument, InstrumentIdentity):
            raise TypeError("instrument must be an InstrumentIdentity")
        object.__setattr__(
            self,
            "original_quantity",
            _positive_number(self.original_quantity, field_name="original_quantity"),
        )
        object.__setattr__(
            self,
            "remaining_quantity",
            _positive_number(self.remaining_quantity, field_name="remaining_quantity"),
        )
        if self.remaining_quantity > self.original_quantity:
            raise ValueError("remaining_quantity must not exceed original_quantity")
        object.__setattr__(
            self,
            "unit_cost",
            _non_negative_number(self.unit_cost, field_name="unit_cost"),
        )
        object.__setattr__(
            self,
            "currency",
            normalize_required_text(
                self.currency, field_name="currency", uppercase=True
            ),
        )

    @property
    def instrument_key(self) -> str:
        return self.instrument.instrument_key

    @property
    def remaining_cost_basis(self) -> float:
        return float(
            Decimal(str(self.remaining_quantity)) * Decimal(str(self.unit_cost))
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "acquisition_transaction_id": self.acquisition_transaction_id,
            "acquired_at": self.acquired_at.isoformat(),
            "instrument": self.instrument.to_dict(),
            "original_quantity": self.original_quantity,
            "remaining_quantity": self.remaining_quantity,
            "unit_cost": self.unit_cost,
            "remaining_cost_basis": self.remaining_cost_basis,
            "currency": self.currency,
        }


@dataclass(frozen=True, slots=True)
class TaxLotAllocation:
    """Cost and proceeds attributable to one sale/acquisition pair."""

    sell_transaction_id: str
    sold_at: datetime
    acquisition_transaction_id: str
    acquired_at: datetime
    instrument: InstrumentIdentity
    quantity: float
    proceeds: float
    allocated_cost_basis: float
    realized_gain_loss: float
    currency: str

    def __post_init__(self) -> None:
        for field_name in (
            "sell_transaction_id",
            "acquisition_transaction_id",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name), field_name=field_name
                ),
            )
        validate_aware_datetime(self.sold_at, field_name="sold_at")
        validate_aware_datetime(self.acquired_at, field_name="acquired_at")
        if self.acquired_at > self.sold_at:
            raise ValueError("acquired_at must not be later than sold_at")
        if not isinstance(self.instrument, InstrumentIdentity):
            raise TypeError("instrument must be an InstrumentIdentity")
        object.__setattr__(
            self, "quantity", _positive_number(self.quantity, field_name="quantity")
        )
        for field_name in ("proceeds", "allocated_cost_basis"):
            object.__setattr__(
                self,
                field_name,
                _non_negative_number(getattr(self, field_name), field_name=field_name),
            )
        object.__setattr__(
            self,
            "realized_gain_loss",
            validate_finite_number(
                self.realized_gain_loss, field_name="realized_gain_loss"
            ),
        )
        expected = Decimal(str(self.proceeds)) - Decimal(str(self.allocated_cost_basis))
        if Decimal(str(self.realized_gain_loss)) != expected:
            raise ValueError(
                "realized_gain_loss must equal proceeds minus allocated_cost_basis"
            )
        object.__setattr__(
            self,
            "currency",
            normalize_required_text(
                self.currency, field_name="currency", uppercase=True
            ),
        )

    @property
    def instrument_key(self) -> str:
        return self.instrument.instrument_key

    def to_dict(self) -> dict[str, Any]:
        return {
            "sell_transaction_id": self.sell_transaction_id,
            "sold_at": self.sold_at.isoformat(),
            "acquisition_transaction_id": self.acquisition_transaction_id,
            "acquired_at": self.acquired_at.isoformat(),
            "instrument": self.instrument.to_dict(),
            "quantity": self.quantity,
            "proceeds": self.proceeds,
            "allocated_cost_basis": self.allocated_cost_basis,
            "realized_gain_loss": self.realized_gain_loss,
            "currency": self.currency,
        }


@dataclass(frozen=True, slots=True)
class TaxLotAttribution:
    """Complete deterministic explicit-lot projection of one ledger."""

    ledger_id: str
    portfolio_name: str
    processed_trade_count: int
    allocations: tuple[TaxLotAllocation, ...]
    open_lots: tuple[AcquisitionTaxLot, ...]

    def __post_init__(self) -> None:
        for field_name in ("ledger_id", "portfolio_name"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name), field_name=field_name
                ),
            )
        if isinstance(self.processed_trade_count, bool) or not isinstance(
            self.processed_trade_count, int
        ):
            raise TypeError("processed_trade_count must be an integer")
        if self.processed_trade_count < 0:
            raise ValueError("processed_trade_count must be non-negative")
        if not isinstance(self.allocations, tuple) or any(
            not isinstance(item, TaxLotAllocation) for item in self.allocations
        ):
            raise TypeError("allocations must contain only TaxLotAllocation objects")
        if not isinstance(self.open_lots, tuple) or any(
            not isinstance(item, AcquisitionTaxLot) for item in self.open_lots
        ):
            raise TypeError("open_lots must contain only AcquisitionTaxLot objects")
        allocation_keys = tuple(
            (
                item.sold_at,
                item.sell_transaction_id,
                item.acquired_at,
                item.acquisition_transaction_id,
            )
            for item in self.allocations
        )
        if allocation_keys != tuple(sorted(allocation_keys)):
            raise ValueError("allocations must be deterministically ordered")
        lot_keys = tuple(
            (
                item.instrument_key,
                item.acquired_at,
                item.acquisition_transaction_id,
            )
            for item in self.open_lots
        )
        if lot_keys != tuple(sorted(lot_keys)):
            raise ValueError("open_lots must be deterministically ordered")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "portfolio_name": self.portfolio_name,
            "processed_trade_count": self.processed_trade_count,
            "allocation_count": len(self.allocations),
            "open_lot_count": len(self.open_lots),
            "allocations": [item.to_dict() for item in self.allocations],
            "open_lots": [item.to_dict() for item in self.open_lots],
        }


class TaxLotAttributor:
    """Validate explicit sale selections and derive lot-level evidence."""

    @classmethod
    def attribute(
        cls,
        ledger: PortfolioTransactionLedger,
        selections: tuple[TaxLotSelection, ...],
    ) -> TaxLotAttribution:
        if not isinstance(ledger, PortfolioTransactionLedger):
            raise TypeError("ledger must be a PortfolioTransactionLedger")
        if not isinstance(selections, tuple):
            raise TypeError("selections must be a tuple")
        if any(not isinstance(item, TaxLotSelection) for item in selections):
            raise TypeError("selections must contain only TaxLotSelection objects")
        selection_keys = tuple(
            (item.sell_transaction_id, item.acquisition_transaction_id)
            for item in selections
        )
        if len(selection_keys) != len(set(selection_keys)):
            raise ValueError("selections must contain unique sale/acquisition pairs")

        trades = {
            item.transaction_id: item
            for item in ledger.transactions
            if item.transaction_type in {"BUY", "SELL"}
        }
        buys = {
            key: item for key, item in trades.items() if item.transaction_type == "BUY"
        }
        sells = {
            key: item for key, item in trades.items() if item.transaction_type == "SELL"
        }
        by_sale: dict[str, list[TaxLotSelection]] = {}
        allocated_by_buy: dict[str, Decimal] = {}
        for selection in selections:
            sale = cls._require_trade(
                sells, selection.sell_transaction_id, expected_type="SELL"
            )
            buy = cls._require_trade(
                buys, selection.acquisition_transaction_id, expected_type="BUY"
            )
            cls._validate_pair(buy, sale)
            by_sale.setdefault(sale.transaction_id, []).append(selection)
            allocated_by_buy[buy.transaction_id] = allocated_by_buy.get(
                buy.transaction_id, Decimal("0")
            ) + Decimal(str(selection.quantity))

        for sale in sells.values():
            assert sale.quantity is not None
            selected = sum(
                (
                    Decimal(str(item.quantity))
                    for item in by_sale.get(sale.transaction_id, [])
                ),
                Decimal("0"),
            )
            if selected != Decimal(str(sale.quantity)):
                raise ValueError(
                    f"SELL transaction {sale.transaction_id} must be attributed exactly"
                )
        for buy_id, quantity in allocated_by_buy.items():
            buy = buys[buy_id]
            assert buy.quantity is not None
            if quantity > Decimal(str(buy.quantity)):
                raise ValueError(
                    f"acquisition {buy_id} allocation exceeds available quantity"
                )

        allocations = tuple(
            sorted(
                (cls._allocation(selection, buys, sells) for selection in selections),
                key=lambda item: (
                    item.sold_at,
                    item.sell_transaction_id,
                    item.acquired_at,
                    item.acquisition_transaction_id,
                ),
            )
        )
        open_lots = tuple(
            sorted(
                (
                    cls._open_lot(buy, allocated_by_buy.get(buy_id, Decimal("0")))
                    for buy_id, buy in buys.items()
                    if allocated_by_buy.get(buy_id, Decimal("0"))
                    < Decimal(str(buy.quantity))
                ),
                key=lambda item: (
                    item.instrument_key,
                    item.acquired_at,
                    item.acquisition_transaction_id,
                ),
            )
        )
        return TaxLotAttribution(
            ledger_id=ledger.ledger_id,
            portfolio_name=ledger.portfolio_name,
            processed_trade_count=len(trades),
            allocations=allocations,
            open_lots=open_lots,
        )

    @staticmethod
    def _require_trade(
        trades: dict[str, PortfolioTransaction],
        transaction_id: str,
        *,
        expected_type: str,
    ) -> PortfolioTransaction:
        transaction = trades.get(transaction_id)
        if transaction is None:
            raise ValueError(
                f"{expected_type} transaction {transaction_id} does not exist"
            )
        return transaction

    @staticmethod
    def _validate_pair(buy: PortfolioTransaction, sale: PortfolioTransaction) -> None:
        assert buy.instrument is not None
        assert sale.instrument is not None
        if buy.occurred_at > sale.occurred_at:
            raise ValueError("acquisition must not be later than sale")
        if buy.instrument != sale.instrument:
            raise ValueError("acquisition and sale must use the same instrument")
        if buy.settlement_currency != sale.settlement_currency:
            raise ValueError("acquisition and sale must use the same currency")

    @staticmethod
    def _allocation(
        selection: TaxLotSelection,
        buys: dict[str, PortfolioTransaction],
        sells: dict[str, PortfolioTransaction],
    ) -> TaxLotAllocation:
        buy = buys[selection.acquisition_transaction_id]
        sale = sells[selection.sell_transaction_id]
        assert buy.instrument is not None
        assert buy.unit_price is not None
        assert sale.unit_price is not None
        quantity = Decimal(str(selection.quantity))
        proceeds = quantity * Decimal(str(sale.unit_price))
        cost_basis = quantity * Decimal(str(buy.unit_price))
        return TaxLotAllocation(
            sell_transaction_id=sale.transaction_id,
            sold_at=sale.occurred_at,
            acquisition_transaction_id=buy.transaction_id,
            acquired_at=buy.occurred_at,
            instrument=buy.instrument,
            quantity=float(quantity),
            proceeds=float(proceeds),
            allocated_cost_basis=float(cost_basis),
            realized_gain_loss=float(proceeds - cost_basis),
            currency=buy.settlement_currency,
        )

    @staticmethod
    def _open_lot(
        buy: PortfolioTransaction, allocated_quantity: Decimal
    ) -> AcquisitionTaxLot:
        assert buy.instrument is not None
        assert buy.quantity is not None
        assert buy.unit_price is not None
        original = Decimal(str(buy.quantity))
        return AcquisitionTaxLot(
            acquisition_transaction_id=buy.transaction_id,
            acquired_at=buy.occurred_at,
            instrument=buy.instrument,
            original_quantity=float(original),
            remaining_quantity=float(original - allocated_quantity),
            unit_cost=buy.unit_price,
            currency=buy.settlement_currency,
        )
