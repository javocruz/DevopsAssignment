import sqlite3
from pathlib import Path

from book.config import get_settings

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estimate_id INTEGER NOT NULL UNIQUE,
    market_id TEXT NOT NULL,
    decider TEXT NOT NULL,
    context_level TEXT NOT NULL,
    side TEXT NOT NULL,
    entry_price REAL NOT NULL,
    stake REAL NOT NULL,
    shares REAL NOT NULL,
    status TEXT NOT NULL,
    pnl REAL,
    placed_at TEXT NOT NULL,
    settled_at TEXT
);
"""


def db_path():
    return Path(get_settings().data_dir) / "book.db"


def get_connection():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_schema_version(conn):
    return conn.execute("PRAGMA user_version").fetchone()[0]


def init_db():
    Path(get_settings().data_dir).mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        version = get_schema_version(conn)
        if version == 0:
            conn.executescript(SCHEMA_SQL)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            conn.commit()
        elif version != SCHEMA_VERSION:
            raise RuntimeError(
                f"DB schema is v{version}, app expects v{SCHEMA_VERSION}. "
                "Delete DATA_DIR/book.db or migrate."
            )
    finally:
        conn.close()
