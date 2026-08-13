from decimal import Decimal

import pytest

from investment_terminal.server.rate_limit_clock import (
    GroundedAIServerMonotonicDecimalClock,
)


def test_monotonic_clock_returns_decimal_without_binary_float_artifacts() -> None:
    clock = GroundedAIServerMonotonicDecimalClock(
        monotonic_source=lambda: 12.5,
    )

    assert clock() == Decimal("12.5")


def test_monotonic_clock_rejects_invalid_source_result() -> None:
    clock = GroundedAIServerMonotonicDecimalClock(
        monotonic_source=lambda: "bad",
    )

    with pytest.raises(
        TypeError,
        match="int or float",
    ):
        clock()
