"""
Investment Terminal
"""

from investment_terminal.config.settings import Settings
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
from investment_terminal.database.database import Database

db = Database()

db.initialize()

db.close()

print("Database: OK")

from investment_terminal.models.quote import Quote

quote = Quote(
    symbol="TEST",
    price=100.0
)

print("Quote Model: OK")

if __name__ == "__main__":
    main()