from decimal import Decimal

from investment_terminal.server.rate_limit_admission import (
    GroundedAIServerRateLimitAdmissionService,
)
from investment_terminal.server.rate_limit_identity import (
    GroundedAIServerRateLimitIdentityDeriver,
)
from investment_terminal.server.rate_limits import (
    GroundedAIServerRateLimitPolicy,
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


def service(
    clock: Clock,
) -> GroundedAIServerRateLimitAdmissionService:
    return GroundedAIServerRateLimitAdmissionService(
        policy=GroundedAIServerRateLimitPolicy(
            capacity=1,
            refill_tokens_per_second=Decimal("1"),
        ),
        clock=clock,
    )


def identity(
    raw: str,
):
    return GroundedAIServerRateLimitIdentityDeriver().derive(
        raw
    )


def test_admission_is_scoped_per_opaque_identity() -> None:
    clock = Clock()
    admission = service(
        clock
    )

    first = identity(
        "key-one"
    )
    second = identity(
        "key-two"
    )

    assert admission.decide(
        identity=first
    ).allowed
    assert not admission.decide(
        identity=first
    ).allowed

    assert admission.decide(
        identity=second
    ).allowed
    assert admission.identity_count == 2


def test_admission_refills_each_identity_independently() -> None:
    clock = Clock()
    admission = service(
        clock
    )
    first = identity(
        "key-one"
    )

    assert admission.decide(
        identity=first
    ).allowed
    assert not admission.decide(
        identity=first
    ).allowed

    clock.advance(
        "1"
    )

    assert admission.decide(
        identity=first
    ).allowed


def test_raw_secret_is_not_present_in_admission_state_repr() -> None:
    clock = Clock()
    admission = service(
        clock
    )
    raw = "super-secret-api-key"

    opaque = identity(
        raw
    )
    admission.decide(
        identity=opaque
    )

    assert raw not in repr(
        admission._limiters
    )
    assert str(
        opaque
    ) in repr(
        admission._limiters
    )
