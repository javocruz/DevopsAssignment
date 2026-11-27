import pymssql

from intel.contracts import Estimate, Resolution


def query(conn, sql, params=()):
    cursor = conn.cursor()
    cursor.execute(sql, params)
    return cursor


def insert_once(conn, sql, params):
    try:
        return query(conn, sql, params).rowcount
    except pymssql.IntegrityError as exc:
        if exc.args[0] in (2601, 2627):
            return 0
        raise


def save_markets(conn, rows):
    inserted = 0
    for row in rows:
        inserted += insert_once(
            conn,
            """
            INSERT INTO markets
                (id, question, rules, category, end_date, news_query,
                 analyst_notes, source, status, outcome)
            SELECT %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM markets WITH (UPDLOCK, HOLDLOCK)
                WHERE id = %s
            )
            """,
            (
                row["id"], row["question"], row["rules"], row["category"],
                row["end_date"], row["news_query"],
                row.get("source", "fixture"), row["status"], row["outcome"],
                row["id"],
            ),
        )
        insert_once(
            conn,
            """
            INSERT INTO price_snapshots (market_id, yes_price, captured_at)
            SELECT %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM price_snapshots WITH (UPDLOCK, HOLDLOCK)
                WHERE market_id = %s AND captured_at = %s
            )
            """,
            (row["id"], row["yes_price"], row["captured_at"], row["id"], row["captured_at"]),
        )
    conn.commit()
    return inserted


def list_markets(conn):
    return query(conn, "SELECT * FROM markets ORDER BY id").fetchall()


def get_market(conn, market_id):
    return query(conn, "SELECT * FROM markets WHERE id = %s", (market_id,)).fetchone()


def latest_snapshot(conn, market_id):
    return query(
        conn,
        """
        SELECT TOP (1) * FROM price_snapshots
        WHERE market_id = %s
        ORDER BY captured_at DESC
        """,
        (market_id,),
    ).fetchone()


# The cache key is (market_id, url), so the same article is never stored
# twice and a re-run costs no API calls.
def save_news_items(conn, market_id, items, fetched_at):
    for item in items:
        insert_once(
            conn,
            """
            INSERT INTO news_items
                (market_id, title, description, source, url, published_at, fetched_at)
            SELECT %s, %s, %s, %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM news_items WITH (UPDLOCK, HOLDLOCK)
                WHERE market_id = %s AND url_hash = HASHBYTES('SHA2_256', CONVERT(NVARCHAR(MAX), %s))
            )
            """,
            (
                market_id, item["title"], item.get("description"),
                item.get("source"), item["url"], item["published_at"], fetched_at,
                market_id, item["url"],
            ),
        )
    conn.commit()


# One query for the whole batch instead of one COUNT per market.
def market_ids_with_news(conn):
    rows = query(conn, "SELECT DISTINCT market_id FROM news_items").fetchall()
    return {row["market_id"] for row in rows}


def list_news_items(conn, market_id):
    rows = query(
        conn,
        """
        SELECT title, description, published_at FROM news_items
        WHERE market_id = %s
        """,
        (market_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def estimate_exists(conn, market_id, snapshot_id, decider_name, context_level):
    row = query(
        conn,
        """
        SELECT id FROM estimates
        WHERE market_id = %s AND snapshot_id = %s AND decider = %s AND context_level = %s
        """,
        (market_id, snapshot_id, decider_name, context_level),
    ).fetchone()
    return row is not None


# UNIQUE (market_id, snapshot_id, decider, context_level) makes a second
# save for the same key a no-op.
def save_estimate(conn, market_id, snapshot_id, decider_name, context_level,
                  decision, state_json, created_at):
    insert_once(
        conn,
        """
        INSERT INTO estimates
            (market_id, snapshot_id, decider, context_level, jev_prob,
             info_score, confidence, category, state_json, created_at)
        SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        WHERE NOT EXISTS (
            SELECT 1 FROM estimates WITH (UPDLOCK, HOLDLOCK)
            WHERE market_id = %s AND snapshot_id = %s AND decider = %s AND context_level = %s
        )
        """,
        (
            market_id, snapshot_id, decider_name, context_level, decision.jev_prob,
            decision.info_score, decision.confidence, decision.category,
            state_json, created_at,
            market_id, snapshot_id, decider_name, context_level,
        ),
    )
    conn.commit()


# market_price is the snapshot the estimate was made at, not the latest one,
# so Book compares Jev against the price he could actually have bet on.
def list_estimate_records(conn):
    rows = query(
        conn,
        """
        SELECT e.id, e.market_id, m.question, s.yes_price, e.jev_prob,
               e.info_score, e.confidence, e.decider, e.context_level, e.created_at
        FROM estimates e
        JOIN markets m ON m.id = e.market_id
        JOIN price_snapshots s ON s.id = e.snapshot_id
        ORDER BY e.id
        """
    ).fetchall()
    return [
        Estimate(
            estimate_id=row["id"],
            market_id=row["market_id"],
            question=row["question"],
            market_price=row["yes_price"],
            jev_prob=row["jev_prob"],
            info_score=row["info_score"],
            confidence=row["confidence"],
            decider=row["decider"],
            context_level=row["context_level"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_estimate_detail(conn, estimate_id):
    return query(
        conn,
        """
        SELECT e.id, e.market_id, m.question, s.yes_price, e.jev_prob,
               e.info_score, e.confidence, e.decider, e.context_level,
               e.created_at, e.state_json
        FROM estimates e
        JOIN markets m ON m.id = e.market_id
        JOIN price_snapshots s ON s.id = e.snapshot_id
        WHERE e.id = %s
        """,
        (estimate_id,),
    ).fetchone()


# markets has no resolved_at column, so end_date stands in for it.
def list_resolutions(conn):
    rows = query(
        conn,
        """
        SELECT id, outcome, end_date FROM markets
        WHERE outcome IS NOT NULL
        ORDER BY id
        """
    ).fetchall()
    return [
        Resolution(market_id=row["id"], outcome=row["outcome"], resolved_at=row["end_date"])
        for row in rows
    ]
