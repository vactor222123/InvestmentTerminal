"""
Provider-neutral pricing and deterministic token-cost accounting.

Pricing data is explicit configuration. This module contains no hardcoded
provider prices, no network calls, and no provider SDK dependencies.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from investment_terminal.ai.model_adapter import GroundedProviderUsage
from investment_terminal.utils.validation import normalize_required_text


TOKENS_PER_MILLION = Decimal("1000000")
COST_QUANTUM = Decimal("0.000001")


def _non_negative_decimal(value: Decimal | str | int, *, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be a Decimal-compatible value")
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
class GroundedProviderPricingEntry:
    """Explicit price entry for one provider/model pair."""

    provider_identity: str
    model_identity: str
    currency: str
    input_cost_per_million_tokens: Decimal
    output_cost_per_million_tokens: Decimal

    def __post_init__(self) -> None:
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
        object.__setattr__(
            self,
            "input_cost_per_million_tokens",
            _non_negative_decimal(
                self.input_cost_per_million_tokens,
                field_name="input_cost_per_million_tokens",
            ),
        )
        object.__setattr__(
            self,
            "output_cost_per_million_tokens",
            _non_negative_decimal(
                self.output_cost_per_million_tokens,
                field_name="output_cost_per_million_tokens",
            ),
        )

    @property
    def identity_key(self) -> str:
        return f"{self.provider_identity}:{self.model_identity}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_identity": self.provider_identity,
            "model_identity": self.model_identity,
            "currency": self.currency,
            "input_cost_per_million_tokens": str(
                self.input_cost_per_million_tokens
            ),
            "output_cost_per_million_tokens": str(
                self.output_cost_per_million_tokens
            ),
        }


@dataclass(frozen=True, slots=True)
class GroundedProviderCost:
    """Deterministic estimated cost derived from provider usage."""

    provider_identity: str
    model_identity: str
    currency: str
    input_cost: Decimal
    output_cost: Decimal
    total_cost: Decimal

    def __post_init__(self) -> None:
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_identity": self.provider_identity,
            "model_identity": self.model_identity,
            "currency": self.currency,
            "input_cost": str(self.input_cost),
            "output_cost": str(self.output_cost),
            "total_cost": str(self.total_cost),
        }


@dataclass(frozen=True, slots=True)
class GroundedProviderPricingPolicy:
    """Fail-closed immutable pricing table."""

    entries: tuple[GroundedProviderPricingEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.entries, tuple):
            raise TypeError("entries must be a tuple")
        if any(
            not isinstance(item, GroundedProviderPricingEntry)
            for item in self.entries
        ):
            raise TypeError(
                "entries must contain only GroundedProviderPricingEntry values"
            )
        keys = tuple(item.identity_key for item in self.entries)
        if len(set(keys)) != len(keys):
            raise ValueError(
                "provider/model pricing entries must be unique"
            )

    def require_entry(
        self,
        *,
        provider_identity: str,
        model_identity: str,
    ) -> GroundedProviderPricingEntry:
        provider = normalize_required_text(
            provider_identity,
            field_name="provider_identity",
            uppercase=True,
        )
        model = normalize_required_text(
            model_identity,
            field_name="model_identity",
        )
        key = f"{provider}:{model}"
        for entry in self.entries:
            if entry.identity_key == key:
                return entry
        raise LookupError(
            "pricing is not configured for provider/model: "
            f"{provider}:{model}"
        )

    def estimate_cost(
        self,
        *,
        provider_identity: str,
        model_identity: str,
        usage: GroundedProviderUsage,
    ) -> GroundedProviderCost:
        if not isinstance(usage, GroundedProviderUsage):
            raise TypeError(
                "usage must be a GroundedProviderUsage"
            )

        entry = self.require_entry(
            provider_identity=provider_identity,
            model_identity=model_identity,
        )

        input_cost = (
            Decimal(usage.input_tokens)
            * entry.input_cost_per_million_tokens
            / TOKENS_PER_MILLION
        ).quantize(
            COST_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        output_cost = (
            Decimal(usage.output_tokens)
            * entry.output_cost_per_million_tokens
            / TOKENS_PER_MILLION
        ).quantize(
            COST_QUANTUM,
            rounding=ROUND_HALF_UP,
        )

        return GroundedProviderCost(
            provider_identity=entry.provider_identity,
            model_identity=entry.model_identity,
            currency=entry.currency,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=input_cost + output_cost,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [
                item.to_dict()
                for item in sorted(
                    self.entries,
                    key=lambda value: value.identity_key,
                )
            ]
        }
