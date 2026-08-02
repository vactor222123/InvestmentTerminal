"""
Portfolio policy-gap models.
"""

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Any


@dataclass(frozen=True, slots=True)
class PortfolioPolicyGapItem:
    """Current allocation compared with one strategic target."""

    key: str
    current_amount: float
    current_weight: float
    target_amount: float
    target_weight: float
    gap_amount: float
    gap_weight: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.key, str)
            or not self.key.strip()
        ):
            raise ValueError(
                "key must be a non-empty string"
            )

        object.__setattr__(
            self,
            "key",
            self.key.strip().upper(),
        )

        for field_name in (
            "current_amount",
            "target_amount",
        ):
            self._validate_non_negative_number(
                getattr(self, field_name),
                field_name=field_name,
            )

        for field_name in (
            "current_weight",
            "target_weight",
        ):
            self._validate_weight(
                getattr(self, field_name),
                field_name=field_name,
            )

        for field_name in (
            "gap_amount",
            "gap_weight",
        ):
            self._validate_finite_number(
                getattr(self, field_name),
                field_name=field_name,
            )

    @property
    def status(self) -> str:
        tolerance = 0.005

        if self.gap_weight > tolerance:
            return "UNDERWEIGHT"

        if self.gap_weight < -tolerance:
            return "OVERWEIGHT"

        return "ON_TARGET"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "current_amount": self.current_amount,
            "current_weight": self.current_weight,
            "current_percent": round(
                self.current_weight * 100.0,
                4,
            ),
            "target_amount": self.target_amount,
            "target_weight": self.target_weight,
            "target_percent": round(
                self.target_weight * 100.0,
                4,
            ),
            "gap_amount": self.gap_amount,
            "gap_weight": self.gap_weight,
            "gap_percent": round(
                self.gap_weight * 100.0,
                4,
            ),
            "status": self.status,
        }

    @staticmethod
    def _validate_non_negative_number(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
            or float(value) < 0
        ):
            raise ValueError(
                f"{field_name} must be a finite non-negative number"
            )

    @staticmethod
    def _validate_finite_number(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
        ):
            raise ValueError(
                f"{field_name} must be a finite number"
            )

    @staticmethod
    def _validate_weight(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
            or not 0.0 <= float(value) <= 1.0
        ):
            raise ValueError(
                f"{field_name} must be between 0 and 1"
            )


@dataclass(frozen=True, slots=True)
class PortfolioPolicyGapResult:
    """Strategic allocation gaps for one portfolio snapshot."""

    portfolio_name: str
    base_currency: str
    total_value: float
    items: tuple[PortfolioPolicyGapItem, ...]

    REQUIRED_KEYS = (
        "CORE_LONG_TERM",
        "TACTICAL_TOTAL",
        "CASH_RESERVE",
    )

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

        PortfolioPolicyGapItem._validate_non_negative_number(
            self.total_value,
            field_name="total_value",
        )

        if not isinstance(self.items, tuple):
            raise TypeError(
                "items must be a tuple"
            )

        if any(
            not isinstance(
                item,
                PortfolioPolicyGapItem,
            )
            for item in self.items
        ):
            raise TypeError(
                "items must contain only PortfolioPolicyGapItem objects"
            )

        keys = tuple(
            item.key
            for item in self.items
        )

        if keys != self.REQUIRED_KEYS:
            raise ValueError(
                "items must use the required strategic order"
            )

    def item(
        self,
        key: str,
    ) -> PortfolioPolicyGapItem:
        normalized = key.strip().upper()

        for item in self.items:
            if item.key == normalized:
                return item

        raise KeyError(
            f"No portfolio policy gap found for {normalized}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_name": self.portfolio_name,
            "base_currency": self.base_currency,
            "total_value": self.total_value,
            "items": [
                item.to_dict()
                for item in self.items
            ],
        }