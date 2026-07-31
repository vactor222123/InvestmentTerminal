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

CREATE TABLE IF NOT EXISTS candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    resolution TEXT NOT NULL,
    timestamp TEXT NOT NULL,

    open_price REAL NOT NULL,
    high_price REAL NOT NULL,
    low_price REAL NOT NULL,
    close_price REAL NOT NULL,

    volume REAL NOT NULL,
    currency TEXT NOT NULL,

    UNIQUE(symbol, resolution, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_candles_symbol_resolution_timestamp
ON candles(symbol, resolution, timestamp);
"""