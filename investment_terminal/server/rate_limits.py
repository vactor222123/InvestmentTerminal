"""
Deterministic inbound rate-limit policy and token-bucket service.

This module is framework-neutral and process-local. It performs no FastAPI,
network, persistence, or distributed coordination work.
"""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from threading import Lock


DecimalClock = Callable[[], Decimal]


@dataclass(frozen=True, slots=True)
class GroundedAIServerRateLimitPolicy:
    capacity: int
    refill_tokens_per_second: Decimal

    def __post_init__(self) -> None:
        if (
            isinstance(self.capacity, bool)
            or not isinstance(self.capacity, int)
            or self.capacity <= 0
        ):
            raise ValueError(
                "capacity must be a positive integer"
            )
        if (
            not isinstance(
                self.refill_tokens_per_second,
                Decimal,
            )
            or self.refill_tokens_per_second <= 0
        ):
            raise ValueError(
                "refill_tokens_per_second must be a positive Decimal"
            )


@dataclass(frozen=True, slots=True)
class GroundedAIServerRateLimitDecision:
    allowed: bool
    remaining_tokens: Decimal
    retry_after_seconds: Decimal | None

    def __post_init__(self) -> None:
        if not isinstance(
            self.remaining_tokens,
            Decimal,
        ):
            raise TypeError(
                "remaining_tokens must be a Decimal"
            )
        if self.remaining_tokens < 0:
            raise ValueError(
                "remaining_tokens must not be negative"
            )
        if self.allowed and self.retry_after_seconds is not None:
            raise ValueError(
                "allowed decisions must not have retry_after_seconds"
            )
        if not self.allowed:
            if (
                not isinstance(
                    self.retry_after_seconds,
                    Decimal,
                )
                or self.retry_after_seconds <= 0
            ):
                raise ValueError(
                    "denied decisions require positive retry_after_seconds"
                )

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "allowed": self.allowed,
            "remaining_tokens": str(
                self.remaining_tokens
            ),
            "retry_after_seconds": (
                str(self.retry_after_seconds)
                if self.retry_after_seconds is not None
                else None
            ),
        }


class GroundedAIServerTokenBucketRateLimiter:
    """
    Thread-safe process-local token bucket.

    One successful admission consumes one token. Tokens refill continuously at
    the configured rate up to capacity. The supplied clock must be monotonic.
    """

    def __init__(
        self,
        *,
        policy: GroundedAIServerRateLimitPolicy,
        clock: DecimalClock,
    ) -> None:
        if not isinstance(
            policy,
            GroundedAIServerRateLimitPolicy,
        ):
            raise TypeError(
                "policy must be a GroundedAIServerRateLimitPolicy"
            )
        if not callable(
            clock
        ):
            raise TypeError(
                "clock must be callable"
            )

        initial_time = clock()
        if not isinstance(
            initial_time,
            Decimal,
        ):
            raise TypeError(
                "clock must return Decimal"
            )

        self._policy = policy
        self._clock = clock
        self._tokens = Decimal(
            policy.capacity
        )
        self._last_refill = initial_time
        self._lock = Lock()

    def decide(
        self,
    ) -> GroundedAIServerRateLimitDecision:
        with self._lock:
            now = self._clock()
            if not isinstance(
                now,
                Decimal,
            ):
                raise TypeError(
                    "clock must return Decimal"
                )
            if now < self._last_refill:
                raise ValueError(
                    "clock must be monotonic"
                )

            elapsed = now - self._last_refill
            if elapsed > 0:
                self._tokens = min(
                    Decimal(
                        self._policy.capacity
                    ),
                    self._tokens
                    + (
                        elapsed
                        * self._policy.refill_tokens_per_second
                    ),
                )
                self._last_refill = now

            if self._tokens >= Decimal("1"):
                self._tokens -= Decimal("1")
                return GroundedAIServerRateLimitDecision(
                    allowed=True,
                    remaining_tokens=self._tokens,
                    retry_after_seconds=None,
                )

            missing = Decimal("1") - self._tokens
            retry_after = (
                missing
                / self._policy.refill_tokens_per_second
            )

            return GroundedAIServerRateLimitDecision(
                allowed=False,
                remaining_tokens=self._tokens,
                retry_after_seconds=retry_after,
            )
