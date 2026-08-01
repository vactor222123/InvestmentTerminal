"""
Structured portfolio-allocation models.
"""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from numbers import Real
from typing import Any

from investment_terminal.portfolio.recommendation_models import (
    CandidateRecommendation,
)


ALLOCATION_PROFILES = (
    "CONSERVATIVE",
    "BALANCED",
    "GROWTH",
)


@dataclass(frozen=True, slots=True)
class AllocationConstraints:
    """
    Portfolio-construction limits and preferences.
    """

    profile: str
    minimum_position_weight: float
    maximum_position_weight: float
    cash_reserve_weight: float

    def __post_init__(self) -> None:
        normalized_profile = self._normalize_profile(
            self.profile
        )

        minimum = self._validate_weight(
            self.minimum_position_weight,
            field_name="minimum_position_weight",
        )
        maximum = self._validate_weight(
            self.maximum_position_weight,
            field_name="maximum_position_weight",
        )
        cash_reserve = self._validate_weight(
            self.cash_reserve_weight,
            field_name="cash_reserve_weight",
        )

        if minimum > maximum:
            raise ValueError(
                "minimum_position_weight must not exceed "
                "maximum_position_weight"
            )

        if maximum <= 0:
            raise ValueError(
                "maximum_position_weight must be greater than zero"
            )

        if cash_reserve >= 1:
            raise ValueError(
                "cash_reserve_weight must be less than one"
            )

        object.__setattr__(
            self,
            "profile",
            normalized_profile,
        )
        object.__setattr__(
            self,
            "minimum_position_weight",
            minimum,
        )
        object.__setattr__(
            self,
            "maximum_position_weight",
            maximum,
        )
        object.__setattr__(
            self,
            "cash_reserve_weight",
            cash_reserve,
        )

    @property
    def investable_weight(self) -> float:
        return round(
            1.0 - self.cash_reserve_weight,
            10,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "minimum_position_weight": (
                self.minimum_position_weight
            ),
            "maximum_position_weight": (
                self.maximum_position_weight
            ),
            "cash_reserve_weight": (
                self.cash_reserve_weight
            ),
            "investable_weight": self.investable_weight,
        }

    @staticmethod
    def _normalize_profile(
        value: object,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                "profile must be a non-empty string"
            )

        normalized = (
            value.strip()
            .upper()
            .replace(" ", "_")
        )

        if normalized not in ALLOCATION_PROFILES:
            supported = ", ".join(
                ALLOCATION_PROFILES
            )
            raise ValueError(
                f"Unsupported allocation profile "
                f"'{normalized}'. Supported values: "
                f"{supported}."
            )

        return normalized

    @staticmethod
    def _validate_weight(
        value: object,
        field_name: str,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
        ):
            raise ValueError(
                f"{field_name} must be a finite number"
            )

        numeric = float(value)

        if numeric < 0 or numeric > 1:
            raise ValueError(
                f"{field_name} must be between zero and one"
            )

        return numeric


@dataclass(frozen=True, slots=True)
class PortfolioAllocationPosition:
    """
    One target position in a generated portfolio.
    """

    recommendation: CandidateRecommendation
    target_weight: float
    target_amount: float
    allocation_score: float
    explanation: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.recommendation,
            CandidateRecommendation,
        ):
            raise TypeError(
                "recommendation must be a "
                "CandidateRecommendation"
            )

        target_weight = self._validate_non_negative_number(
            self.target_weight,
            field_name="target_weight",
        )
        target_amount = self._validate_non_negative_number(
            self.target_amount,
            field_name="target_amount",
        )
        allocation_score = self._validate_non_negative_number(
            self.allocation_score,
            field_name="allocation_score",
        )

        if target_weight > 1:
            raise ValueError(
                "target_weight must not exceed one"
            )

        if (
            not isinstance(self.explanation, str)
            or not self.explanation.strip()
        ):
            raise ValueError(
                "explanation must be a non-empty string"
            )

        object.__setattr__(
            self,
            "target_weight",
            target_weight,
        )
        object.__setattr__(
            self,
            "target_amount",
            target_amount,
        )
        object.__setattr__(
            self,
            "allocation_score",
            allocation_score,
        )
        object.__setattr__(
            self,
            "explanation",
            self.explanation.strip(),
        )

    @property
    def rank(self) -> int:
        return self.recommendation.rank

    @property
    def symbol(self) -> str:
        return self.recommendation.symbol

    @property
    def currency(self) -> str:
        return self.recommendation.currency

    @property
    def recommendation_label(self) -> str:
        return self.recommendation.recommendation

    @property
    def risk_level(self) -> str:
        return self.recommendation.risk_level

    @property
    def target_percent(self) -> float:
        return round(
            self.target_weight * 100.0,
            4,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "symbol": self.symbol,
            "currency": self.currency,
            "recommendation": (
                self.recommendation_label
            ),
            "risk_level": self.risk_level,
            "target_weight": self.target_weight,
            "target_percent": self.target_percent,
            "target_amount": self.target_amount,
            "allocation_score": self.allocation_score,
            "explanation": self.explanation,
        }

    @staticmethod
    def _validate_non_negative_number(
        value: object,
        field_name: str,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
        ):
            raise ValueError(
                f"{field_name} must be a finite number"
            )

        numeric = float(value)

        if numeric < 0:
            raise ValueError(
                f"{field_name} must not be negative"
            )

        return numeric


@dataclass(frozen=True, slots=True)
class PortfolioAllocationResult:
    """
    Complete target allocation for one analyzed universe.
    """

    schema_version: str
    generated_at: datetime
    total_capital: float
    currency: str
    constraints: AllocationConstraints
    positions: tuple[
        PortfolioAllocationPosition,
        ...,
    ]
    cash_amount: float

    WEIGHT_TOLERANCE = 1e-6
    AMOUNT_TOLERANCE = 0.01

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, str)
            or not self.schema_version.strip()
        ):
            raise ValueError(
                "schema_version must be a non-empty string"
            )

        if not isinstance(
            self.generated_at,
            datetime,
        ):
            raise TypeError(
                "generated_at must be a datetime"
            )

        total_capital = self._validate_positive_number(
            self.total_capital,
            field_name="total_capital",
        )

        if (
            not isinstance(self.currency, str)
            or not self.currency.strip()
        ):
            raise ValueError(
                "currency must be a non-empty string"
            )

        if not isinstance(
            self.constraints,
            AllocationConstraints,
        ):
            raise TypeError(
                "constraints must be an "
                "AllocationConstraints"
            )

        if not isinstance(
            self.positions,
            tuple,
        ):
            raise TypeError(
                "positions must be a tuple"
            )

        if not self.positions:
            raise ValueError(
                "positions must not be empty"
            )

        if any(
            not isinstance(
                position,
                PortfolioAllocationPosition,
            )
            for position in self.positions
        ):
            raise TypeError(
                "positions must contain only "
                "PortfolioAllocationPosition objects"
            )

        symbols = [
            position.symbol
            for position in self.positions
        ]

        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "positions must contain unique symbols"
            )

        expected_ranks = list(
            range(
                1,
                len(self.positions) + 1,
            )
        )
        actual_ranks = [
            position.rank
            for position in self.positions
        ]

        if actual_ranks != expected_ranks:
            raise ValueError(
                "position ranks must be consecutive "
                "and start at one"
            )

        cash_amount = self._validate_non_negative_number(
            self.cash_amount,
            field_name="cash_amount",
        )

        invested_weight = sum(
            position.target_weight
            for position in self.positions
        )
        expected_invested_weight = (
            self.constraints.investable_weight
        )

        if abs(
            invested_weight
            - expected_invested_weight
        ) > self.WEIGHT_TOLERANCE:
            raise ValueError(
                "position weights must equal "
                "the investable portfolio weight"
            )

        for position in self.positions:
            if (
                position.target_weight
                > self.constraints.maximum_position_weight
                + self.WEIGHT_TOLERANCE
            ):
                raise ValueError(
                    "position weight exceeds "
                    "maximum_position_weight"
                )

            if (
                position.target_weight > 0
                and position.target_weight
                + self.WEIGHT_TOLERANCE
                < self.constraints.minimum_position_weight
            ):
                raise ValueError(
                    "positive position weight is below "
                    "minimum_position_weight"
                )

            expected_amount = (
                total_capital
                * position.target_weight
            )

            if abs(
                position.target_amount
                - expected_amount
            ) > self.AMOUNT_TOLERANCE:
                raise ValueError(
                    "position target_amount must match "
                    "total_capital and target_weight"
                )

        expected_cash_amount = (
            total_capital
            * self.constraints.cash_reserve_weight
        )

        if abs(
            cash_amount
            - expected_cash_amount
        ) > self.AMOUNT_TOLERANCE:
            raise ValueError(
                "cash_amount must match total_capital "
                "and cash_reserve_weight"
            )

        total_amount = (
            sum(
                position.target_amount
                for position in self.positions
            )
            + cash_amount
        )

        if abs(
            total_amount - total_capital
        ) > self.AMOUNT_TOLERANCE:
            raise ValueError(
                "allocated amounts and cash must equal "
                "total_capital"
            )

        normalized_currency = (
            self.currency.strip().upper()
        )

        if any(
            position.currency
            != normalized_currency
            for position in self.positions
        ):
            raise ValueError(
                "all positions must use "
                "the allocation currency"
            )

        object.__setattr__(
            self,
            "schema_version",
            self.schema_version.strip(),
        )
        object.__setattr__(
            self,
            "total_capital",
            total_capital,
        )
        object.__setattr__(
            self,
            "currency",
            normalized_currency,
        )
        object.__setattr__(
            self,
            "cash_amount",
            cash_amount,
        )

    @property
    def universe_size(self) -> int:
        return len(self.positions)

    @property
    def invested_amount(self) -> float:
        return round(
            sum(
                position.target_amount
                for position in self.positions
            ),
            2,
        )

    @property
    def invested_weight(self) -> float:
        return round(
            sum(
                position.target_weight
                for position in self.positions
            ),
            10,
        )

    @property
    def cash_weight(self) -> float:
        return self.constraints.cash_reserve_weight

    @property
    def top_position(
        self,
    ) -> PortfolioAllocationPosition:
        return max(
            self.positions,
            key=lambda position: (
                position.target_weight
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": (
                self.generated_at.isoformat()
            ),
            "profile": self.constraints.profile,
            "currency": self.currency,
            "total_capital": self.total_capital,
            "invested_amount": self.invested_amount,
            "cash_amount": self.cash_amount,
            "invested_weight": self.invested_weight,
            "cash_weight": self.cash_weight,
            "universe_size": self.universe_size,
            "top_symbol": self.top_position.symbol,
            "constraints": (
                self.constraints.to_dict()
            ),
            "positions": [
                position.to_dict()
                for position in self.positions
            ],
        }

    @staticmethod
    def _validate_positive_number(
        value: object,
        field_name: str,
    ) -> float:
        numeric = (
            PortfolioAllocationResult
            ._validate_non_negative_number(
                value,
                field_name=field_name,
            )
        )

        if numeric <= 0:
            raise ValueError(
                f"{field_name} must be greater than zero"
            )

        return numeric

    @staticmethod
    def _validate_non_negative_number(
        value: object,
        field_name: str,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
        ):
            raise ValueError(
                f"{field_name} must be a finite number"
            )

        numeric = float(value)

        if numeric < 0:
            raise ValueError(
                f"{field_name} must not be negative"
            )

        return numeric