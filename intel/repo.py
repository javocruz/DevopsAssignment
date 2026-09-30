# INSERT OR IGNORE plus the UNIQUE keys make every save idempotent:
# syncing the same markets twice changes nothing the second time.
def save_markets(conn, rows):
    for row in rows:
        conn.execute(
            """
            INSERT OR IGNORE INTO markets
                (id, question, rules, category, end_date, news_query,
                 analyst_notes, source, status, outcome)
            VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
            """,
            (
                row["id"], row["question"], row["rules"], row["category"],
                row["end_date"], row["news_query"],
                row.get("source", "fixture"), row["status"], row["outcome"],
            ),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO price_snapshots (market_id, yes_price, captured_at)
            VALUES (?, ?, ?)
            """,
            (row["id"], row["yes_price"], row["captured_at"]),
        )
    conn.commit()


def list_markets(conn):
    return conn.execute("SELECT * FROM markets ORDER BY id").fetchall()


def latest_snapshot(conn, market_id):
    return conn.execute(
        """
        SELECT * FROM price_snapshots
        WHERE market_id = ?
        ORDER BY captured_at DESC
        LIMIT 1
        """,
        (market_id,),
    ).fetchone()


# The cache key is (market_id, url), so the same article is never stored
# twice and a re-run costs no API calls.
def save_news_items(conn, market_id, items, fetched_at):
    for item in items:
        conn.execute(
            """
            INSERT OR IGNORE INTO news_items
                (market_id, title, description, source, url, published_at, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                market_id, item["title"], item.get("description"),
                item.get("source"), item["url"], item["published_at"], fetched_at,
            ),
        )
    conn.commit()


# One query for the whole batch instead of one COUNT per market.
def market_ids_with_news(conn):
    rows = conn.execute("SELECT DISTINCT market_id FROM news_items").fetchall()
    return {row["market_id"] for row in rows}

