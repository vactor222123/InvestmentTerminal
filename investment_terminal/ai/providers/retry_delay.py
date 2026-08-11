"""
Provider-neutral deterministic retry delay policy.

This module calculates retry delays only. It performs no sleeping, clock access,
transport I/O, Retry-After parsing, jitter, or provider-specific behavior.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


def _non_negative_decimal(
    value: Decimal | str | int | float,
    *,
    field_name: str,
) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(
            f"{field_name} must be Decimal-compatible"
        )
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise TypeError(
            f"{field_name} must be Decimal-compatible"
        ) from exc
    if not parsed.is_finite() or parsed < 0:
        raise ValueError(
            f"{field_name} must be finite and non-negative"
        )
    return parsed


@dataclass(frozen=True, slots=True)
class GroundedProviderRetryDelayPolicy:
    """
    Deterministic bounded exponential retry delay policy.

    retry_number is one-based and refers to the retry about to happen:
    retry_number=1 is the delay after the initial failed attempt.
    """

    initial_delay_seconds: Decimal
    multiplier: Decimal
    maximum_delay_seconds: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "initial_delay_seconds",
            _non_negative_decimal(
                self.initial_delay_seconds,
                field_name="initial_delay_seconds",
            ),
        )
        object.__setattr__(
            self,
            "multiplier",
            _non_negative_decimal(
                self.multiplier,
                field_name="multiplier",
            ),
        )
        object.__setattr__(
            self,
            "maximum_delay_seconds",
            _non_negative_decimal(
                self.maximum_delay_seconds,
                field_name="maximum_delay_seconds",
            ),
        )

        if self.multiplier < Decimal("1"):
            raise ValueError(
                "multiplier must be at least 1"
            )
        if self.maximum_delay_seconds < self.initial_delay_seconds:
            raise ValueError(
                "maximum_delay_seconds must be at least initial_delay_seconds"
            )

    def delay_for_retry(
        self,
        *,
        retry_number: int,
    ) -> Decimal:
        if (
            isinstance(retry_number, bool)
            or not isinstance(retry_number, int)
            or retry_number < 1
        ):
            raise ValueError(
                "retry_number must be a positive integer"
            )

        delay = (
            self.initial_delay_seconds
            * (self.multiplier ** (retry_number - 1))
        )
        return min(
            delay,
            self.maximum_delay_seconds,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_delay_seconds": str(
                self.initial_delay_seconds
            ),
            "multiplier": str(
                self.multiplier
            ),
            "maximum_delay_seconds": str(
                self.maximum_delay_seconds
            ),
        }


@dataclass(frozen=True, slots=True)
class GroundedProviderRetryDelayDecision:
    """One deterministic retry-delay decision."""

    retry_number: int
    delay_seconds: Decimal

    def __post_init__(self) -> None:
        if (
            isinstance(self.retry_number, bool)
            or not isinstance(self.retry_number, int)
            or self.retry_number < 1
        ):
            raise ValueError(
                "retry_number must be a positive integer"
            )
        object.__setattr__(
            self,
            "delay_seconds",
            _non_negative_decimal(
                self.delay_seconds,
                field_name="delay_seconds",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "retry_number": self.retry_number,
            "delay_seconds": str(
                self.delay_seconds
            ),
        }


class GroundedProviderRetryDelayService:
    """Pure calculator for one retry delay decision."""

    def decide(
        self,
        *,
        policy: GroundedProviderRetryDelayPolicy,
        retry_number: int,
    ) -> GroundedProviderRetryDelayDecision:
        if not isinstance(
            policy,
            GroundedProviderRetryDelayPolicy,
        ):
            raise TypeError(
                "policy must be a GroundedProviderRetryDelayPolicy"
            )

        return GroundedProviderRetryDelayDecision(
            retry_number=retry_number,
            delay_seconds=policy.delay_for_retry(
                retry_number=retry_number
            ),
        )
