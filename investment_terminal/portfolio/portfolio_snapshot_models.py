"""
Portfolio snapshot models.
"""

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Any

from investment_terminal.portfolio.current_portfolio_models import (
    CurrentPortfolio,
    SUPPORTED_ASSET_TYPES,
    SUPPORTED_SLEEVES,
)


@dataclass(frozen=True, slots=True)
class PortfolioBreakdownItem:
    """One value and weight inside a portfolio breakdown."""

    key: str
    amount: float
    weight: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.key, str)
            or not self.key.strip()
        ):
            raise ValueError(
                "key must be a non-empty string"
            )

        self._validate_non_negative_number(
            self.amount,
            field_name="amount",
        )
        self._validate_weight(
            self.weight,
            field_name="weight",
        )

        object.__setattr__(
            self,
            "key",
            self.key.strip().upper(),
        )

    @property
    def percent(self) -> float:
        return round(
            self.weight * 100.0,
            4,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "amount": self.amount,
            "weight": self.weight,
            "percent": self.percent,
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
class PortfolioSnapshot:
    """Calculated summary of one current portfolio."""

    portfolio_name: str
    base_currency: str
    total_value: float
    invested_value: float
    cash_value: float
    monthly_contribution: float
    asset_breakdown: tuple[PortfolioBreakdownItem, ...]
    sleeve_breakdown: tuple[PortfolioBreakdownItem, ...]

    WEIGHT_TOLERANCE = 0.0001
    AMOUNT_TOLERANCE = 0.01

    def __post_init__(self) -> None:
        for field_name in (
            "portfolio_name",
            "base_currency",
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
            "base_currency",
            self.base_currency.upper(),
        )

        for field_name in (
            "total_value",
            "invested_value",
            "cash_value",
            "monthly_contribution",
        ):
            PortfolioBreakdownItem._validate_non_negative_number(
                getattr(self, field_name),
                field_name=field_name,
            )

        for field_name in (
            "asset_breakdown",
            "sleeve_breakdown",
        ):
            values = getattr(
                self,
                field_name,
            )

            if not isinstance(values, tuple):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if any(
                not isinstance(
                    item,
                    PortfolioBreakdownItem,
                )
                for item in values
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    "PortfolioBreakdownItem objects"
                )

            keys = tuple(
                item.key
                for item in values
            )

            if len(keys) != len(set(keys)):
                raise ValueError(
                    f"{field_name} must contain unique keys"
                )

        if abs(
            self.invested_value
            + self.cash_value
            - self.total_value
        ) > self.AMOUNT_TOLERANCE:
            raise ValueError(
                "invested_value and cash_value must equal total_value"
            )

        self._validate_breakdown(
            self.asset_breakdown,
            field_name="asset_breakdown",
        )
        self._validate_breakdown(
            self.sleeve_breakdown,
            field_name="sleeve_breakdown",
        )

    @property
    def cash_weight(self) -> float:
        if self.total_value == 0:
            return 0.0

        return round(
            self.cash_value
            / self.total_value,
            8,
        )

    @property
    def invested_weight(self) -> float:
        if self.total_value == 0:
            return 0.0

        return round(
            self.invested_value
            / self.total_value,
            8,
        )

    def asset(
        self,
        asset_type: str,
    ) -> PortfolioBreakdownItem:
        return self._require_item(
            self.asset_breakdown,
            asset_type,
        )

    def sleeve(
        self,
        sleeve: str,
    ) -> PortfolioBreakdownItem:
        return self._require_item(
            self.sleeve_breakdown,
            sleeve,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_name": self.portfolio_name,
            "base_currency": self.base_currency,
            "total_value": self.total_value,
            "invested_value": self.invested_value,
            "invested_weight": self.invested_weight,
            "cash_value": self.cash_value,
            "cash_weight": self.cash_weight,
            "monthly_contribution": self.monthly_contribution,
            "asset_breakdown": [
                item.to_dict()
                for item in self.asset_breakdown
            ],
            "sleeve_breakdown": [
                item.to_dict()
                for item in self.sleeve_breakdown
            ],
        }

    def _validate_breakdown(
        self,
        items: tuple[PortfolioBreakdownItem, ...],
        *,
        field_name: str,
    ) -> None:
        amount_total = sum(
            item.amount
            for item in items
        )
        weight_total = sum(
            item.weight
            for item in items
        )

        if abs(
            amount_total - self.total_value
        ) > self.AMOUNT_TOLERANCE:
            raise ValueError(
                f"{field_name} amounts must equal total_value"
            )

        expected_weight = (
            1.0
            if self.total_value > 0
            else 0.0
        )

        if abs(
            weight_total - expected_weight
        ) > self.WEIGHT_TOLERANCE:
            raise ValueError(
                f"{field_name} weights must equal "
                f"{expected_weight}"
            )

    @staticmethod
    def _require_item(
        items: tuple[PortfolioBreakdownItem, ...],
        key: str,
    ) -> PortfolioBreakdownItem:
        normalized = key.strip().upper()

        for item in items:
            if item.key == normalized:
                return item

        raise KeyError(
            f"No portfolio breakdown item found for {normalized}"
        )