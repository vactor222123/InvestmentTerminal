"""
SQLite schema.
"""

SCHEMA = """

CREATE TABLE IF NOT EXISTS quotes (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    symbol TEXT NOT NULL,

    price REAL NOT NULL,

    currency TEXT,

    timestamp TEXT NOT NULL

);

"""