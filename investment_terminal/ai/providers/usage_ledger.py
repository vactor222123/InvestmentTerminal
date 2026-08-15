"""
Immutable provider usage/cost ledger record.

The ledger model is provider-neutral and persistence-agnostic. It records only
explicit, already-observed usage and deterministic estimated cost; it does not
perform provider calls, pricing lookup, budget enforcement, or grounding.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from investment_terminal.utils.validation import normalize_required_text


def _non_negative_int(
    value: int,
    *,
    field_name: str,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"{field_name} must be a non-negative integer"
        )
    return value


def _non_negative_decimal(
    value: Decimal | str | int,
    *,
    field_name: str,
) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(
            f"{field_name} must be a Decimal-compatible value"
        )
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise TypeError(
            f"{field_name} must be a Decimal-compatible value"
        ) from exc
    if not parsed.is_finite() or parsed < 0:
        raise ValueError(
            f"{field_name} must be a finite non-negative decimal"
        )
    return parsed


@dataclass(frozen=True, slots=True)
class GroundedProviderUsageCostLedgerRecord:
    """
    One immutable successful provider usage/cost accounting observation.

    `request_id` is the canonical record identity. `recorded_at` is explicit
    operational metadata and must be timezone-aware.
    """

    request_id: str
    provider_identity: str
    model_identity: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    currency: str
    input_cost: Decimal
    output_cost: Decimal
    total_cost: Decimal
    recorded_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            normalize_required_text(
                self.request_id,
                field_name="request_id",
            ),
        )
        object.__setattr__(
            self,
            "provider_identity",
            normalize_required_text(
                self.provider_identity,
                field_name="provider_identity",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "model_identity",
            normalize_required_text(
                self.model_identity,
                field_name="model_identity",
            ),
        )
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
            "input_tokens",
            "output_tokens",
            "total_tokens",
        ):
            object.__setattr__(
                self,
                field_name,
                _non_negative_int(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )

        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError(
                "total_tokens must equal input_tokens + output_tokens"
            )

        for field_name in (
            "input_cost",
            "output_cost",
            "total_cost",
        ):
            object.__setattr__(
                self,
                field_name,
                _non_negative_decimal(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )

        if self.total_cost != self.input_cost + self.output_cost:
            raise ValueError(
                "total_cost must equal input_cost + output_cost"
            )

        if not isinstance(self.recorded_at, datetime):
            raise TypeError(
                "recorded_at must be a datetime"
            )
        if (
            self.recorded_at.tzinfo is None
            or self.recorded_at.utcoffset() is None
        ):
            raise ValueError(
                "recorded_at must be timezone-aware"
            )

    @property
    def identity_key(self) -> str:
        return self.request_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "provider_identity": self.provider_identity,
            "model_identity": self.model_identity,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "currency": self.currency,
            "input_cost": str(self.input_cost),
            "output_cost": str(self.output_cost),
            "total_cost": str(self.total_cost),
            "recorded_at": self.recorded_at.isoformat(),
        }
