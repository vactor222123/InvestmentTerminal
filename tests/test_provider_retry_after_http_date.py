from datetime import datetime, timezone
from decimal import Decimal

import pytest

from investment_terminal.ai.providers.clock import (
    GroundedProviderClock,
)
from investment_terminal.ai.providers.http_transport import (
    UrllibGroundedProviderTransport,
)


class FixedClock(
    GroundedProviderClock
):
    def __init__(
        self,
        now: datetime,
    ) -> None:
        self._now = now

    def now_utc(self) -> datetime:
        return self._now


def transport_at(
    value: datetime,
) -> UrllibGroundedProviderTransport:
    return UrllibGroundedProviderTransport(
        clock=FixedClock(value)
    )


def test_http_date_retry_after_is_converted_to_seconds() -> None:
    transport = transport_at(
        datetime(
            2015,
            10,
            21,
            7,
            27,
            55,
            tzinfo=timezone.utc,
        )
    )

    assert transport._parse_retry_after(
        "Wed, 21 Oct 2015 07:28:00 GMT"
    ) == Decimal("5.0")


def test_past_http_date_retry_after_becomes_zero() -> None:
    transport = transport_at(
        datetime(
            2015,
            10,
            21,
            7,
            28,
            5,
            tzinfo=timezone.utc,
        )
    )

    assert transport._parse_retry_after(
        "Wed, 21 Oct 2015 07:28:00 GMT"
    ) == Decimal("0.0")


def test_delta_seconds_still_take_precedence_over_date_parsing() -> None:
    transport = transport_at(
        datetime(
            2015,
            10,
            21,
            7,
            28,
            5,
            tzinfo=timezone.utc,
        )
    )

    assert transport._parse_retry_after(
        "2.5"
    ) == Decimal("2.5")


def test_malformed_retry_after_returns_none() -> None:
    transport = transport_at(
        datetime(
            2015,
            10,
            21,
            7,
            28,
            5,
            tzinfo=timezone.utc,
        )
    )

    assert transport._parse_retry_after(
        "not-a-date"
    ) is None


def test_naive_clock_value_is_rejected() -> None:
    transport = transport_at(
        datetime(
            2015,
            10,
            21,
            7,
            28,
            5,
        )
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware UTC",
    ):
        transport._parse_retry_after(
            "Wed, 21 Oct 2015 07:28:10 GMT"
        )


def test_invalid_clock_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="GroundedProviderClock",
    ):
        UrllibGroundedProviderTransport(
            clock=object(),  # type: ignore[arg-type]
        )
