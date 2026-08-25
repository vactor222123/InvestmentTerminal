"""
Tests that personal portfolio files are excluded from Git.
"""

from pathlib import Path


def test_personal_portfolio_files_are_gitignored() -> None:
    gitignore = Path(".gitignore").read_text(
        encoding="utf-8"
    )

    required_entries = {
        "data/portfolios/current_portfolio.json",
        "data/portfolios/portfolio_holdings.csv",
        "data/portfolios/portfolio_quotes.json",
        "data/portfolios/portfolio_transactions.csv",
        "output/investment_review_package.json",
    }

    for entry in required_entries:
        assert entry in gitignore


def test_example_portfolio_exists() -> None:
    path = Path(
        "data/portfolios/current_portfolio.example.json"
    )

    assert path.exists()
    assert path.is_file()


def test_example_transaction_csv_exists() -> None:
    path = Path("data/portfolios/portfolio_transactions.example.csv")

    assert path.exists()
    assert path.is_file()
