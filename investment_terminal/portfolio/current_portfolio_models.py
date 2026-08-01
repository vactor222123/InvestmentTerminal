"""
Current portfolio and investment-policy domain models.
"""

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Any


SUPPORTED_ASSET_TYPES = (
    "ETF",
    "STOCK",
    "BOND",
    "GOLD",
    "CASH",
    "OTHER",
)

SUPPORTED_SLEEVES = (
    "CORE",
    "TACTICAL",
    "RESERVE",
)


@dataclass(frozen=True, slots=True)
class PortfolioHolding:
    """One currently owned portfolio position."""

    symbol: str
    name: str
    asset_type: str
    sleeve: str
    quantity: float
    average_cost: float
    currency: str = "EUR"
    isin: str | None = None
    exchange_ticker: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "symbol",
            self._normalize_text(
                self.symbol,
                field_name="symbol",
            ).upper(),
        )
        object.__setattr__(
            self,
            "name",
            self._normalize_text(
                self.name,
                field_name="name",
            ),
        )
        object.__setattr__(
            self,
            "asset_type",
            self._normalize_choice(
                self.asset_type,
                field_name="asset_type",
                choices=SUPPORTED_ASSET_TYPES,
            ),
        )
        object.__setattr__(
            self,
            "sleeve",
            self._normalize_choice(
                self.sleeve,
                field_name="sleeve",
                choices=SUPPORTED_SLEEVES,
            ),
        )
        object.__setattr__(
            self,
            "currency",
            self._normalize_text(
                self.currency,
                field_name="currency",
            ).upper(),
        )
        object.__setattr__(
            self,
            "isin",
            self._normalize_optional_isin(
                self.isin
            ),
        )
        object.__setattr__(
            self,
            "exchange_ticker",
            self._normalize_optional_text(
                self.exchange_ticker,
                uppercase=True,
            ),
        )

        self._validate_positive_number(
            self.quantity,
            field_name="quantity",
        )
        self._validate_non_negative_number(
            self.average_cost,
            field_name="average_cost",
        )

        if self.asset_type == "CASH":
            raise ValueError(
                "Cash must be stored in portfolio cash_balance, "
                "not as a holding"
            )

        if (
            self.sleeve == "CORE"
            and self.asset_type == "STOCK"
        ):
            raise ValueError(
                "Individual stocks must use the TACTICAL sleeve"
            )

        if (
            self.asset_type in {"ETF", "BOND", "GOLD"}
            and self.isin is None
        ):
            raise ValueError(
                "ETF, BOND, and GOLD holdings must provide an ISIN"
            )

    @property
    def invested_cost(self) -> float:
        return round(
            self.quantity * self.average_cost,
            2,
        )

    @property
    def instrument_key(self) -> str:
        """
        Stable identifier used for duplicate detection and price mapping.
        """
        return self.isin or self.exchange_ticker or self.symbol

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "asset_type": self.asset_type,
            "sleeve": self.sleeve,
            "quantity": self.quantity,
            "average_cost": self.average_cost,
            "currency": self.currency,
            "isin": self.isin,
            "exchange_ticker": self.exchange_ticker,
            "instrument_key": self.instrument_key,
            "invested_cost": self.invested_cost,
        }

    @staticmethod
    def _normalize_text(
        value: object,
        *,
        field_name: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} must be a non-empty string"
            )

        return value.strip()

    @staticmethod
    def _normalize_optional_text(
        value: object,
        *,
        uppercase: bool = False,
    ) -> str | None:
        if value is None:
            return None

        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                "optional text values must be non-empty strings or None"
            )

        normalized = value.strip()

        return (
            normalized.upper()
            if uppercase
            else normalized
        )

    @classmethod
    def _normalize_optional_isin(
        cls,
        value: object,
    ) -> str | None:
        normalized = cls._normalize_optional_text(
            value,
            uppercase=True,
        )

        if normalized is None:
            return None

        if (
            len(normalized) != 12
            or not normalized[:2].isalpha()
            or not normalized[2:].isalnum()
        ):
            raise ValueError(
                "isin must contain 12 alphanumeric characters "
                "and start with a two-letter country code"
            )

        return normalized

    @classmethod
    def _normalize_choice(
        cls,
        value: object,
        *,
        field_name: str,
        choices: tuple[str, ...],
    ) -> str:
        normalized = cls._normalize_text(
            value,
            field_name=field_name,
        ).upper()

        if normalized not in choices:
            raise ValueError(
                f"{field_name} must be one of: "
                + ", ".join(choices)
            )

        return normalized

    @staticmethod
    def _validate_positive_number(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
            or float(value) <= 0
        ):
            raise ValueError(
                f"{field_name} must be a finite number greater than zero"
            )

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


@dataclass(frozen=True, slots=True)
class PortfolioPolicy:
    """Long-term core, tactical-stock, and cash policy."""

    core_target_weight: float
    tactical_target_weight: float
    cash_target_weight: float
    monthly_contribution: float
    base_currency: str = "EUR"

    TOLERANCE = 0.0001

    def __post_init__(self) -> None:
        for field_name in (
            "core_target_weight",
            "tactical_target_weight",
            "cash_target_weight",
        ):
            value = getattr(
                self,
                field_name,
            )
            self._validate_weight(
                value,
                field_name=field_name,
            )

        total = (
            self.core_target_weight
            + self.tactical_target_weight
            + self.cash_target_weight
        )

        if abs(total - 1.0) > self.TOLERANCE:
            raise ValueError(
                "portfolio policy weights must sum to 1.0"
            )

        if not 0.85 <= self.core_target_weight <= 0.90:
            raise ValueError(
                "core_target_weight must be between 0.85 and 0.90"
            )

        if not 0.10 <= self.tactical_target_weight <= 0.15:
            raise ValueError(
                "tactical_target_weight must be between 0.10 and 0.15"
            )

        PortfolioHolding._validate_non_negative_number(
            self.monthly_contribution,
            field_name="monthly_contribution",
        )

        object.__setattr__(
            self,
            "base_currency",
            PortfolioHolding._normalize_text(
                self.base_currency,
                field_name="base_currency",
            ).upper(),
        )

    @property
    def invested_target_weight(self) -> float:
        return round(
            self.core_target_weight
            + self.tactical_target_weight,
            6,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "core_target_weight": self.core_target_weight,
            "tactical_target_weight": self.tactical_target_weight,
            "cash_target_weight": self.cash_target_weight,
            "invested_target_weight": self.invested_target_weight,
            "monthly_contribution": self.monthly_contribution,
            "base_currency": self.base_currency,
        }

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
class CurrentPortfolio:
    """Snapshot of owned positions, cash, and portfolio policy."""

    name: str
    policy: PortfolioPolicy
    holdings: tuple[PortfolioHolding, ...]
    cash_balance: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name",
            PortfolioHolding._normalize_text(
                self.name,
                field_name="name",
            ),
        )

        if not isinstance(
            self.policy,
            PortfolioPolicy,
        ):
            raise TypeError(
                "policy must be a PortfolioPolicy"
            )

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

        instrument_keys = tuple(
            holding.instrument_key
            for holding in self.holdings
        )

        if len(instrument_keys) != len(set(instrument_keys)):
            raise ValueError(
                "holdings must contain unique instruments"
            )

        PortfolioHolding._validate_non_negative_number(
            self.cash_balance,
            field_name="cash_balance",
        )

    @property
    def invested_cost(self) -> float:
        return round(
            sum(
                holding.invested_cost
                for holding in self.holdings
            ),
            2,
        )

    @property
    def total_cost_basis(self) -> float:
        return round(
            self.invested_cost
            + self.cash_balance,
            2,
        )

    @property
    def core_cost(self) -> float:
        return self._sleeve_cost(
            "CORE"
        )

    @property
    def tactical_cost(self) -> float:
        return self._sleeve_cost(
            "TACTICAL"
        )

    def _sleeve_cost(
        self,
        sleeve: str,
    ) -> float:
        return round(
            sum(
                holding.invested_cost
                for holding in self.holdings
                if holding.sleeve == sleeve
            ),
            2,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "policy": self.policy.to_dict(),
            "cash_balance": self.cash_balance,
            "invested_cost": self.invested_cost,
            "total_cost_basis": self.total_cost_basis,
            "core_cost": self.core_cost,
            "tactical_cost": self.tactical_cost,
            "holdings": [
                holding.to_dict()
                for holding in self.holdings
            ],
        }