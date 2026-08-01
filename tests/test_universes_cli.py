"""
Tests for the investment-universe inspection CLI.
"""

from pathlib import Path

from investment_terminal.cli.universes import (
    build_argument_parser,
    main,
)


def create_universe_directory(
    tmp_path: Path,
) -> Path:
    directory = (
        tmp_path
        / "universes"
    )
    directory.mkdir()

    (
        directory
        / "mega_cap_tech.txt"
    ).write_text(
        "MSFT\nAAPL\nGOOGL\n",
        encoding="utf-8",
    )
    (
        directory
        / "watchlist.txt"
    ).write_text(
        "TSLA\nAMD\n",
        encoding="utf-8",
    )

    return directory


def test_parser_uses_default_directory() -> None:
    options = (
        build_argument_parser()
        .parse_args([])
    )

    assert options.universe is None
    assert options.symbols is False
    assert options.directory == Path(
        "data/universes"
    )


def test_main_lists_available_universes(
    tmp_path,
    capsys,
) -> None:
    directory = create_universe_directory(
        tmp_path
    )

    main(
        [
            "--directory",
            str(directory),
        ]
    )

    output = capsys.readouterr().out

    assert (
        "Configured Investment Universes"
        in output
    )
    assert "mega_cap_tech" in output
    assert "watchlist" in output
    assert "Mega Cap Tech" in output
    assert "3" in output
    assert "2" in output


def test_main_inspects_one_universe(
    tmp_path,
    capsys,
) -> None:
    directory = create_universe_directory(
        tmp_path
    )

    main(
        [
            "--directory",
            str(directory),
            "--universe",
            "mega_cap_tech",
        ]
    )

    output = capsys.readouterr().out

    assert "Investment Universe" in output
    assert "Name        : Mega Cap Tech" in output
    assert "Size        : 3" in output
    assert (
        "Use --symbols to print all symbols."
        in output
    )
    assert "1. MSFT" not in output


def test_main_prints_symbols(
    tmp_path,
    capsys,
) -> None:
    directory = create_universe_directory(
        tmp_path
    )

    main(
        [
            "--directory",
            str(directory),
            "--universe",
            "mega_cap_tech",
            "--symbols",
        ]
    )

    output = capsys.readouterr().out

    assert "Symbols" in output
    assert "1. MSFT" in output
    assert "2. AAPL" in output
    assert "3. GOOGL" in output


def test_main_reports_empty_directory(
    tmp_path,
    capsys,
) -> None:
    directory = (
        tmp_path
        / "empty"
    )
    directory.mkdir()

    main(
        [
            "--directory",
            str(directory),
        ]
    )

    output = capsys.readouterr().out

    assert "Available : 0" in output
    assert (
        "No .txt universe files were found."
        in output
    )


def test_main_reports_invalid_universe_file(
    tmp_path,
    capsys,
) -> None:
    directory = (
        tmp_path
        / "universes"
    )
    directory.mkdir()

    (
        directory
        / "valid.txt"
    ).write_text(
        "MSFT\n",
        encoding="utf-8",
    )
    (
        directory
        / "invalid.txt"
    ).write_text(
        "# comments only\n",
        encoding="utf-8",
    )

    main(
        [
            "--directory",
            str(directory),
        ]
    )

    output = capsys.readouterr().out

    assert "valid" in output
    assert "Invalid universe files" in output
    assert "invalid" in output