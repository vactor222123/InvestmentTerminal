"""
Database manager.
"""

import sqlite3
from pathlib import Path

from investment_terminal.config.settings import Settings
from investment_terminal.database.schema import SCHEMA


class Database:
    """Manage the SQLite database connection and schema."""

    def __init__(
        self,
        path: str | Path | None = None,
    ) -> None:
        if path is None:
            database_path = Settings.DATABASE_PATH
        else:
            database_path = Path(path)
            database_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
        self.connection = sqlite3.connect(
            database_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self.connection.row_factory = sqlite3.Row

    def initialize(self) -> None:
        """Create database tables when they do not exist."""
        cursor = self.connection.cursor()
        cursor.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        """Close the database connection."""
        self.connection.close()
