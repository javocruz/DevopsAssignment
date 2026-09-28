import sqlite3
from pathlib import Path

from config import get_settings

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE markets (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    rules TEXT,
    category TEXT,
    end_date TEXT,
    news_query TEXT,
    analyst_notes TEXT,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    outcome INTEGER
);

CREATE TABLE price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL REFERENCES markets(id),
    yes_price REAL NOT NULL,
    captured_at TEXT NOT NULL,
    UNIQUE (market_id, captured_at)
);

CREATE TABLE news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL REFERENCES markets(id),
    title TEXT NOT NULL,
    description TEXT,
    source TEXT,
    url TEXT NOT NULL,
    published_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    UNIQUE (market_id, url)
);

CREATE TABLE estimates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL REFERENCES markets(id),
    snapshot_id INTEGER NOT NULL REFERENCES price_snapshots(id),
    decider TEXT NOT NULL,
    context_level TEXT NOT NULL,
    jev_prob REAL NOT NULL,
    info_score REAL NOT NULL,
    confidence REAL NOT NULL,
    category TEXT,
    state_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (market_id, snapshot_id, decider, context_level)
);

-- Book table. estimate_id and market_id have no FK on purpose: they cross
-- the Intel/Book seam, so the two domains can live in separate DBs in A2.
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
    return Path(get_settings().data_dir) / "edgebook.db"


# Pragmas are per connection, so every new connection has to set them again.
def get_connection():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# One connection per request: FastAPI runs def routes in a thread pool and
# a sqlite3 connection can't be shared across threads.
def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_schema_version(conn):
    return conn.execute("PRAGMA user_version").fetchone()[0]


# CREATE TABLE IF NOT EXISTS would never change an existing table, so a
# version number decides whether the schema needs building or is stale.
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
                "Delete DATA_DIR/edgebook.db or migrate."
            )
    finally:
        conn.close()
