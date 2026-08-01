"""
Smoke tests for the diversified US large-cap universe.
"""

from pathlib import Path

from investment_terminal.universe.universe_loader import (
    UniverseLoader,
)


UNIVERSE_PATH = (
    Path("data")
    / "universes"
    / "us_large_cap_30.txt"
)


def test_us_large_cap_30_universe_loads() -> None:
    universe = UniverseLoader().load(
        "us_large_cap_30"
    )

    assert universe.name == "Us Large Cap 30"
    assert universe.size == 30
    assert universe.source_path == UNIVERSE_PATH


def test_us_large_cap_30_contains_expected_sectors() -> None:
    universe = UniverseLoader().load(
        "us_large_cap_30"
    )

    expected_symbols = {
        "MSFT",
        "NVDA",
        "JPM",
        "V",
        "LLY",
        "JNJ",
        "WMT",
        "MCD",
        "CAT",
        "XOM",
    }

    assert expected_symbols.issubset(
        set(universe.symbols)
    )


def test_us_large_cap_30_has_unique_symbols() -> None:
    universe = UniverseLoader().load(
        "us_large_cap_30"
    )

    assert len(universe.symbols) == len(
        set(universe.symbols)
    )