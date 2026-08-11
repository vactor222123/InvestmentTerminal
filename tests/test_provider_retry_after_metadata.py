from decimal import Decimal

import pytest

from investment_terminal.ai.providers.http_transport import (
    UrllibGroundedProviderTransport,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransportFailure,
)


def test_retryable_failure_accepts_retry_after_seconds() -> None:
    failure = GroundedProviderTransportFailure(
        kind="RETRYABLE",
        message="rate limited",
        retryable=True,
        retry_after_seconds=Decimal("2.5"),
    )

    assert failure.retry_after_seconds == Decimal("2.5")
    assert failure.to_dict()["retry_after_seconds"] == "2.5"


def test_terminal_failure_cannot_carry_retry_after() -> None:
    with pytest.raises(
        ValueError,
        match="requires a retryable failure",
    ):
        GroundedProviderTransportFailure(
            kind="TERMINAL",
            message="bad request",
            retryable=False,
            retry_after_seconds=Decimal("1"),
        )


@pytest.mark.parametrize(
    "value,expected",
    [
        ("0", Decimal("0")),
        ("1", Decimal("1")),
        ("2.5", Decimal("2.5")),
        (" 3 ", Decimal("3")),
        (None, None),
        ("", None),
        ("abc", None),
        ("-1", None),
    ],
)
def test_retry_after_delta_seconds_parser(
    value,
    expected,
) -> None:
    assert (
        UrllibGroundedProviderTransport
        ._parse_retry_after_delta_seconds(value)
        == expected
    )


def test_http_date_retry_after_is_not_parsed_yet() -> None:
    value = "Wed, 21 Oct 2015 07:28:00 GMT"
    assert (
        UrllibGroundedProviderTransport
        ._parse_retry_after_delta_seconds(value)
        is None
    )


def test_retryable_http_status_propagates_retry_after_metadata() -> None:
    with pytest.raises(
        GroundedProviderTransportFailure,
    ) as captured:
        UrllibGroundedProviderTransport._raise_for_http_status(
            status_code=429,
            body="too many requests",
            retry_after_seconds=Decimal("4"),
        )

    assert captured.value.retryable is True
    assert captured.value.retry_after_seconds == Decimal("4")


def test_terminal_http_status_drops_retry_after_metadata() -> None:
    with pytest.raises(
        GroundedProviderTransportFailure,
    ) as captured:
        UrllibGroundedProviderTransport._raise_for_http_status(
            status_code=400,
            body="bad request",
            retry_after_seconds=Decimal("4"),
        )

    assert captured.value.retryable is False
    assert captured.value.retry_after_seconds is None
