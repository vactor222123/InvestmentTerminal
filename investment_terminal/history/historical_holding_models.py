"""
Canonical read model for one normalized historical holding.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Any

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class HistoricalHolding:
    """Immutable normalized holding projection for one historical snapshot."""

    snapshot_id: str
    holding_key: str
    symbol: str
    name: str
    asset_type: str
    sleeve: str
    strategy: str | None
    currency: str
    quantity: float
    unit_price: float
    market_value: float
    weight: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            HistoricalSnapshot._normalize_uuid(
                self.snapshot_id,
                field_name="snapshot_id",
            ),
        )

        for field_name in (
            "holding_key",
            "symbol",
            "name",
            "asset_type",
            "sleeve",
            "currency",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(
                        self,
                        field_name,
                    ),
                    field_name=field_name,
                    uppercase=(
                        field_name
                        in (
                            "holding_key",
                            "symbol",
                            "asset_type",
                            "sleeve",
                            "currency",
                        )
                    ),
                ),
            )

        object.__setattr__(
            self,
            "strategy",
            normalize_optional_text(
                self.strategy,
                field_name="strategy",
            ),
        )
        if self.strategy is not None:
            object.__setattr__(
                self,
                "strategy",
                self.strategy.upper(),
            )

        for field_name in (
            "quantity",
            "unit_price",
            "market_value",
            "weight",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    (
                        int,
                        float,
                    ),
                )
                or not isfinite(
                    float(
                        value
                    )
                )
                or float(
                    value
                ) < 0.0
            ):
                raise ValueError(
                    f"{field_name} must be a finite non-negative number"
                )

            object.__setattr__(
                self,
                field_name,
                float(
                    value
                ),
            )

        if self.weight > 1.0001:
            raise ValueError(
                "weight must not exceed 1"
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "holding_key": self.holding_key,
            "symbol": self.symbol,
            "name": self.name,
            "asset_type": self.asset_type,
            "sleeve": self.sleeve,
            "strategy": self.strategy,
            "currency": self.currency,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "market_value": self.market_value,
            "weight": self.weight,
        }

    def comparison_payload(
        self,
    ) -> dict[str, Any]:
        """Return the stable descriptive payload embedded in HoldingChange."""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "asset_type": self.asset_type,
            "sleeve": self.sleeve,
            "strategy": self.strategy,
            "currency": self.currency,
        }
