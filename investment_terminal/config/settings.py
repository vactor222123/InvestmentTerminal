"""
Application settings.
"""

from pathlib import Path
import os

from dotenv import load_dotenv

from investment_terminal.utils.exceptions import ConfigurationError


class Settings:

    BASE_DIR = Path(__file__).resolve().parents[2]

    load_dotenv(BASE_DIR / ".env")

    DATA_DIR = BASE_DIR / "data"

    OUTPUT_DIR = BASE_DIR / "output"

    LOG_DIR = BASE_DIR / "logs"

    DATABASE_PATH = DATA_DIR / "investment_terminal.db"

    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

    @classmethod
    def validate(cls):

        for directory in (
            cls.DATA_DIR,
            cls.OUTPUT_DIR,
            cls.LOG_DIR,
        ):
            directory.mkdir(exist_ok=True)

        if not cls.FINNHUB_API_KEY:
            raise ConfigurationError(
                "FINNHUB_API_KEY not found in .env"
            )