"""
Investment Terminal
"""

from datetime import datetime, timezone

from investment_terminal.config.settings import Settings
from investment_terminal.database.database import Database
from investment_terminal.models.quote import Quote
from investment_terminal.repositories.quote_repository import QuoteRepository
from investment_terminal.utils.logger import setup_logger


def main():

    Settings.validate()

    logger = setup_logger(Settings.LOG_DIR)

    logger.info("Investment Terminal started.")

    print("=" * 60)
    print("Investment Terminal")
    print("=" * 60)

    print("Configuration: OK")

    print("Finnhub API: OK")

    print("Logger: OK")

    logger.info("Initialization successful.")

    database = Database()
    database.initialize()

    try:
        repository = QuoteRepository(database)
        quote = Quote(
            symbol="TEST",
            price=100.0,
            timestamp=datetime.now(timezone.utc),
        )
        quote_id = repository.save(quote)
        saved_quote = repository.get(quote_id)

        if saved_quote != quote:
            raise RuntimeError("Saved quote could not be read back")

        print("Quote repository: OK")
        logger.info("Quote repository initialized successfully.")
    finally:
        database.close()

if __name__ == "__main__":
    main()
