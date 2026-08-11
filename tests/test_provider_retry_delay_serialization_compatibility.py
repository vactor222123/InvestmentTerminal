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


def test_original_decision_serialization_contract_is_exactly_preserved() -> None:
    decision = GroundedProviderRetryDelayService().decide(
        policy=policy(),
        retry_number=3,
    )

    assert decision.delay_seconds == Decimal("2.0")
    assert decision.to_dict() == {
        "retry_number": 3,
        "delay_seconds": "2.0",
    }


def test_precedence_details_remain_available_as_typed_attributes() -> None:
    decision = GroundedProviderRetryDelayService().decide(
        policy=policy(),
        retry_number=2,
        provider_retry_after_seconds=Decimal("5"),
    )

    assert decision.policy_delay_seconds == Decimal("1.0")
    assert decision.provider_retry_after_seconds == Decimal("5")
    assert decision.effective_delay_seconds == Decimal("5")
    assert decision.delay_seconds == Decimal("5")
