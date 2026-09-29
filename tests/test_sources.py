from db import get_connection
from intel.repo import latest_snapshot, list_markets, save_markets
from intel.sources import FixtureSource

REQUIRED_KEYS = {
    "id", "question", "rules", "category", "end_date",
    "news_query", "yes_price", "captured_at", "status", "outcome",
}


def test_fixture_rows_are_valid():
    rows = FixtureSource().fetch()
    assert len(rows) == 5
    for row in rows:
        assert REQUIRED_KEYS <= row.keys()
        assert 0 < row["yes_price"] < 1
        assert row["outcome"] in {0, 1}


def test_saving_twice_does_not_duplicate(tmp_db):
    rows = FixtureSource().fetch()
    conn = get_connection()
    save_markets(conn, rows)
    save_markets(conn, rows)
    assert len(list_markets(conn)) == 5
    snapshots = conn.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0]
    assert snapshots == 5
    conn.close()


def test_latest_snapshot_returns_fixture_price(tmp_db):
    conn = get_connection()
    save_markets(conn, FixtureSource().fetch())
    snapshot = latest_snapshot(conn, "fx-ecb-cut")
    assert snapshot["yes_price"] == 0.62
    assert latest_snapshot(conn, "no-such-market") is None
    conn.close()
