"""
Portfolio market-price and market-value models.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from math import isfinite
from numbers import Real
from typing import Any

from investment_terminal.portfolio.current_portfolio_models import (
    CurrentPortfolio,
    PortfolioHolding,
)


def round_money(
    value: Decimal | Real,
) -> float:
    """Round a monetary value to cents using commercial rounding."""
    decimal_value = (
        value
        if isinstance(value, Decimal)
        else Decimal(str(value))
    )

    return float(
        decimal_value.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )


@dataclass(frozen=True, slots=True)
class PortfolioPriceQuote:
    """Latest known market price for one portfolio instrument."""

    instrument_key: str
    exchange_ticker: str
    price: float
    currency: str
    quoted_at: datetime
    source: str

    def __post_init__(self) -> None:
        for field_name in (
            "instrument_key",
            "exchange_ticker",
            "currency",
            "source",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

            object.__setattr__(
                self,
                field_name,
                value.strip(),
            )

        object.__setattr__(
            self,
            "instrument_key",
            self.instrument_key.upper(),
        )
        object.__setattr__(
            self,
            "exchange_ticker",
            self.exchange_ticker.upper(),
        )
        object.__setattr__(
            self,
            "currency",
            self.currency.upper(),
        )

        if (
            isinstance(self.price, bool)
            or not isinstance(self.price, Real)
            or not isfinite(float(self.price))
            or float(self.price) <= 0
        ):
            raise ValueError(
                "price must be a finite number greater than zero"
            )

        if not isinstance(
            self.quoted_at,
            datetime,
        ):
            raise TypeError(
                "quoted_at must be a datetime"
            )

        if self.quoted_at.tzinfo is None:
            raise ValueError(
                "quoted_at must be timezone-aware"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "exchange_ticker": self.exchange_ticker,
            "price": self.price,
            "currency": self.currency,
            "quoted_at": self.quoted_at.isoformat(),
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class PortfolioMarketPosition:
    """One holding enriched with market value and profit/loss."""

    symbol: str
    name: str
    asset_type: str
    sleeve: str
    quantity: float
    average_cost: float
    cost_basis: float
    market_price: float
    market_value: float
    unrealized_profit_loss: float
    unrealized_return: float
    currency: str
    instrument_key: str
    exchange_ticker: str
    quoted_at: datetime
    quote_source: str

    def __post_init__(self) -> None:
        for field_name in (
            "symbol",
            "name",
            "asset_type",
            "sleeve",
            "currency",
            "instrument_key",
            "exchange_ticker",
            "quote_source",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not isinstance(
            self.quoted_at,
            datetime,
        ):
            raise TypeError(
                "quoted_at must be a datetime"
            )

        if self.quoted_at.tzinfo is None:
            raise ValueError(
                "quoted_at must be timezone-aware"
            )

    @classmethod
    def build(
        cls,
        holding: PortfolioHolding,
        quote: PortfolioPriceQuote,
    ) -> "PortfolioMarketPosition":
        if not isinstance(
            holding,
            PortfolioHolding,
        ):
            raise TypeError(
                "holding must be a PortfolioHolding"
            )

        if not isinstance(
            quote,
            PortfolioPriceQuote,
        ):
            raise TypeError(
                "quote must be a PortfolioPriceQuote"
            )

        if (
            holding.instrument_key
            != quote.instrument_key
        ):
            raise ValueError(
                "holding and quote must use the same instrument_key"
            )

        if holding.currency != quote.currency:
            raise ValueError(
                "holding and quote currencies must match until "
                "FX conversion is implemented"
            )

        cost_basis = holding.invested_cost
        market_value = round_money(
            Decimal(str(holding.quantity))
            * Decimal(str(quote.price))
        )
        profit_loss = round_money(
            Decimal(str(market_value))
            - Decimal(str(cost_basis))
        )
        unrealized_return = (
            profit_loss / cost_basis
            if cost_basis > 0
            else 0.0
        )

        return cls(
            symbol=holding.symbol,
            name=holding.name,
            asset_type=holding.asset_type,
            sleeve=holding.sleeve,
            quantity=holding.quantity,
            average_cost=holding.average_cost,
            cost_basis=cost_basis,
            market_price=quote.price,
            market_value=market_value,
            unrealized_profit_loss=profit_loss,
            unrealized_return=round(
                unrealized_return,
                8,
            ),
            currency=quote.currency,
            instrument_key=holding.instrument_key,
            exchange_ticker=quote.exchange_ticker,
            quoted_at=quote.quoted_at,
            quote_source=quote.source,
        )

    @property
    def unrealized_return_percent(self) -> float:
        return round(
            self.unrealized_return * 100.0,
            4,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "asset_type": self.asset_type,
            "sleeve": self.sleeve,
            "quantity": self.quantity,
            "average_cost": self.average_cost,
            "cost_basis": self.cost_basis,
            "market_price": self.market_price,
            "market_value": self.market_value,
            "unrealized_profit_loss": self.unrealized_profit_loss,
            "unrealized_return": self.unrealized_return,
            "unrealized_return_percent": (
                self.unrealized_return_percent
            ),
            "currency": self.currency,
            "instrument_key": self.instrument_key,
            "exchange_ticker": self.exchange_ticker,
            "quoted_at": self.quoted_at.isoformat(),
            "quote_source": self.quote_source,
        }


@dataclass(frozen=True, slots=True)
class PortfolioMarketValueResult:
    """Market-value summary for the entire current portfolio."""

    portfolio_name: str
    base_currency: str
    generated_at: datetime
    positions: tuple[PortfolioMarketPosition, ...]
    cash_value: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.portfolio_name, str)
            or not self.portfolio_name.strip()
        ):
            raise ValueError(
                "portfolio_name must be a non-empty string"
            )

        if (
            not isinstance(self.base_currency, str)
            or not self.base_currency.strip()
        ):
            raise ValueError(
                "base_currency must be a non-empty string"
            )

        if not isinstance(
            self.generated_at,
            datetime,
        ):
            raise TypeError(
                "generated_at must be a datetime"
            )

        if self.generated_at.tzinfo is None:
            raise ValueError(
                "generated_at must be timezone-aware"
            )

        if not isinstance(
            self.positions,
            tuple,
        ):
            raise TypeError(
                "positions must be a tuple"
            )

        if any(
            not isinstance(
                position,
                PortfolioMarketPosition,
            )
            for position in self.positions
        ):
            raise TypeError(
                "positions must contain only "
                "PortfolioMarketPosition objects"
            )

        keys = tuple(
            position.instrument_key
            for position in self.positions
        )

        if len(keys) != len(set(keys)):
            raise ValueError(
                "positions must contain unique instruments"
            )

        if (
            isinstance(self.cash_value, bool)
            or not isinstance(self.cash_value, Real)
            or not isfinite(float(self.cash_value))
            or float(self.cash_value) < 0
        ):
            raise ValueError(
                "cash_value must be a finite non-negative number"
            )

    @property
    def invested_market_value(self) -> float:
        return round_money(
            sum(
                Decimal(str(position.market_value))
                for position in self.positions
            )
        )

    @property
    def invested_cost_basis(self) -> float:
        return round_money(
            sum(
                Decimal(str(position.cost_basis))
                for position in self.positions
            )
        )

    @property
    def total_market_value(self) -> float:
        return round_money(
            Decimal(str(self.invested_market_value))
            + Decimal(str(self.cash_value))
        )

    @property
    def unrealized_profit_loss(self) -> float:
        return round_money(
            Decimal(str(self.invested_market_value))
            - Decimal(str(self.invested_cost_basis))
        )

    @property
    def unrealized_return(self) -> float:
        if self.invested_cost_basis == 0:
            return 0.0

        return round(
            self.unrealized_profit_loss
            / self.invested_cost_basis,
            8,
        )

    @property
    def unrealized_return_percent(self) -> float:
        return round(
            self.unrealized_return * 100.0,
            4,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_name": self.portfolio_name,
            "base_currency": self.base_currency,
            "generated_at": self.generated_at.isoformat(),
            "invested_market_value": self.invested_market_value,
            "invested_cost_basis": self.invested_cost_basis,
            "cash_value": self.cash_value,
            "total_market_value": self.total_market_value,
            "unrealized_profit_loss": self.unrealized_profit_loss,
            "unrealized_return": self.unrealized_return,
            "unrealized_return_percent": (
                self.unrealized_return_percent
            ),
            "positions": [
                position.to_dict()
                for position in self.positions
            ],
        }