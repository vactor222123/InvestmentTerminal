"""Deterministic open-position reconstruction from portfolio trades."""

from dataclasses import dataclass
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
    validate_finite_number,
)


@dataclass(frozen=True, slots=True)
class ReconstructedPosition:
    """One open position reconstructed with average-cost accounting."""

    instrument: InstrumentIdentity
    quantity: float
    cost_basis: float
    average_cost: float
    cost_currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, InstrumentIdentity):
            raise TypeError("instrument must be an InstrumentIdentity")
        for field_name in ("quantity", "cost_basis", "average_cost"):
            value = validate_finite_number(
                getattr(self, field_name),
                field_name=field_name,
            )
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative")
            object.__setattr__(self, field_name, value)
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        object.__setattr__(
            self,
            "cost_currency",
            normalize_required_text(
                self.cost_currency,
                field_name="cost_currency",
                uppercase=True,
            ),
        )

    @property
    def instrument_key(self) -> str:
        return self.instrument.instrument_key

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "quantity": self.quantity,
            "cost_basis": self.cost_basis,
            "average_cost": self.average_cost,
            "cost_currency": self.cost_currency,
        }


@dataclass(frozen=True, slots=True)
class PositionReconstruction:
    """Immutable deterministic projection of all currently open positions."""

    ledger_id: str
    portfolio_name: str
    processed_trade_count: int
    positions: tuple[ReconstructedPosition, ...]

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
        if not isinstance(self.processed_trade_count, int):
            raise TypeError("processed_trade_count must be an integer")
        if self.processed_trade_count < 0:
            raise ValueError("processed_trade_count must be non-negative")
        if not isinstance(self.positions, tuple):
            raise TypeError("positions must be a tuple")
        if any(not isinstance(item, ReconstructedPosition) for item in self.positions):
            raise TypeError("positions must contain only ReconstructedPosition objects")
        keys = tuple(item.instrument_key for item in self.positions)
        if keys != tuple(sorted(keys)):
            raise ValueError("positions must be ordered by instrument_key")
        if len(keys) != len(set(keys)):
            raise ValueError("positions must contain unique instruments")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "portfolio_name": self.portfolio_name,
            "processed_trade_count": self.processed_trade_count,
            "position_count": len(self.positions),
            "positions": [position.to_dict() for position in self.positions],
        }


@dataclass(slots=True)
class _PositionState:
    instrument: InstrumentIdentity
    cost_currency: str
    quantity: Decimal
    cost_basis: Decimal


class PositionReconstructor:
    """Project a validated transaction ledger into average-cost positions."""

    @classmethod
    def reconstruct(
        cls,
        ledger: PortfolioTransactionLedger,
    ) -> PositionReconstruction:
        if not isinstance(ledger, PortfolioTransactionLedger):
            raise TypeError("ledger must be a PortfolioTransactionLedger")

        states: dict[str, _PositionState] = {}
        known_instruments: dict[str, InstrumentIdentity] = {}
        processed_trade_count = 0
        for transaction in ledger.transactions:
            if transaction.transaction_type not in {"BUY", "SELL"}:
                continue
            processed_trade_count += 1
            assert transaction.instrument is not None
            assert transaction.quantity is not None
            assert transaction.unit_price is not None
            instrument_key = transaction.instrument.instrument_key
            known_instrument = known_instruments.get(instrument_key)
            if (
                known_instrument is not None
                and transaction.instrument != known_instrument
            ):
                raise ValueError(f"instrument identity changed for {instrument_key}")
            known_instruments[instrument_key] = transaction.instrument
            quantity = Decimal(str(transaction.quantity))
            unit_price = Decimal(str(transaction.unit_price))
            state = states.get(instrument_key)

            if state is None:
                if transaction.transaction_type == "SELL":
                    raise ValueError(
                        "SELL transaction "
                        f"{transaction.transaction_id} exceeds available quantity "
                        f"for {instrument_key}"
                    )
                states[instrument_key] = _PositionState(
                    instrument=transaction.instrument,
                    cost_currency=transaction.settlement_currency,
                    quantity=quantity,
                    cost_basis=quantity * unit_price,
                )
                continue

            cls._validate_consistent_trade(state, transaction)
            if transaction.transaction_type == "BUY":
                state.quantity += quantity
                state.cost_basis += quantity * unit_price
                continue

            if quantity > state.quantity:
                raise ValueError(
                    "SELL transaction "
                    f"{transaction.transaction_id} exceeds available quantity "
                    f"for {instrument_key}"
                )
            average_cost = state.cost_basis / state.quantity
            state.quantity -= quantity
            state.cost_basis -= average_cost * quantity
            if state.quantity == 0:
                del states[instrument_key]

        positions = tuple(cls._to_position(states[key]) for key in sorted(states))
        return PositionReconstruction(
            ledger_id=ledger.ledger_id,
            portfolio_name=ledger.portfolio_name,
            processed_trade_count=processed_trade_count,
            positions=positions,
        )

    @staticmethod
    def _validate_consistent_trade(
        state: _PositionState,
        transaction: PortfolioTransaction,
    ) -> None:
        assert transaction.instrument is not None
        if transaction.instrument != state.instrument:
            raise ValueError(
                f"instrument identity changed for {state.instrument.instrument_key}"
            )
        if transaction.settlement_currency != state.cost_currency:
            raise ValueError(
                f"settlement currency changed for {state.instrument.instrument_key}"
            )

    @staticmethod
    def _to_position(state: _PositionState) -> ReconstructedPosition:
        average_cost = state.cost_basis / state.quantity
        return ReconstructedPosition(
            instrument=state.instrument,
            quantity=float(state.quantity),
            cost_basis=float(state.cost_basis),
            average_cost=float(average_cost),
            cost_currency=state.cost_currency,
        )
