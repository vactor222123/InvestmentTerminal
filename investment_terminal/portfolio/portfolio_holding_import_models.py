"""
Portfolio holding import models.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.portfolio.current_portfolio_models import (
    PortfolioHolding,
)


@dataclass(frozen=True, slots=True)
class PortfolioHoldingImportResult:
    """Validated holdings loaded from an import file."""

    holdings: tuple[PortfolioHolding, ...]
    source_name: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.holdings,
            tuple,
        ):
            raise TypeError(
                "holdings must be a tuple"
            )

        if any(
            not isinstance(
                holding,
                PortfolioHolding,
            )
            for holding in self.holdings
        ):
            raise TypeError(
                "holdings must contain only PortfolioHolding objects"
            )

        if (
            not isinstance(self.source_name, str)
            or not self.source_name.strip()
        ):
            raise ValueError(
                "source_name must be a non-empty string"
            )

        keys = tuple(
            holding.instrument_key
            for holding in self.holdings
        )

        if len(keys) != len(set(keys)):
            raise ValueError(
                "imported holdings must contain unique instruments"
            )

        object.__setattr__(
            self,
            "source_name",
            self.source_name.strip(),
        )

    @property
    def count(self) -> int:
        return len(self.holdings)

    @property
    def total_cost(self) -> float:
        return round(
            sum(
                holding.invested_cost
                for holding in self.holdings
            ),
            2,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "count": self.count,
            "total_cost": self.total_cost,
            "holdings": [
                holding.to_dict()
                for holding in self.holdings
            ],
        }