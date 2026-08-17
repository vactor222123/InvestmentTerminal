"""Immutable valuation-history contracts for transaction-derived performance."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from investment_terminal.portfolio.realized_performance import (
    RealizedCurrencySummary,
    RealizedPerformance,
)
from investment_terminal.portfolio.unrealized_performance import (
    UnrealizedCurrencySummary,
    UnrealizedPerformance,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_finite_number,
)


@dataclass(frozen=True, slots=True)
class PortfolioValuationCurrencySnapshot:
    """One currency-safe row inside a portfolio valuation snapshot."""

    currency: str
    open_cost_basis: float
    market_value: float
    unrealized_gain_loss: float
    realized_proceeds: float
    realized_cost_basis: float
    realized_gain_loss: float
    combined_gain_loss: float

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
            "open_cost_basis",
            "market_value",
            "unrealized_gain_loss",
            "realized_proceeds",
            "realized_cost_basis",
            "realized_gain_loss",
            "combined_gain_loss",
        ):
            object.__setattr__(
                self,
                field_name,
                validate_finite_number(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )
        for field_name in (
            "open_cost_basis",
            "market_value",
            "realized_proceeds",
            "realized_cost_basis",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be non-negative")
        expected_combined = Decimal(str(self.unrealized_gain_loss)) + Decimal(
            str(self.realized_gain_loss)
        )
        if Decimal(str(self.combined_gain_loss)) != expected_combined:
            raise ValueError(
                "combined_gain_loss must equal realised plus unrealised gain/loss"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "currency": self.currency,
            "open_cost_basis": self.open_cost_basis,
            "market_value": self.market_value,
            "unrealized_gain_loss": self.unrealized_gain_loss,
            "realized_proceeds": self.realized_proceeds,
            "realized_cost_basis": self.realized_cost_basis,
            "realized_gain_loss": self.realized_gain_loss,
            "combined_gain_loss": self.combined_gain_loss,
        }


@dataclass(frozen=True, slots=True)
class PortfolioValuationSnapshot:
    """One immutable realised/unrealised valuation evidence snapshot."""

    snapshot_id: str
    unrealized: UnrealizedPerformance
    realized: RealizedPerformance
    currency_values: tuple[PortfolioValuationCurrencySnapshot, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            normalize_required_text(
                self.snapshot_id,
                field_name="snapshot_id",
            ),
        )
        if not isinstance(self.unrealized, UnrealizedPerformance):
            raise TypeError("unrealized must be an UnrealizedPerformance")
        if not isinstance(self.realized, RealizedPerformance):
            raise TypeError("realized must be a RealizedPerformance")
        if self.unrealized.ledger_id != self.realized.ledger_id:
            raise ValueError("performance projections must use the same ledger_id")
        if self.unrealized.portfolio_name != self.realized.portfolio_name:
            raise ValueError("performance projections must use the same portfolio_name")
        if any(
            sale.occurred_at > self.unrealized.valued_at for sale in self.realized.sales
        ):
            raise ValueError("realized sales must not be later than valued_at")
        if not isinstance(self.currency_values, tuple):
            raise TypeError("currency_values must be a tuple")
        if any(
            not isinstance(item, PortfolioValuationCurrencySnapshot)
            for item in self.currency_values
        ):
            raise TypeError(
                "currency_values must contain only "
                "PortfolioValuationCurrencySnapshot objects"
            )
        currencies = tuple(item.currency for item in self.currency_values)
        if currencies != tuple(sorted(currencies)):
            raise ValueError("currency_values must be ordered by currency")
        if len(currencies) != len(set(currencies)):
            raise ValueError("currency_values must contain unique currencies")
        unrealized_by_currency = {
            item.currency: item for item in self.unrealized.currency_summaries
        }
        realized_by_currency = {
            item.currency: item for item in self.realized.currency_summaries
        }
        expected_currencies = sorted(
            set(unrealized_by_currency) | set(realized_by_currency)
        )
        expected_values = tuple(
            self._build_currency_value(
                currency,
                unrealized_by_currency.get(currency),
                realized_by_currency.get(currency),
            )
            for currency in expected_currencies
        )
        if self.currency_values != expected_values:
            raise ValueError("currency_values must match the performance projections")

    @property
    def ledger_id(self) -> str:
        return self.unrealized.ledger_id

    @property
    def portfolio_name(self) -> str:
        return self.unrealized.portfolio_name

    @property
    def valued_at(self) -> datetime:
        return self.unrealized.valued_at

    @classmethod
    def build(
        cls,
        *,
        snapshot_id: str,
        unrealized: UnrealizedPerformance,
        realized: RealizedPerformance,
    ) -> "PortfolioValuationSnapshot":
        if not isinstance(unrealized, UnrealizedPerformance):
            raise TypeError("unrealized must be an UnrealizedPerformance")
        if not isinstance(realized, RealizedPerformance):
            raise TypeError("realized must be a RealizedPerformance")
        unrealized_by_currency = {
            item.currency: item for item in unrealized.currency_summaries
        }
        realized_by_currency = {
            item.currency: item for item in realized.currency_summaries
        }
        currencies = sorted(set(unrealized_by_currency) | set(realized_by_currency))
        currency_values = tuple(
            cls._build_currency_value(
                currency,
                unrealized_by_currency.get(currency),
                realized_by_currency.get(currency),
            )
            for currency in currencies
        )
        return cls(
            snapshot_id=snapshot_id,
            unrealized=unrealized,
            realized=realized,
            currency_values=currency_values,
        )

    @staticmethod
    def _build_currency_value(
        currency: str,
        unrealized: UnrealizedCurrencySummary | None,
        realized: RealizedCurrencySummary | None,
    ) -> PortfolioValuationCurrencySnapshot:
        unrealized_gain = Decimal(
            str(unrealized.unrealized_gain_loss if unrealized else 0)
        )
        realized_gain = Decimal(str(realized.realized_gain_loss if realized else 0))
        return PortfolioValuationCurrencySnapshot(
            currency=currency,
            open_cost_basis=(unrealized.cost_basis if unrealized else 0.0),
            market_value=(unrealized.market_value if unrealized else 0.0),
            unrealized_gain_loss=float(unrealized_gain),
            realized_proceeds=(realized.proceeds if realized else 0.0),
            realized_cost_basis=(realized.allocated_cost_basis if realized else 0.0),
            realized_gain_loss=float(realized_gain),
            combined_gain_loss=float(unrealized_gain + realized_gain),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "ledger_id": self.ledger_id,
            "portfolio_name": self.portfolio_name,
            "valued_at": self.valued_at.isoformat(),
            "currency_values": [item.to_dict() for item in self.currency_values],
            "unrealized": self.unrealized.to_dict(),
            "realized": self.realized.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class PortfolioValuationHistory:
    """Deterministically ordered immutable valuation-snapshot sequence."""

    ledger_id: str
    portfolio_name: str
    snapshots: tuple[PortfolioValuationSnapshot, ...]

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
        if not isinstance(self.snapshots, tuple):
            raise TypeError("snapshots must be a tuple")
        if any(
            not isinstance(item, PortfolioValuationSnapshot) for item in self.snapshots
        ):
            raise TypeError(
                "snapshots must contain only PortfolioValuationSnapshot objects"
            )
        if any(item.ledger_id != self.ledger_id for item in self.snapshots):
            raise ValueError("snapshots must use the history ledger_id")
        if any(item.portfolio_name != self.portfolio_name for item in self.snapshots):
            raise ValueError("snapshots must use the history portfolio_name")
        identities = tuple(item.snapshot_id for item in self.snapshots)
        if len(identities) != len(set(identities)):
            raise ValueError("snapshots must contain unique snapshot IDs")
        order_keys = tuple(
            (item.valued_at, item.snapshot_id) for item in self.snapshots
        )
        if order_keys != tuple(sorted(order_keys)):
            raise ValueError("snapshots must be ordered by valued_at and snapshot_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "portfolio_name": self.portfolio_name,
            "snapshot_count": len(self.snapshots),
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
        }
