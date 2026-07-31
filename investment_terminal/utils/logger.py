"""
Application logger.
"""

import logging
from pathlib import Path


def setup_logger(log_directory: Path) -> logging.Logger:
    log_directory.mkdir(exist_ok=True)

    logger = logging.getLogger("InvestmentTerminal")

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler = logging.FileHandler(
        log_directory / "investment_terminal.log",
        encoding="utf-8"
    )

    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()

    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger