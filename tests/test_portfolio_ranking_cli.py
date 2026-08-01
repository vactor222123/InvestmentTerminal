"""Tests for portfolio-ranking command-line options."""

from pathlib import Path

import pytest

from investment_terminal.cli.portfolio_ranking import (
    DEFAULT_ALLOCATION_CAPITAL,
    DEFAULT_ALLOCATION_PROFILE,
    DEFAULT_CURRENCY,
    DEFAULT_RESOLUTION,
    DEFAULT_UNIVERSE_KEY,
    build_output_path,
    parse_arguments,
    positive_float,
)


def test_parse_arguments_uses_defaults() -> None:
    options = parse_arguments([])

    assert options.universe_key == DEFAULT_UNIVERSE_KEY
    assert options.capital == DEFAULT_ALLOCATION_CAPITAL
    assert options.profile == DEFAULT_ALLOCATION_PROFILE
    assert options.currency == DEFAULT_CURRENCY
    assert options.resolution == DEFAULT_RESOLUTION
    assert options.output_path == Path(
        "output/mega_cap_tech_portfolio.json"
    )


def test_parse_arguments_normalizes_values() -> None:
    options = parse_arguments(
        [
            "--universe",
            "Mega-Cap Tech",
            "--capital",
            "65000",
            "--profile",
            "conservative",
            "--currency",
            "eur",
            "--resolution",
            "w",
        ]
    )

    assert options.universe_key == "mega_cap_tech"
    assert options.capital == 65_000.0
    assert options.profile == "CONSERVATIVE"
    assert options.currency == "EUR"
    assert options.resolution == "W"
    assert options.output_path == Path(
        "output/mega_cap_tech_portfolio.json"
    )


def test_parse_arguments_accepts_custom_output() -> None:
    options = parse_arguments(
        [
            "--output",
            "reports/custom.json",
        ]
    )

    assert options.output_path == Path(
        "reports/custom.json"
    )


def test_parse_arguments_rejects_non_positive_capital() -> None:
    with pytest.raises(SystemExit):
        parse_arguments(
            [
                "--capital",
                "0",
            ]
        )


def test_parse_arguments_rejects_invalid_profile() -> None:
    with pytest.raises(SystemExit):
        parse_arguments(
            [
                "--profile",
                "aggressive",
            ]
        )


def test_parse_arguments_rejects_invalid_resolution() -> None:
    with pytest.raises(SystemExit):
        parse_arguments(
            [
                "--resolution",
                "5m",
            ]
        )


def test_positive_float_rejects_infinity() -> None:
    with pytest.raises(
        Exception,
        match="finite",
    ):
        positive_float("inf")


def test_build_output_path_normalizes_universe_key() -> None:
    assert build_output_path(
        "Mega-Cap Tech"
    ) == Path(
        "output/mega_cap_tech_portfolio.json"
    )