"""
Investment Terminal
"""

from investment_terminal.clients.finnhub_client import FinnhubClient
from investment_terminal.config.settings import Settings
from investment_terminal.database.database import Database
from investment_terminal.repositories.quote_repository import QuoteRepository
from investment_terminal.services.market_data_service import MarketDataService
from investment_terminal.utils.exceptions import APIError
from investment_terminal.utils.logger import setup_logger


def main() -> None:
    """
    Start Investment Terminal and download one live market quote.
    """
    Settings.validate()

    logger = setup_logger(Settings.LOG_DIR)
    logger.info("Investment Terminal started.")

    print("=" * 60)
    print("Investment Terminal")
    print("=" * 60)

    print("Configuration: OK")
    print("Logger: OK")

    database = Database()
    database.initialize()

    try:
        repository = QuoteRepository(database)

        with FinnhubClient.from_settings() as client:
            service = MarketDataService(
                client=client,
                repository=repository,
            )

            result = service.download_and_save_quote(
                symbol="MSFT",
                currency="USD",
            )

        print("Finnhub API: OK")
        print("Database: OK")
        print(f"Downloaded: {result.quote.symbol}")
        print(f"Price: {result.quote.price:.2f} {result.quote.currency}")
        print(f"Timestamp: {result.quote.timestamp.isoformat()}")
        print(f"Saved quote ID: {result.quote_id}")
        print("Read back: OK")

        logger.info(
            "Downloaded and saved %s quote with ID %s.",
            result.quote.symbol,
            result.quote_id,
        )

    except APIError as exc:
        logger.exception("Finnhub operation failed.")
        print(f"Finnhub API: ERROR — {exc}")
        raise
    finally:
        database.close()


if __name__ == "__main__":
    main()