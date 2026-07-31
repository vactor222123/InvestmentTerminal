"""
Database manager.
"""

import sqlite3

from investment_terminal.config.settings import Settings

from investment_terminal.database.schema import SCHEMA


class Database:

    def __init__(self):

        self.connection = sqlite3.connect(
            Settings.DATABASE_PATH
        )

        self.connection.row_factory = sqlite3.Row

    def initialize(self):

        cursor = self.connection.cursor()

        cursor.executescript(SCHEMA)

        self.connection.commit()

    def close(self):

        self.connection.close()