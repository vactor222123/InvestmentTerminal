from decimal import Decimal

from investment_terminal.ai.providers.retry_delay import (
    GroundedProviderRetryDelayPolicy,
    GroundedProviderRetryDelayService,
)


def policy():
    return GroundedProviderRetryDelayPolicy(
        initial_delay_seconds=Decimal("0.5"),
        multiplier=Decimal("2"),
        maximum_delay_seconds=Decimal("4"),
    )


def test_legacy_delay_seconds_alias_is_preserved() -> None:
    decision = GroundedProviderRetryDelayService().decide(
        policy=policy(),
        retry_number=3,
    )

    assert decision.delay_seconds == Decimal("2.0")
    assert decision.effective_delay_seconds == Decimal("2.0")


def test_legacy_serialization_contract_is_preserved() -> None:
    decision = GroundedProviderRetryDelayService().decide(
        policy=policy(),
        retry_number=3,
    )

    assert decision.to_dict() == {
        "retry_number": 3,
        "delay_seconds": "2.0",
    }
