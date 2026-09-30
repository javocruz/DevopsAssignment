import json
import logging
from pathlib import Path

import httpx

from db import get_connection
from intel.news import (
    FixtureNews,
    NoNews,
    TheNewsApi,
    build_news_query,
    fetch_news_for_markets,
    filter_news_before,
    get_news_source,
)
from intel.repo import list_markets, market_ids_with_news, save_markets, save_news_items

NEWS_SAMPLE = json.loads((Path(__file__).parent / "data" / "thenewsapi_sample.json").read_text())
FAKE_TOKEN = "test-token-never-real"


def news_market(market_id):
    return {
        "id": market_id,
        "question": f"Will {market_id} happen?",
        "rules": None,
        "category": None,
        "end_date": "2026-12-31T00:00:00Z",
        "news_query": None,
        "yes_price": 0.5,
        "captured_at": "2026-01-01T00:00:00Z",
        "status": "open",
        "outcome": None,
    }


def counting_api(seen):
    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=NEWS_SAMPLE)

    return TheNewsApi(FAKE_TOKEN, limit=3, timeout=5, transport=httpx.MockTransport(handler))


def test_build_news_query_spec_example():
    question = "Will the ECB cut interest rates at its December 2026 meeting?"
    assert build_news_query(question) == "ecb cut interest rates its"


def test_filter_news_before_drops_future_and_sorts_newest_first():
    items = [
        {"title": "a", "published_at": "2026-09-29T10:00:00Z"},
        {"title": "b", "published_at": "2026-10-02T10:00:00Z"},
        {"title": "c", "published_at": "2026-09-30T10:00:00Z"},
    ]
    kept = filter_news_before(items, "2026-10-01T00:00:00", limit=3)
    assert [item["title"] for item in kept] == ["c", "a"]


def test_filter_news_before_respects_limit():
    items = [{"published_at": f"2026-09-{day:02d}T00:00:00Z"} for day in range(1, 11)]
    kept = filter_news_before(items, "2026-10-01T00:00:00", limit=3)
    assert [item["published_at"][:10] for item in kept] == ["2026-09-10", "2026-09-09", "2026-09-08"]


def test_thenewsapi_sends_spec_params_and_drops_snippet():
    seen = []
    items = counting_api(seen).fetch("m1", "ecb rate cut", "2024-10-22T11:00:03Z")
    params = seen[0].url.params
    assert params["search"] == "ecb rate cut"
    assert params["language"] == "en"
    assert params["published_before"] == "2024-10-22T11:00:03"
    assert params["limit"] == "3"
    assert params["sort"] == "relevance_score"
    assert len(items) == 3
    for item in items:
        assert set(item) == {"title", "description", "source", "url", "published_at"}


def test_token_never_appears_in_logs(tmp_db, caplog):
    def handler(request):
        return httpx.Response(401, json={"error": "invalid token"})

    source = TheNewsApi(FAKE_TOKEN, limit=3, timeout=5, transport=httpx.MockTransport(handler))
    conn = get_connection()
    save_markets(conn, [news_market("m1")])
    # Same setting as app.main(): httpx logs every URL at INFO, and this one
    # carries the token. Everything else is captured down to DEBUG.
    caplog.set_level(logging.WARNING, logger="httpx")
    with caplog.at_level(logging.DEBUG):
        result = fetch_news_for_markets(conn, source, list_markets(conn), max_calls=5)
    conn.close()
    assert result["failed"] == [{"market_id": "m1", "reason": "NewsApiError"}]
    assert caplog.records
    assert FAKE_TOKEN not in caplog.text
    assert FAKE_TOKEN not in json.dumps(result)


def test_call_cap_stops_at_max_calls(tmp_db):
    seen = []
    conn = get_connection()
    save_markets(conn, [news_market(f"m{i}") for i in range(5)])
    result = fetch_news_for_markets(conn, counting_api(seen), list_markets(conn), max_calls=2)
    conn.close()
    assert len(seen) == 2
    assert result["processed"] == 2
    assert result["skipped"] == 3


def test_market_with_news_is_not_fetched_again(tmp_db):
    seen = []
    conn = get_connection()
    save_markets(conn, [news_market("cached"), news_market("fresh")])
    save_news_items(conn, "cached", [{
        "title": "old", "description": None, "source": "x.com",
        "url": "https://x.com/old", "published_at": "2025-12-01T00:00:00Z",
    }], "2025-12-02T00:00:00Z")
    result = fetch_news_for_markets(conn, counting_api(seen), list_markets(conn), max_calls=5)
    assert len(seen) == 1
    assert "search" in seen[0].url.params
    assert result == {"processed": 1, "skipped": 1, "failed": []}
    assert market_ids_with_news(conn) == {"cached", "fresh"}
    conn.close()


def test_saving_same_article_twice_does_not_duplicate(tmp_db):
    conn = get_connection()
    save_markets(conn, [news_market("m1")])
    item = {"title": "t", "description": None, "source": "x.com",
            "url": "https://x.com/a", "published_at": "2025-12-01T00:00:00Z"}
    save_news_items(conn, "m1", [item], "2025-12-02T00:00:00Z")
    save_news_items(conn, "m1", [item], "2025-12-03T00:00:00Z")
    count = conn.execute("SELECT COUNT(*) FROM news_items").fetchone()[0]
    conn.close()
    assert count == 1


def test_fixture_reads_do_not_count_as_api_calls(tmp_db):
    from intel.sources import FixtureSource

    conn = get_connection()
    save_markets(conn, FixtureSource().fetch())
    result = fetch_news_for_markets(conn, FixtureNews(3), list_markets(conn), max_calls=0)
    conn.close()
    assert result["processed"] == len(FixtureSource().fetch())
    assert result["failed"] == []


def test_get_news_source_picks_by_settings(monkeypatch, caplog):
    from config import get_settings

    monkeypatch.setenv("NEWS_SOURCE", "none")
    assert isinstance(get_news_source(get_settings()), NoNews)
    monkeypatch.setenv("NEWS_SOURCE", "fixture")
    assert isinstance(get_news_source(get_settings()), FixtureNews)
    monkeypatch.setenv("NEWS_SOURCE", "thenewsapi")
    monkeypatch.setenv("THENEWSAPI_TOKEN", FAKE_TOKEN)
    assert isinstance(get_news_source(get_settings()), TheNewsApi)
    monkeypatch.setenv("THENEWSAPI_TOKEN", "")
    with caplog.at_level(logging.WARNING):
        assert isinstance(get_news_source(get_settings()), FixtureNews)
    assert "THENEWSAPI_TOKEN is empty" in caplog.text
