"""
Investment Terminal
Main entry point.
"""

from investment_terminal.config.settings import FINNHUB_API_KEY


def main() -> None:
    print("=" * 50)
    print("Investment Terminal")
    print("=" * 50)
    print(f"Finnhub API: {'OK' if FINNHUB_API_KEY else 'Missing'}")


if __name__ == "__main__":
    main()