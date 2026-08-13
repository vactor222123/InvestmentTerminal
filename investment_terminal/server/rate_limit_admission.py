"""
Per-identity inbound rate-limit admission boundary.

The service receives only an opaque rate-limit identity and owns the lifecycle
of process-local token buckets for those identities.
"""

from collections.abc import Callable
from decimal import Decimal
from threading import Lock

from investment_terminal.server.rate_limit_identity import (
    GroundedAIServerRateLimitIdentity,
)
from investment_terminal.server.rate_limits import (
    DecimalClock,
    GroundedAIServerRateLimitDecision,
    GroundedAIServerRateLimitPolicy,
    GroundedAIServerTokenBucketRateLimiter,
)


class GroundedAIServerRateLimitAdmissionService:
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

        self._policy = policy
        self._clock = clock
        self._limiters: dict[
            GroundedAIServerRateLimitIdentity,
            GroundedAIServerTokenBucketRateLimiter,
        ] = {}
        self._lock = Lock()

    def decide(
        self,
        *,
        identity: GroundedAIServerRateLimitIdentity,
    ) -> GroundedAIServerRateLimitDecision:
        if not isinstance(
            identity,
            GroundedAIServerRateLimitIdentity,
        ):
            raise TypeError(
                "identity must be a GroundedAIServerRateLimitIdentity"
            )

        with self._lock:
            limiter = self._limiters.get(
                identity
            )
            if limiter is None:
                limiter = GroundedAIServerTokenBucketRateLimiter(
                    policy=self._policy,
                    clock=self._clock,
                )
                self._limiters[
                    identity
                ] = limiter

        return limiter.decide()

    @property
    def identity_count(self) -> int:
        with self._lock:
            return len(
                self._limiters
            )
