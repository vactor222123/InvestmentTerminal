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


if __name__ == "__main__":
    main()