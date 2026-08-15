"""
Aggregated provider usage/cost ledger summary.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class GroundedProviderUsageCostLedgerSummary:
    request_count: int
    currency: str | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: Decimal
    output_cost: Decimal
    total_cost: Decimal

    def __post_init__(self) -> None:
        if (
            isinstance(self.request_count, bool)
            or not isinstance(self.request_count, int)
            or self.request_count < 0
        ):
            raise ValueError(
                "request_count must be a non-negative integer"
            )
        for field_name in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError(
                "total_tokens must equal input_tokens + output_tokens"
            )

        if self.request_count == 0:
            if self.currency is not None:
                raise ValueError(
                    "empty summary currency must be None"
                )
        elif (
            not isinstance(self.currency, str)
            or not self.currency.strip()
        ):
            raise ValueError(
                "non-empty summary currency must be present"
            )

        for field_name in (
            "input_cost",
            "output_cost",
            "total_cost",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, Decimal):
                raise TypeError(
                    f"{field_name} must be a Decimal"
                )
            if not value.is_finite() or value < 0:
                raise ValueError(
                    f"{field_name} must be a finite non-negative Decimal"
                )

        if self.total_cost != self.input_cost + self.output_cost:
            raise ValueError(
                "total_cost must equal input_cost + output_cost"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "request_count": self.request_count,
            "currency": self.currency,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "input_cost": str(self.input_cost),
            "output_cost": str(self.output_cost),
            "total_cost": str(self.total_cost),
        }
