"""
Global application settings.
"""

from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"

for directory in (DATA_DIR, OUTPUT_DIR, LOG_DIR):
    directory.mkdir(exist_ok=True)

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

if not FINNHUB_API_KEY:
    raise RuntimeError("FINNHUB_API_KEY is missing in .env")