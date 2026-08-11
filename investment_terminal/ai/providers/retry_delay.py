"""
Provider-neutral deterministic retry delay policy and precedence.

Policy backoff is calculated locally. If a retryable transport failure carries
provider-requested retry_after_seconds, the effective delay is the greater of
the local policy delay and the provider-requested delay.

Backward compatibility:
- decision.delay_seconds remains the public effective-delay attribute;
- decision.to_dict() preserves the original two-key serialization contract.
Detailed precedence fields remain available as attributes.
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
    retry_number: int
    policy_delay_seconds: Decimal
    provider_retry_after_seconds: Decimal | None
    effective_delay_seconds: Decimal

    def __post_init__(self) -> None:
        if (
            isinstance(self.retry_number, bool)
            or not isinstance(self.retry_number, int)
            or self.retry_number < 1
        ):
            raise ValueError(
                "retry_number must be a positive integer"
            )

        for field_name in (
            "policy_delay_seconds",
            "effective_delay_seconds",
        ):
            object.__setattr__(
                self,
                field_name,
                _non_negative_decimal(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )

        if self.provider_retry_after_seconds is not None:
            object.__setattr__(
                self,
                "provider_retry_after_seconds",
                _non_negative_decimal(
                    self.provider_retry_after_seconds,
                    field_name="provider_retry_after_seconds",
                ),
            )

        expected = self.policy_delay_seconds
        if self.provider_retry_after_seconds is not None:
            expected = max(
                expected,
                self.provider_retry_after_seconds,
            )

        if self.effective_delay_seconds != expected:
            raise ValueError(
                "effective_delay_seconds must equal max("
                "policy_delay_seconds, provider_retry_after_seconds)"
            )

    @property
    def delay_seconds(self) -> Decimal:
        """Backward-compatible alias for the effective retry delay."""
        return self.effective_delay_seconds

    def to_dict(self) -> dict[str, Any]:
        """
        Preserve the original public serialization contract.

        Detailed precedence information is intentionally available only through
        typed attributes so existing callers comparing serialized dictionaries
        remain stable.
        """
        return {
            "retry_number": self.retry_number,
            "delay_seconds": str(
                self.effective_delay_seconds
            ),
        }


class GroundedProviderRetryDelayService:
    def decide(
        self,
        *,
        policy: GroundedProviderRetryDelayPolicy,
        retry_number: int,
        provider_retry_after_seconds: Decimal | None = None,
    ) -> GroundedProviderRetryDelayDecision:
        if not isinstance(
            policy,
            GroundedProviderRetryDelayPolicy,
        ):
            raise TypeError(
                "policy must be a GroundedProviderRetryDelayPolicy"
            )

        policy_delay = policy.delay_for_retry(
            retry_number=retry_number
        )
        effective_delay = policy_delay

        if provider_retry_after_seconds is not None:
            provider_delay = _non_negative_decimal(
                provider_retry_after_seconds,
                field_name="provider_retry_after_seconds",
            )
            effective_delay = max(
                policy_delay,
                provider_delay,
            )

        return GroundedProviderRetryDelayDecision(
            retry_number=retry_number,
            policy_delay_seconds=policy_delay,
            provider_retry_after_seconds=provider_retry_after_seconds,
            effective_delay_seconds=effective_delay,
        )
