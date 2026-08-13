from decimal import Decimal

import pytest

from investment_terminal.server.rate_limit_headers import (
    grounded_ai_rate_limit_headers,
)
from investment_terminal.server.rate_limits import (
    GroundedAIServerRateLimitDecision,
    GroundedAIServerRateLimitPolicy,
)


def policy() -> GroundedAIServerRateLimitPolicy:
    return GroundedAIServerRateLimitPolicy(
        capacity=10,
        refill_tokens_per_second=Decimal("2"),
    )


def test_headers_expose_only_safe_numeric_bucket_metadata() -> None:
    headers = grounded_ai_rate_limit_headers(
        policy=policy(),
        decision=GroundedAIServerRateLimitDecision(
            allowed=True,
            remaining_tokens=Decimal("7.5"),
            retry_after_seconds=None,
        ),
    )

    assert headers == {
        "RateLimit-Limit": "10",
        "RateLimit-Remaining": "7",
        "RateLimit-Reset": "2",
    }


def test_denied_decision_reports_zero_immediate_remaining() -> None:
    headers = grounded_ai_rate_limit_headers(
        policy=policy(),
        decision=GroundedAIServerRateLimitDecision(
            allowed=False,
            remaining_tokens=Decimal("0.25"),
            retry_after_seconds=Decimal("0.375"),
        ),
    )

    assert headers["RateLimit-Remaining"] == "0"
    assert headers["RateLimit-Reset"] == "5"


def test_header_formatter_rejects_wrong_types() -> None:
    decision = GroundedAIServerRateLimitDecision(
        allowed=True,
        remaining_tokens=Decimal("9"),
        retry_after_seconds=None,
    )

    with pytest.raises(TypeError, match="policy"):
        grounded_ai_rate_limit_headers(
            policy=object(),
            decision=decision,
        )

    with pytest.raises(TypeError, match="decision"):
        grounded_ai_rate_limit_headers(
            policy=policy(),
            decision=object(),
        )
