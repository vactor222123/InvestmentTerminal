from decimal import Decimal

import pytest

from investment_terminal.ai.providers.retry_delay import (
    GroundedProviderRetryDelayPolicy,
    GroundedProviderRetryDelayService,
)


def policy() -> GroundedProviderRetryDelayPolicy:
    return GroundedProviderRetryDelayPolicy(
        initial_delay_seconds=Decimal("0.5"),
        multiplier=Decimal("2"),
        maximum_delay_seconds=Decimal("4"),
    )


@pytest.mark.parametrize(
    "retry_number,expected",
    [
        (1, Decimal("0.5")),
        (2, Decimal("1.0")),
        (3, Decimal("2.0")),
        (4, Decimal("4.0")),
        (5, Decimal("4.0")),
        (10, Decimal("4.0")),
    ],
)
def test_exponential_delay_is_deterministic_and_bounded(
    retry_number,
    expected,
) -> None:
    assert policy().delay_for_retry(
        retry_number=retry_number
    ) == expected


def test_retry_delay_service_returns_explicit_decision() -> None:
    decision = GroundedProviderRetryDelayService().decide(
        policy=policy(),
        retry_number=3,
    )

    assert decision.retry_number == 3
    assert decision.delay_seconds == Decimal("2.0")
    assert decision.to_dict() == {
        "retry_number": 3,
        "delay_seconds": "2.0",
    }


def test_zero_delay_policy_is_supported() -> None:
    zero = GroundedProviderRetryDelayPolicy(
        initial_delay_seconds=Decimal("0"),
        multiplier=Decimal("1"),
        maximum_delay_seconds=Decimal("0"),
    )
    assert zero.delay_for_retry(
        retry_number=50
    ) == Decimal("0")


def test_invalid_retry_number_is_rejected() -> None:
    for value in (0, -1, True):
        with pytest.raises(ValueError):
            policy().delay_for_retry(
                retry_number=value
            )


def test_multiplier_below_one_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="multiplier",
    ):
        GroundedProviderRetryDelayPolicy(
            initial_delay_seconds=Decimal("1"),
            multiplier=Decimal("0.5"),
            maximum_delay_seconds=Decimal("10"),
        )


def test_maximum_below_initial_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="maximum_delay_seconds",
    ):
        GroundedProviderRetryDelayPolicy(
            initial_delay_seconds=Decimal("2"),
            multiplier=Decimal("2"),
            maximum_delay_seconds=Decimal("1"),
        )


def test_serialization_uses_decimal_strings() -> None:
    assert policy().to_dict() == {
        "initial_delay_seconds": "0.5",
        "multiplier": "2",
        "maximum_delay_seconds": "4",
    }


def test_policy_contains_no_sleep_jitter_or_retry_after_semantics() -> None:
    data = str(policy().to_dict()).lower()
    for forbidden in (
        "sleep",
        "jitter",
        "retry-after",
        "retry_after",
        "header",
        "clock",
    ):
        assert forbidden not in data
