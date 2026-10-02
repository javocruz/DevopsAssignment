from fastapi.testclient import TestClient

from app import app
from book.scoring import brier_score, calibration_buckets
from db import get_connection
from intel.decider import Decision
from intel.repo import save_estimate, save_markets


def test_brier_example_rounds_to_four_decimals():
    score = brier_score([0.8, 0.3, 0.6], [1, 0, 0])
    assert round(score, 4) == 0.1633


def test_brier_empty_is_none():
    assert brier_score([], []) is None


def test_probability_one_goes_in_the_last_bucket():
    buckets = calibration_buckets([1.0, 0.65], [1, 0])
    assert [bucket["range"] for bucket in buckets] == ["0.6-0.7", "0.9-1.0"]
    assert buckets[1]["avg_pred"] == 1.0
    assert buckets[1]["count"] == 1


def market(market_id, yes_price, outcome):
    return {
        "id": market_id,
        "question": "Will it happen?",
        "rules": "Resolves Yes if it happens.",
        "category": "other",
        "end_date": "2026-12-17T00:00:00Z",
        "news_query": None,
        "yes_price": yes_price,
        "captured_at": "2026-10-01T09:00:00Z",
        "status": "resolved" if outcome is not None else "open",
        "outcome": outcome,
    }


def save_one_estimate(conn, market_id, decider_name, context_level, jev_prob):
    snapshot_id = conn.execute(
        "SELECT id FROM price_snapshots WHERE market_id = ?", (market_id,)
    ).fetchone()["id"]
    save_estimate(
        conn, market_id, snapshot_id, decider_name, context_level,
        Decision(jev_prob, 0.5, 0.7, "other"), "{}", "2026-10-02T12:00:00Z",
    )


def test_scorecard_uses_one_decider_and_one_context(tmp_db):
    conn = get_connection()
    save_markets(conn, [
        market("m-yes", 0.62, 1),
        market("m-no", 0.40, 0),
        market("m-open", 0.50, None),
    ])
    save_one_estimate(conn, "m-yes", "stub", "basic", 0.8)
    save_one_estimate(conn, "m-no", "stub", "basic", 0.3)
    save_one_estimate(conn, "m-yes", "jev", "basic", 0.1)
    save_one_estimate(conn, "m-yes", "stub", "news", 0.2)
    save_one_estimate(conn, "m-open", "stub", "basic", 0.99)
    conn.close()

    client = TestClient(app)
    body = client.get("/scorecard?decider=stub&context=basic").json()
    assert body["count"] == 2
    assert body["decider"] == "stub"
    assert body["context_level"] == "basic"
    assert body["jev_brier"] == brier_score([0.8, 0.3], [1, 0])
    assert body["market_brier"] == brier_score([0.62, 0.40], [1, 0])
    assert client.get("/scorecard").json() == body

    rejected = client.get("/scorecard?decider=other&context=basic")
    assert rejected.status_code == 400
