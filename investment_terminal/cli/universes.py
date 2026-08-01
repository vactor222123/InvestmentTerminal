"""
Inspect configured investment universes.
"""

import argparse
from collections.abc import Sequence
from pathlib import Path

from investment_terminal.universe.universe_loader import (
    UniverseLoader,
)


DEFAULT_UNIVERSE_DIRECTORY = (
    Path("data")
    / "universes"
)


def main(
    argv: Sequence[str] | None = None,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(argv)

    loader = UniverseLoader(
        options.directory
    )

    if options.universe is None:
        print_available_universes(
            loader
        )
        return

    universe = loader.load(
        options.universe
    )
    print_universe(
        universe,
        show_symbols=options.symbols,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Build the universe-inspection command-line parser.
    """
    parser = argparse.ArgumentParser(
        description=(
            "List configured investment universes or inspect "
            "one universe in detail."
        ),
    )

    parser.add_argument(
        "--universe",
        help=(
            "Universe name from the configured directory "
            "without the .txt extension."
        ),
    )
    parser.add_argument(
        "--symbols",
        action="store_true",
        help=(
            "Print every symbol when inspecting one universe."
        ),
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=DEFAULT_UNIVERSE_DIRECTORY,
        help=(
            "Directory containing universe .txt files. "
            "Default: %(default)s."
        ),
    )

    return parser


def print_available_universes(
    loader: UniverseLoader,
) -> None:
    """
    Print all configured universe names and sizes.
    """
    available = loader.list_available()

    print()
    print("=" * 72)
    print("Configured Investment Universes")
    print("=" * 72)
    print(
        f"Directory : "
        f"{loader.universe_directory}"
    )
    print(
        f"Available : "
        f"{len(available)}"
    )
    print("-" * 72)

    if not available:
        print(
            "No .txt universe files were found."
        )
        return

    print(
        f"{'Key':<32}"
        f"{'Name':<28}"
        f"{'Symbols':>12}"
    )
    print("-" * 72)

    failed: list[
        tuple[str, str]
    ] = []

    for universe_key in available:
        try:
            universe = loader.load(
                universe_key
            )
        except (
            FileNotFoundError,
            TypeError,
            ValueError,
        ) as exc:
            failed.append(
                (
                    universe_key,
                    str(exc),
                )
            )
            continue

        print(
            f"{universe_key:<32}"
            f"{universe.name:<28}"
            f"{universe.size:>12}"
        )

    if failed:
        print()
        print("Invalid universe files")
        print("-" * 72)

        for universe_key, error in failed:
            print(
                f"- {universe_key}: {error}"
            )


def print_universe(
    universe,
    *,
    show_symbols: bool,
) -> None:
    """
    Print metadata and optionally all symbols for one universe.
    """
    print()
    print("=" * 72)
    print("Investment Universe")
    print("=" * 72)
    print(
        f"Name        : "
        f"{universe.name}"
    )
    print(
        f"Size        : "
        f"{universe.size}"
    )
    print(
        f"Source      : "
        f"{universe.source_path}"
    )

    if universe.description is not None:
        print(
            f"Description : "
            f"{universe.description}"
        )

    if not show_symbols:
        print()
        print(
            "Use --symbols to print all symbols."
        )
        return

    print("-" * 72)
    print("Symbols")
    print("-" * 72)

    for index, symbol in enumerate(
        universe.symbols,
        start=1,
    ):
        print(
            f"{index:>5}. {symbol}"
        )


if __name__ == "__main__":
    main()