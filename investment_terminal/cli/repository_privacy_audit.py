"""
Check whether the repository layout is safe for personal portfolio data.
"""

from pathlib import Path


PERSONAL_FILES = (
    Path("data/portfolios/current_portfolio.json"),
    Path("data/portfolios/portfolio_holdings.csv"),
    Path("data/portfolios/portfolio_quotes.json"),
)

EXAMPLE_FILES = (
    Path("data/portfolios/current_portfolio.example.json"),
    Path("data/portfolios/portfolio_holdings.example.csv"),
    Path("data/portfolios/portfolio_quotes.example.json"),
)


def main() -> None:
    gitignore = Path(".gitignore").read_text(
        encoding="utf-8"
    )

    print()
    print("=" * 88)
    print("Repository Privacy Audit")
    print("=" * 88)

    for path in PERSONAL_FILES:
        ignored = path.as_posix() in gitignore
        print(
            f"{path.as_posix():<58}"
            f"{'IGNORED' if ignored else 'NOT IGNORED'}"
        )

    print("-" * 88)

    for path in EXAMPLE_FILES:
        print(
            f"{path.as_posix():<58}"
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )


if __name__ == "__main__":
    main()