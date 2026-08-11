from decimal import Decimal

import pytest

from investment_terminal.cli.grounded_ai_live import (
    build_argument_parser,
)


def test_retry_delay_flags_are_optional() -> None:
    options = build_argument_parser().parse_args(
        [
            "--live",
            "--request-id", "r1",
            "--query", "Question",
            "--model", "gpt-test",
        ]
    )

    assert options.retry_initial_delay_seconds is None
    assert options.retry_delay_multiplier is None
    assert options.retry_maximum_delay_seconds is None


def test_retry_delay_flags_parse_as_decimals() -> None:
    options = build_argument_parser().parse_args(
        [
            "--live",
            "--request-id", "r1",
            "--query", "Question",
            "--model", "gpt-test",
            "--retry-initial-delay-seconds", "0.5",
            "--retry-delay-multiplier", "2",
            "--retry-maximum-delay-seconds", "4",
        ]
    )

    assert options.retry_initial_delay_seconds == Decimal("0.5")
    assert options.retry_delay_multiplier == Decimal("2")
    assert options.retry_maximum_delay_seconds == Decimal("4")


def test_retry_delay_multiplier_below_one_is_rejected() -> None:
    with pytest.raises(SystemExit):
        build_argument_parser().parse_args(
            [
                "--live",
                "--request-id", "r1",
                "--query", "Question",
                "--model", "gpt-test",
                "--retry-delay-multiplier", "0.5",
            ]
        )


def test_negative_retry_delay_is_rejected() -> None:
    with pytest.raises(SystemExit):
        build_argument_parser().parse_args(
            [
                "--live",
                "--request-id", "r1",
                "--query", "Question",
                "--model", "gpt-test",
                "--retry-initial-delay-seconds", "-1",
            ]
        )
