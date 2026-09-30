import json

from fastapi.testclient import TestClient

from app import app
from contracts import Estimate
from db import get_connection
from intel.decider import StubDecider
from intel.estimates import build_state, days_to_resolution, render_state, run_estimates
from intel.news import NoNews
from intel.repo import list_estimate_records, list_markets, save_markets, save_news_items

NOW = "2026-10-01T12:00:00Z"
HEADLINE = {
    "title": "ECB's Lane says inflation path on track",
    "description": "Rates could come down again this year.",
    "source": "example.com",
    "url": "https://example.com/lane",
    "published_at": "2026-09-30T08:00:00Z",
}


def estimate_market(market_id):
    return {
        "id": market_id,
        "question": "Will the ECB cut rates in December 2026?",
        "rules": "Resolves Yes if it happens.",
        "category": "economics",
        "end_date": "2026-12-17T00:00:00Z",
        "news_query": None,
        "yes_price": 0.62,
        "captured_at": "2026-10-01T09:00:00Z",
        "status": "resolved",
        "outcome": 1,
    }


def stored_market_and_snapshot(market_id="m1"):
    conn = get_connection()
    save_markets(conn, [estimate_market(market_id)])
    market = list_markets(conn)[0]
    snapshot = conn.execute("SELECT * FROM price_snapshots").fetchone()
    conn.close()
    return market, snapshot


def count_estimates(conn):
    return conn.execute("SELECT COUNT(*) FROM estimates").fetchone()[0]


class FailsOn:
    name = "stub"

    def __init__(self, bad_id):
        self.bad_id = bad_id
        self.stub = StubDecider()

    def decide(self, market_id, state_text, market_price):
        if market_id == self.bad_id:
            raise RuntimeError("decider broke")
        return self.stub.decide(market_id, state_text, market_price)


def test_days_to_resolution_spec_example():
    assert days_to_resolution("2026-12-17T00:00:00Z", "2026-10-01T09:00:00Z") == 77


def test_days_to_resolution_past_end_date_is_zero():
    assert days_to_resolution("2026-09-01T00:00:00Z", "2026-10-01T09:00:00Z") == 0


def test_build_state_never_leaks_outcome_or_price(tmp_db):
    market, snapshot = stored_market_and_snapshot()
    state = build_state(market, snapshot, [HEADLINE], "news")
    for key in ("outcome", "yes_price", "status", "market_id"):
        assert key not in state
    assert "0.62" not in json.dumps(state)


def test_basic_has_no_headlines_and_news_does(tmp_db):
    market, snapshot = stored_market_and_snapshot()
    basic = build_state(market, snapshot, [HEADLINE], "basic")
    news = build_state(market, snapshot, [HEADLINE], "news")
    assert "headlines" not in basic
    assert news["headlines"] == [{
        "title": HEADLINE["title"],
        "description": HEADLINE["description"],
        "published_at": HEADLINE["published_at"],
    }]


def test_render_state_labels_and_headline_line(tmp_db):
    market, snapshot = stored_market_and_snapshot()
    text = render_state(build_state(market, snapshot, [HEADLINE], "news"))
    assert "Market closes: 2026-12-17" in text
    assert "Today: 2026-10-01 (77 days before close)" in text
    assert f"- 2026-09-30: {HEADLINE['title']} | {HEADLINE['description']}" in text
    assert "m1" not in text


def test_running_twice_adds_no_second_row(tmp_db):
    conn = get_connection()
    save_markets(conn, [estimate_market("m1"), estimate_market("m2")])
    first = run_estimates(conn, StubDecider(), NoNews(3), "basic", 20, NOW)
    second = run_estimates(conn, StubDecider(), NoNews(3), "basic", 20, NOW)
    rows = count_estimates(conn)
    conn.close()
    assert first["processed"] == 2
    assert second["processed"] == 0
    assert rows == 2


def test_one_failing_market_does_not_stop_the_batch(tmp_db):
    conn = get_connection()
    save_markets(conn, [estimate_market(f"m{i}") for i in range(3)])
    result = run_estimates(conn, FailsOn("m1"), NoNews(3), "basic", 20, NOW)
    rows = count_estimates(conn)
    conn.close()
    assert result["processed"] == 2
    assert result["failed"] == [{"market_id": "m1", "reason": "RuntimeError"}]
    assert rows == 2


def test_state_json_is_the_dict_with_cached_headlines(tmp_db):
    conn = get_connection()
    save_markets(conn, [estimate_market("m1")])
    save_news_items(conn, "m1", [HEADLINE], NOW)
    run_estimates(conn, StubDecider(), NoNews(3), "news", 20, NOW)
    row = conn.execute("SELECT state_json, created_at FROM estimates").fetchone()
    conn.close()
    state = json.loads(row["state_json"])
    assert state["headlines"][0]["title"] == HEADLINE["title"]
    assert "yes_price" not in state and "outcome" not in state
    assert row["created_at"] == NOW


def test_list_estimate_records_returns_estimates(tmp_db):
    conn = get_connection()
    save_markets(conn, [estimate_market("m1")])
    run_estimates(conn, StubDecider(), NoNews(3), "basic", 20, NOW)
    records = list_estimate_records(conn)
    conn.close()
    assert len(records) == 1
    assert isinstance(records[0], Estimate)
    assert records[0].market_price == 0.62
    assert records[0].question == "Will the ECB cut rates in December 2026?"


def test_run_route_rejects_unknown_context(tmp_db):
    response = TestClient(app).post("/estimates/run?context=everything")
    assert response.status_code == 400
