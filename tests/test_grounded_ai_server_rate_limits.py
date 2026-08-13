from decimal import Decimal

import pytest

from investment_terminal.server.rate_limits import (
    GroundedAIServerRateLimitPolicy,
    GroundedAIServerTokenBucketRateLimiter,
)


class Clock:
    def __init__(self) -> None:
        self.value = Decimal("0")

    def __call__(self) -> Decimal:
        return self.value

    def advance(
        self,
        seconds: str,
    ) -> None:
        self.value += Decimal(
            seconds
        )


def policy() -> GroundedAIServerRateLimitPolicy:
    return GroundedAIServerRateLimitPolicy(
        capacity=2,
        refill_tokens_per_second=Decimal("0.5"),
    )


def test_token_bucket_allows_up_to_capacity() -> None:
    clock = Clock()
    limiter = GroundedAIServerTokenBucketRateLimiter(
        policy=policy(),
        clock=clock,
    )

    first = limiter.decide()
    second = limiter.decide()

    assert first.allowed
    assert first.remaining_tokens == Decimal("1")
    assert second.allowed
    assert second.remaining_tokens == Decimal("0")


def test_token_bucket_denies_when_empty_with_retry_after() -> None:
    clock = Clock()
    limiter = GroundedAIServerTokenBucketRateLimiter(
        policy=policy(),
        clock=clock,
    )

    limiter.decide()
    limiter.decide()
    decision = limiter.decide()

    assert not decision.allowed
    assert decision.remaining_tokens == Decimal("0")
    assert decision.retry_after_seconds == Decimal("2")


def test_token_bucket_refills_continuously() -> None:
    clock = Clock()
    limiter = GroundedAIServerTokenBucketRateLimiter(
        policy=policy(),
        clock=clock,
    )

    limiter.decide()
    limiter.decide()

    clock.advance("1")
    denied = limiter.decide()

    assert not denied.allowed
    assert denied.remaining_tokens == Decimal("0.5")
    assert denied.retry_after_seconds == Decimal("1")

    clock.advance("1")
    allowed = limiter.decide()

    assert allowed.allowed
    assert allowed.remaining_tokens == Decimal("0")


def test_token_bucket_refill_is_capped_at_capacity() -> None:
    clock = Clock()
    limiter = GroundedAIServerTokenBucketRateLimiter(
        policy=policy(),
        clock=clock,
    )

    limiter.decide()
    clock.advance("100")

    decision = limiter.decide()

    assert decision.allowed
    assert decision.remaining_tokens == Decimal("1")


def test_rate_limit_decision_serialization_is_explicit() -> None:
    clock = Clock()
    limiter = GroundedAIServerTokenBucketRateLimiter(
        policy=policy(),
        clock=clock,
    )

    limiter.decide()
    limiter.decide()

    assert limiter.decide().to_dict() == {
        "allowed": False,
        "remaining_tokens": "0",
        "retry_after_seconds": "2",
    }


def test_token_bucket_rejects_non_monotonic_clock() -> None:
    clock = Clock()
    limiter = GroundedAIServerTokenBucketRateLimiter(
        policy=policy(),
        clock=clock,
    )

    clock.advance("1")
    limiter.decide()
    clock.value = Decimal("0")

    with pytest.raises(
        ValueError,
        match="monotonic",
    ):
        limiter.decide()


@pytest.mark.parametrize(
    ("capacity", "rate"),
    [
        (0, Decimal("1")),
        (-1, Decimal("1")),
        (1, Decimal("0")),
        (1, Decimal("-1")),
    ],
)
def test_policy_rejects_invalid_values(
    capacity,
    rate,
) -> None:
    with pytest.raises(
        ValueError,
    ):
        GroundedAIServerRateLimitPolicy(
            capacity=capacity,
            refill_tokens_per_second=rate,
        )
