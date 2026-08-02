"""
Contribution-plan models.
"""

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Any


@dataclass(frozen=True, slots=True)
class ContributionPlanItem:
    """One recommended destination for new capital."""

    key: str
    amount: float
    share: float
    reason: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.key, str)
            or not self.key.strip()
        ):
            raise ValueError(
                "key must be a non-empty string"
            )

        if (
            not isinstance(self.reason, str)
            or not self.reason.strip()
        ):
            raise ValueError(
                "reason must be a non-empty string"
            )

        self._validate_non_negative_number(
            self.amount,
            field_name="amount",
        )
        self._validate_weight(
            self.share,
            field_name="share",
        )

        object.__setattr__(
            self,
            "key",
            self.key.strip().upper(),
        )
        object.__setattr__(
            self,
            "reason",
            self.reason.strip(),
        )

    @property
    def percent(self) -> float:
        return round(
            self.share * 100.0,
            4,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "amount": self.amount,
            "share": self.share,
            "percent": self.percent,
            "reason": self.reason,
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
class ContributionPlan:
    """Allocation of one available contribution across strategic buckets."""

    available_capital: float
    deployable_capital: float
    retained_cash: float
    items: tuple[ContributionPlanItem, ...]
    status: str

    SUPPORTED_STATUSES = (
        "ALLOCATE",
        "HOLD_CASH",
        "NO_CAPITAL",
    )

    def __post_init__(self) -> None:
        for field_name in (
            "available_capital",
            "deployable_capital",
            "retained_cash",
        ):
            ContributionPlanItem._validate_non_negative_number(
                getattr(self, field_name),
                field_name=field_name,
            )

        if not isinstance(self.items, tuple):
            raise TypeError(
                "items must be a tuple"
            )

        if any(
            not isinstance(
                item,
                ContributionPlanItem,
            )
            for item in self.items
        ):
            raise TypeError(
                "items must contain only ContributionPlanItem objects"
            )

        normalized_status = self.status.strip().upper()

        if normalized_status not in self.SUPPORTED_STATUSES:
            raise ValueError(
                "status must be one of: "
                + ", ".join(self.SUPPORTED_STATUSES)
            )

        object.__setattr__(
            self,
            "status",
            normalized_status,
        )

        if round(
            self.deployable_capital
            + self.retained_cash,
            2,
        ) != round(
            self.available_capital,
            2,
        ):
            raise ValueError(
                "deployable_capital and retained_cash "
                "must equal available_capital"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "available_capital": self.available_capital,
            "deployable_capital": self.deployable_capital,
            "retained_cash": self.retained_cash,
            "items": [
                item.to_dict()
                for item in self.items
            ],
        }