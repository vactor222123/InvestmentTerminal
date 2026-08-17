"""Unrealised performance projection for transaction-derived positions."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.portfolio.portfolio_market_value_models import (
    PortfolioPriceQuote,
)
from investment_terminal.portfolio.portfolio_price_provider import (
    PortfolioPriceProvider,
)
from investment_terminal.portfolio.position_reconstruction import (
    PositionReconstruction,
    ReconstructedPosition,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
)


@dataclass(frozen=True, slots=True)
class UnrealizedPositionPerformance:
    """One open position valued by one explicit market quote."""

    instrument: InstrumentIdentity
    quantity: float
    average_cost: float
    cost_basis: float
    market_price: float
    market_value: float
    unrealized_gain_loss: float
    currency: str
    unrealized_return_percent: float | None
    quoted_at: datetime
    quote_source: str

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, InstrumentIdentity):
            raise TypeError("instrument must be an InstrumentIdentity")
        for field_name in (
            "quantity",
            "average_cost",
            "cost_basis",
            "market_price",
            "market_value",
            "unrealized_gain_loss",
        ):
            object.__setattr__(
                self,
                field_name,
                validate_finite_number(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        for field_name in (
            "average_cost",
            "cost_basis",
            "market_price",
            "market_value",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be non-negative")
        if self.unrealized_return_percent is not None:
            object.__setattr__(
                self,
                "unrealized_return_percent",
                validate_finite_number(
                    self.unrealized_return_percent,
                    field_name="unrealized_return_percent",
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
        validate_aware_datetime(self.quoted_at, field_name="quoted_at")
        object.__setattr__(
            self,
            "quote_source",
            normalize_required_text(
                self.quote_source,
                field_name="quote_source",
            ),
        )

    @property
    def instrument_key(self) -> str:
        return self.instrument.instrument_key

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "quantity": self.quantity,
            "average_cost": self.average_cost,
            "cost_basis": self.cost_basis,
            "market_price": self.market_price,
            "market_value": self.market_value,
            "unrealized_gain_loss": self.unrealized_gain_loss,
            "currency": self.currency,
            "unrealized_return_percent": self.unrealized_return_percent,
            "quoted_at": self.quoted_at.isoformat(),
            "quote_source": self.quote_source,
        }


@dataclass(frozen=True, slots=True)
class UnrealizedCurrencySummary:
    """Unrealised totals that are safe to aggregate in one currency."""

    currency: str
    cost_basis: float
    market_value: float
    unrealized_gain_loss: float
    unrealized_return_percent: float | None

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
            "cost_basis",
            "market_value",
            "unrealized_gain_loss",
        ):
            object.__setattr__(
                self,
                field_name,
                validate_finite_number(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )
        if self.cost_basis < 0:
            raise ValueError("cost_basis must be non-negative")
        if self.market_value < 0:
            raise ValueError("market_value must be non-negative")
        if self.unrealized_return_percent is not None:
            object.__setattr__(
                self,
                "unrealized_return_percent",
                validate_finite_number(
                    self.unrealized_return_percent,
                    field_name="unrealized_return_percent",
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "currency": self.currency,
            "cost_basis": self.cost_basis,
            "market_value": self.market_value,
            "unrealized_gain_loss": self.unrealized_gain_loss,
            "unrealized_return_percent": self.unrealized_return_percent,
        }


@dataclass(frozen=True, slots=True)
class UnrealizedPerformance:
    """Immutable valuation with quote-level provenance and currency-safe totals."""

    ledger_id: str
    portfolio_name: str
    valued_at: datetime
    positions: tuple[UnrealizedPositionPerformance, ...]
    currency_summaries: tuple[UnrealizedCurrencySummary, ...]

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
        validate_aware_datetime(self.valued_at, field_name="valued_at")
        if not isinstance(self.positions, tuple):
            raise TypeError("positions must be a tuple")
        if any(
            not isinstance(item, UnrealizedPositionPerformance)
            for item in self.positions
        ):
            raise TypeError(
                "positions must contain only UnrealizedPositionPerformance objects"
            )
        keys = tuple(item.instrument_key for item in self.positions)
        if keys != tuple(sorted(keys)):
            raise ValueError("positions must be ordered by instrument_key")
        if len(keys) != len(set(keys)):
            raise ValueError("positions must contain unique instruments")
        if not isinstance(self.currency_summaries, tuple):
            raise TypeError("currency_summaries must be a tuple")
        if any(
            not isinstance(item, UnrealizedCurrencySummary)
            for item in self.currency_summaries
        ):
            raise TypeError(
                "currency_summaries must contain only UnrealizedCurrencySummary objects"
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
            "valued_at": self.valued_at.isoformat(),
            "position_count": len(self.positions),
            "positions": [position.to_dict() for position in self.positions],
            "currency_summaries": [
                summary.to_dict() for summary in self.currency_summaries
            ],
        }


class UnrealizedPerformanceCalculator:
    """Value reconstructed positions through the existing quote boundary."""

    def __init__(self, price_provider: PortfolioPriceProvider) -> None:
        if not callable(getattr(price_provider, "get_quote", None)):
            raise TypeError("price_provider must provide get_quote")
        self.price_provider = price_provider

    def calculate(
        self,
        reconstruction: PositionReconstruction,
        *,
        valued_at: datetime,
    ) -> UnrealizedPerformance:
        if not isinstance(reconstruction, PositionReconstruction):
            raise TypeError("reconstruction must be a PositionReconstruction")
        valuation_time = validate_aware_datetime(valued_at, field_name="valued_at")
        positions = tuple(
            self._value_position(position, valued_at=valuation_time)
            for position in reconstruction.positions
        )
        return UnrealizedPerformance(
            ledger_id=reconstruction.ledger_id,
            portfolio_name=reconstruction.portfolio_name,
            valued_at=valuation_time,
            positions=positions,
            currency_summaries=self._summaries(positions),
        )

    def _value_position(
        self,
        position: ReconstructedPosition,
        *,
        valued_at: datetime,
    ) -> UnrealizedPositionPerformance:
        exchange_ticker = position.instrument.exchange_ticker
        if exchange_ticker is None:
            raise ValueError(
                f"{position.instrument_key} has no exchange_ticker "
                "for market-price lookup"
            )
        quote = self.price_provider.get_quote(
            instrument_key=position.instrument_key,
            exchange_ticker=exchange_ticker,
        )
        self._validate_quote(position, quote, valued_at=valued_at)
        quantity = Decimal(str(position.quantity))
        cost_basis = Decimal(str(position.cost_basis))
        market_value = quantity * Decimal(str(quote.price))
        gain_loss = market_value - cost_basis
        return_percent = (
            None if cost_basis == 0 else gain_loss / cost_basis * Decimal("100")
        )
        return UnrealizedPositionPerformance(
            instrument=position.instrument,
            quantity=position.quantity,
            average_cost=position.average_cost,
            cost_basis=position.cost_basis,
            market_price=quote.price,
            market_value=float(market_value),
            unrealized_gain_loss=float(gain_loss),
            currency=quote.currency,
            unrealized_return_percent=(
                None if return_percent is None else float(return_percent)
            ),
            quoted_at=quote.quoted_at,
            quote_source=quote.source,
        )

    @staticmethod
    def _validate_quote(
        position: ReconstructedPosition,
        quote: PortfolioPriceQuote,
        *,
        valued_at: datetime,
    ) -> None:
        if not isinstance(quote, PortfolioPriceQuote):
            raise TypeError("price provider must return a PortfolioPriceQuote")
        if quote.instrument_key != position.instrument_key:
            raise ValueError("position and quote must use the same instrument_key")
        if quote.exchange_ticker != position.instrument.exchange_ticker:
            raise ValueError("position and quote must use the same exchange_ticker")
        if quote.currency != position.cost_currency:
            raise ValueError(
                "position cost currency and quote currency must match until "
                "FX conversion is implemented"
            )
        if quote.quoted_at > valued_at:
            raise ValueError("quote must not be later than valued_at")

    @staticmethod
    def _summaries(
        positions: tuple[UnrealizedPositionPerformance, ...],
    ) -> tuple[UnrealizedCurrencySummary, ...]:
        totals: dict[str, tuple[Decimal, Decimal]] = {}
        for position in positions:
            cost_basis, market_value = totals.get(
                position.currency,
                (Decimal("0"), Decimal("0")),
            )
            totals[position.currency] = (
                cost_basis + Decimal(str(position.cost_basis)),
                market_value + Decimal(str(position.market_value)),
            )
        return tuple(
            UnrealizedPerformanceCalculator._build_summary(
                currency,
                *totals[currency],
            )
            for currency in sorted(totals)
        )

    @staticmethod
    def _build_summary(
        currency: str,
        cost_basis: Decimal,
        market_value: Decimal,
    ) -> UnrealizedCurrencySummary:
        gain_loss = market_value - cost_basis
        return_percent = (
            None if cost_basis == 0 else gain_loss / cost_basis * Decimal("100")
        )
        return UnrealizedCurrencySummary(
            currency=currency,
            cost_basis=float(cost_basis),
            market_value=float(market_value),
            unrealized_gain_loss=float(gain_loss),
            unrealized_return_percent=(
                None if return_percent is None else float(return_percent)
            ),
        )
