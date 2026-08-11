from decimal import Decimal

import pytest

from investment_terminal.ai.providers.composition import (
    _retry_delay_policy,
)


def test_no_retry_delay_configuration_keeps_zero_delay_path() -> None:
    assert _retry_delay_policy(
        initial_delay_seconds=None,
        multiplier=None,
        maximum_delay_seconds=None,
    ) is None


def test_complete_retry_delay_configuration_builds_policy() -> None:
    policy = _retry_delay_policy(
        initial_delay_seconds=Decimal("0.5"),
        multiplier=Decimal("2"),
        maximum_delay_seconds=Decimal("4"),
    )

    assert policy is not None
    assert policy.delay_for_retry(
        retry_number=1
    ) == Decimal("0.5")
    assert policy.delay_for_retry(
        retry_number=4
    ) == Decimal("4")


@pytest.mark.parametrize(
    "initial,multiplier,maximum",
    [
        (Decimal("0.5"), None, Decimal("4")),
        (None, Decimal("2"), Decimal("4")),
        (Decimal("0.5"), Decimal("2"), None),
    ],
)
def test_partial_retry_delay_configuration_is_rejected(
    initial,
    multiplier,
    maximum,
) -> None:
    with pytest.raises(
        ValueError,
        match="requires initial delay",
    ):
        _retry_delay_policy(
            initial_delay_seconds=initial,
            multiplier=multiplier,
            maximum_delay_seconds=maximum,
        )
