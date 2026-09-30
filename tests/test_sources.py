import json
from pathlib import Path

import httpx

from db import get_connection
from intel.repo import latest_snapshot, list_markets, save_markets
from intel.sources import FixtureSource, PolymarketSource, parse_gamma_market

GAMMA_SAMPLE = json.loads((Path(__file__).parent / "data" / "gamma_sample.json").read_text())

REQUIRED_KEYS = {
    "id", "question", "rules", "category", "end_date",
    "news_query", "yes_price", "captured_at", "status", "outcome",
}


def test_fixture_rows_are_valid():
    rows = FixtureSource().fetch()
    assert 30 <= len(rows) <= 40
    for row in rows:
        assert REQUIRED_KEYS <= row.keys()
        assert 0 < row["yes_price"] < 1
        assert row["outcome"] in {0, 1}


# The look-ahead check on the saved data itself. [:19] cuts both sides to
# YYYY-MM-DDTHH:MM:SS, since the API adds .000000Z and captured_at ends in Z.
def test_fixture_headlines_are_before_captured_at():
    for row in FixtureSource().fetch():
        assert len(row["news"]) == 3
        for headline in row["news"]:
            assert set(headline) == {"title", "description", "source", "url", "published_at"}
            assert headline["published_at"][:19] < row["captured_at"][:19]


def test_saving_twice_does_not_duplicate(tmp_db):
    rows = FixtureSource().fetch()
    conn = get_connection()
    save_markets(conn, rows)
    save_markets(conn, rows)
    assert len(list_markets(conn)) == len(rows)
    snapshots = conn.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0]
    assert snapshots == len(rows)
    conn.close()


def test_latest_snapshot_returns_fixture_price(tmp_db):
    rows = FixtureSource().fetch()
    conn = get_connection()
    save_markets(conn, rows)
    snapshot = latest_snapshot(conn, rows[0]["id"])
    assert snapshot["yes_price"] == rows[0]["yes_price"]
    assert latest_snapshot(conn, "no-such-market") is None
    conn.close()


def test_parse_gamma_sample():
    row = parse_gamma_market(GAMMA_SAMPLE[0])
    assert row["id"] == "559651"
    assert row["yes_price"] == 0.0345
    assert 0 < row["yes_price"] < 1
    assert row["status"] == "open"
    assert row["source"] == "polymarket"
    assert row["news_query"] is None


def test_non_binary_market_is_skipped():
    raw = dict(GAMMA_SAMPLE[0], outcomes='["Yes", "No", "Maybe"]',
               outcomePrices='["0.5", "0.3", "0.2"]')
    assert parse_gamma_market(raw) is None


def test_fetch_uses_mock_transport_not_network():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=GAMMA_SAMPLE)

    source = PolymarketSource(limit=2, timeout=5, transport=httpx.MockTransport(handler))
    result = source.fetch()
    assert len(result["rows"]) == 2
    assert result["failed"] == []
    assert seen[0].url.params["limit"] == "2"
    assert seen[0].url.params["closed"] == "false"


def test_timeout_returns_summary_without_crashing():
    def handler(request):
        raise httpx.TimeoutException("too slow", request=request)

    source = PolymarketSource(limit=2, timeout=5, transport=httpx.MockTransport(handler))
    result = source.fetch()
    assert result["rows"] == []
    assert result["failed"] == [{"market_id": None, "reason": "TimeoutException"}]
