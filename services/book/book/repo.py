import logging

import pymssql

from book.settlement import settle_bet
from book.strategy import compute_edge, entry_price, pick_side, should_bet, size_stake

logger = logging.getLogger(__name__)


def query(conn, sql, params=()):
    cursor = conn.cursor()
    cursor.execute(sql, params)
    return cursor


# estimate_id is UNIQUE, so a second auto-bet inserts nothing.
def insert_open_bet(conn, estimate, side, price, stake, shares, now):
    try:
        cursor = query(conn,
            """
            INSERT INTO bets (
                estimate_id, market_id, decider, context_level, side,
                entry_price, stake, shares, status, placed_at
            ) SELECT %s, %s, %s, %s, %s, %s, %s, %s, 'open', %s
            WHERE NOT EXISTS (SELECT 1 FROM bets WITH (UPDLOCK, HOLDLOCK) WHERE estimate_id = %s)
            """,
            (
                estimate.estimate_id, estimate.market_id, estimate.decider,
                estimate.context_level, side, price, stake, shares, now, estimate.estimate_id,
            ),
        )
    except pymssql.IntegrityError as exc:
        conn.rollback()
        if exc.args[0] in (2601, 2627):
            return False
        raise
    inserted = cursor.rowcount
    conn.commit()
    return inserted == 1


def place_bets(conn, estimates, settings, now):
    processed = 0
    skipped = 0
    failed = []

    for estimate in estimates:
        try:
            edge = compute_edge(estimate.jev_prob, estimate.market_price)
            if not should_bet(edge, estimate.confidence, estimate.info_score, settings):
                skipped += 1
                continue
            side = pick_side(edge)
            price = entry_price(side, estimate.market_price)
            stake = size_stake(edge, settings)
            # Left unrounded. settle_bet is the function that rounds the P&L.
            shares = stake / price
            if insert_open_bet(conn, estimate, side, price, stake, shares, now):
                processed += 1
            else:
                skipped += 1
        # One bad estimate is logged and skipped, never crashes the batch.
        # Only the error type is logged, so a leaky message can't print a key.
        except Exception as error:
            conn.rollback()
            logger.warning("Bet failed for %s: %s", estimate.market_id, type(error).__name__)
            failed.append({"market_id": estimate.market_id, "reason": type(error).__name__})

    return {"processed": processed, "skipped": skipped, "failed": failed}


def list_open_bets(conn):
    rows = query(conn,
        "SELECT * FROM bets WHERE status = 'open' ORDER BY id"
    ).fetchall()
    return [dict(row) for row in rows]


def settle_bets(conn, resolutions, now):
    by_market = {resolution.market_id: resolution for resolution in resolutions}
    processed = 0
    skipped = 0
    failed = []

    for bet in list_open_bets(conn):
        resolution = by_market.get(bet["market_id"])
        # Still open. The market has not resolved, so there is no P&L yet.
        if resolution is None:
            skipped += 1
            continue
        try:
            status, pnl = settle_bet(
                bet["side"], bet["stake"], bet["entry_price"], resolution.outcome
            )
            cursor = query(conn,
                """
                UPDATE bets
                SET status = %s, pnl = %s, settled_at = %s
                WHERE id = %s AND status = 'open'
                """,
                (status, pnl, now, bet["id"]),
            )
            changed = cursor.rowcount
            conn.commit()
            processed += changed
            skipped += 1 - changed
        except Exception as error:
            conn.rollback()
            logger.warning("Settle failed for %s: %s", bet["market_id"], type(error).__name__)
            failed.append({"market_id": bet["market_id"], "reason": type(error).__name__})

    return {"processed": processed, "skipped": skipped, "failed": failed}


def list_bets(conn):
    rows = query(conn, "SELECT * FROM bets ORDER BY id").fetchall()
    return [dict(row) for row in rows]


# Open bets have a null pnl, so they are left out of the sum.
def total_pnl(conn):
    rows = query(conn, "SELECT pnl FROM bets WHERE pnl IS NOT NULL").fetchall()
    if not rows:
        return 0.0
    return round(sum(row["pnl"] for row in rows), 2)
