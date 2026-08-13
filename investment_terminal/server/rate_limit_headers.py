"""
Safe public response metadata for inbound rate limiting.

The formatter exposes only policy capacity and aggregate token-bucket state.
Rate-limit identities, API keys, and other authentication material never cross
this boundary.
"""

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

from investment_terminal.server.rate_limits import (
    GroundedAIServerRateLimitDecision,
    GroundedAIServerRateLimitPolicy,
)


def grounded_ai_rate_limit_headers(
    *,
    policy: GroundedAIServerRateLimitPolicy,
    decision: GroundedAIServerRateLimitDecision,
) -> dict[str, str]:
    if not isinstance(
        policy,
        GroundedAIServerRateLimitPolicy,
    ):
        raise TypeError(
            "policy must be a GroundedAIServerRateLimitPolicy"
        )
    if not isinstance(
        decision,
        GroundedAIServerRateLimitDecision,
    ):
        raise TypeError(
            "decision must be a GroundedAIServerRateLimitDecision"
        )

    remaining = int(
        decision.remaining_tokens.to_integral_value(
            rounding=ROUND_FLOOR,
        )
    )
    seconds_until_full = (
        Decimal(policy.capacity)
        - decision.remaining_tokens
    ) / policy.refill_tokens_per_second
    reset_seconds = int(
        seconds_until_full.to_integral_value(
            rounding=ROUND_CEILING,
        )
    )

    return {
        "RateLimit-Limit": str(policy.capacity),
        "RateLimit-Remaining": str(
            max(0, remaining)
        ),
        "RateLimit-Reset": str(
            max(0, reset_seconds)
        ),
    }
