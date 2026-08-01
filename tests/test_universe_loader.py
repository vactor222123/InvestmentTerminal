"""
Tests for configurable investment-universe loading.
"""

import json
from pathlib import Path

import pytest

from investment_terminal.universe.universe_loader import (
    UniverseLoader,
)
from investment_terminal.universe.universe_models import (
    InvestmentUniverse,
)


def test_universe_normalizes_symbols() -> None:
    universe = InvestmentUniverse(
        name=" Test Universe ",
        symbols=(" msft ", "aapl", "GOOGL"),
    )

    assert universe.name == "Test Universe"
    assert universe.symbols == ("MSFT", "AAPL", "GOOGL")
    assert universe.size == 3
    assert universe.contains(" msft ") is True
    assert universe.contains("META") is False


def test_universe_rejects_duplicate_symbols() -> None:
    with pytest.raises(ValueError, match="unique"):
        InvestmentUniverse(
            name="Invalid",
            symbols=("MSFT", " msft "),
        )


def test_universe_is_json_ready() -> None:
    universe = InvestmentUniverse(
        name="Mega Cap Tech",
        symbols=("MSFT", "AAPL"),
        source_path=Path(
            "data/universes/mega_cap_tech.txt"
        ),
        description="Test universe.",
    )

    payload = universe.to_dict()
    serialized = json.dumps(payload, allow_nan=False)

    assert payload["size"] == 2
    assert payload["symbols"] == ["MSFT", "AAPL"]
    assert payload["source_path"] == (
        "data/universes/mega_cap_tech.txt"
    )
    assert '"Mega Cap Tech"' in serialized


def test_parse_symbols_supports_comments_and_commas() -> None:
    content = """
    # Main symbols
    msft
    AAPL, googl

    META  # inline comment
    NVDA
    """

    assert UniverseLoader.parse_symbols(content) == (
        "MSFT",
        "AAPL",
        "GOOGL",
        "META",
        "NVDA",
    )


def test_parse_symbols_deduplicates_in_order() -> None:
    content = """
    MSFT
    AAPL
    msft
    GOOGL, AAPL
    """

    assert UniverseLoader.parse_symbols(content) == (
        "MSFT",
        "AAPL",
        "GOOGL",
    )


def test_parse_symbols_rejects_empty_content() -> None:
    with pytest.raises(ValueError, match="does not contain"):
        UniverseLoader.parse_symbols("# comments only\n")


def test_load_reads_named_universe(tmp_path) -> None:
    directory = tmp_path / "universes"
    directory.mkdir()

    path = directory / "mega_cap_tech.txt"
    path.write_text("MSFT\nAAPL\nGOOGL\n", encoding="utf-8")

    universe = UniverseLoader(directory).load("mega cap tech")

    assert universe.name == "Mega Cap Tech"
    assert universe.symbols == ("MSFT", "AAPL", "GOOGL")
    assert universe.source_path == path


def test_load_path_supports_custom_metadata(tmp_path) -> None:
    path = tmp_path / "watchlist.txt"
    path.write_text("TSLA\nAMD\n", encoding="utf-8")

    universe = UniverseLoader().load_path(
        path,
        name="My Watchlist",
        description="Personal candidates.",
    )

    assert universe.name == "My Watchlist"
    assert universe.description == "Personal candidates."
    assert universe.symbols == ("TSLA", "AMD")


def test_load_rejects_missing_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        UniverseLoader(tmp_path).load("missing")


def test_load_rejects_wrong_extension(tmp_path) -> None:
    path = tmp_path / "universe.csv"
    path.write_text("MSFT", encoding="utf-8")

    with pytest.raises(ValueError, match=".txt"):
        UniverseLoader().load_path(path)


def test_list_available_returns_sorted_names(tmp_path) -> None:
    directory = tmp_path / "universes"
    directory.mkdir()

    (directory / "watchlist.txt").write_text(
        "MSFT",
        encoding="utf-8",
    )
    (directory / "mega_cap_tech.txt").write_text(
        "AAPL",
        encoding="utf-8",
    )
    (directory / "ignore.csv").write_text(
        "META",
        encoding="utf-8",
    )

    assert UniverseLoader(directory).list_available() == (
        "mega_cap_tech",
        "watchlist",
    )


def test_list_available_returns_empty_for_missing_directory(
    tmp_path,
) -> None:
    assert UniverseLoader(
        tmp_path / "missing"
    ).list_available() == ()