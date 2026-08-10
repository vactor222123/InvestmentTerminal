from decimal import Decimal

import pytest

from investment_terminal.cli.grounded_ai_live import (
    _pricing_policy,
    build_argument_parser,
)


def test_pricing_flags_are_explicit_and_optional() -> None:
    options = build_argument_parser().parse_args(
        [
            "--live",
            "--request-id", "r1",
            "--query", "Question",
            "--model", "gpt-test",
        ]
    )
    assert options.pricing_currency is None
    assert options.input_cost_per_million is None
    assert options.output_cost_per_million is None


def test_complete_pricing_flags_build_policy_for_requested_model() -> None:
    policy = _pricing_policy(
        model_identity="gpt-test",
        currency="usd",
        input_cost_per_million=Decimal("2.50"),
        output_cost_per_million=Decimal("10.00"),
    )
    assert policy is not None
    entry = policy.require_entry(
        provider_identity="OPENAI",
        model_identity="gpt-test",
    )
    assert entry.currency == "USD"
    assert entry.input_cost_per_million_tokens == Decimal("2.50")
    assert entry.output_cost_per_million_tokens == Decimal("10.00")


@pytest.mark.parametrize(
    "currency,input_cost,output_cost",
    [
        ("USD", Decimal("2.5"), None),
        ("USD", None, Decimal("10")),
        (None, Decimal("2.5"), Decimal("10")),
    ],
)
def test_partial_pricing_configuration_is_rejected(
    currency,
    input_cost,
    output_cost,
) -> None:
    with pytest.raises(
        ValueError,
        match="pricing requires",
    ):
        _pricing_policy(
            model_identity="gpt-test",
            currency=currency,
            input_cost_per_million=input_cost,
            output_cost_per_million=output_cost,
        )


def test_no_pricing_flags_means_no_cost_policy() -> None:
    assert _pricing_policy(
        model_identity="gpt-test",
        currency=None,
        input_cost_per_million=None,
        output_cost_per_million=None,
    ) is None


def test_negative_cli_price_is_rejected() -> None:
    with pytest.raises(SystemExit):
        build_argument_parser().parse_args(
            [
                "--live",
                "--request-id", "r1",
                "--query", "Question",
                "--model", "gpt-test",
                "--input-cost-per-million", "-1",
            ]
        )
