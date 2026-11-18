import json
import logging
import re
from datetime import datetime, timezone

import httpx

from intel.repo import latest_snapshot, market_ids_with_news, save_news_items
from intel.sources import FIXTURE_PATH

logger = logging.getLogger(__name__)

NEWS_ALL_URL = "https://api.thenewsapi.com/v1/news/all"

# These words are in almost every market question, so they add nothing to a
# search and just push the useful words out of the 5-word budget.
STOPWORDS = {
    "will", "the", "a", "an", "of", "in", "on", "at", "by", "to",
    "be", "is", "before", "after", "end", "2025", "2026",
}

# snippet is dropped on purpose: TheNewsAPI cuts it at 60 characters, so
# description is the only text worth showing the decider.
ARTICLE_KEYS = ("title", "description", "source", "url", "published_at")


class NewsApiError(RuntimeError):
    pass


# Pure: text in, text out.
def build_news_query(question, max_words=5):
    cleaned = re.sub(r"[^a-z0-9 ]", " ", question.lower())
    words = [word for word in cleaned.split() if word not in STOPWORDS]
    return " ".join(words[:max_words])


# Pure. The look-ahead guard: it runs even though TheNewsAPI already filters,
# because a bad response or a hand-edited fixture must never leak future news.
def filter_news_before(items, cutoff, limit):
    fresh = [
        item for item in items
        if item.get("published_at") and item["published_at"] < cutoff
    ]
    fresh.sort(key=lambda item: item["published_at"], reverse=True)
    return fresh[:limit]


def keep_article_fields(article):
    return {key: article.get(key) for key in ARTICLE_KEYS}


# TheNewsAPI wants Y-m-d\TH:i:s, so the trailing Z and any fraction go.
def to_published_before(cutoff):
    return datetime.fromisoformat(cutoff).strftime("%Y-%m-%dT%H:%M:%S")


# uses_api tells fetch_news_for_markets whether a fetch costs one of the
# 100 daily calls. Reading the fixture is free, so it never hits the cap.
class NoNews:
    name = "none"
    uses_api = False

    def __init__(self, limit):
        self.limit = limit

    def fetch(self, market_id, query, cutoff):
        return []


class FixtureNews:
    name = "fixture"
    uses_api = False

    def __init__(self, limit):
        self.limit = limit
        self._by_market = None

    # The fixture is read once per source object, not once per market.
    def fetch(self, market_id, query, cutoff):
        if self._by_market is None:
            with open(FIXTURE_PATH) as f:
                self._by_market = {m["id"]: m.get("news", []) for m in json.load(f)}
        return [keep_article_fields(a) for a in self._by_market.get(market_id, [])]


class TheNewsApi:
    name = "thenewsapi"
    uses_api = True

    def __init__(self, token, limit, timeout, transport=None):
        self.token = token
        self.limit = limit
        self.timeout = timeout
        self.transport = transport

    # The token travels in the query string, so the URL never leaves this
    # method: not in a log line, not in an exception message.
    def fetch(self, market_id, query, cutoff):
        params = {
            "api_token": self.token,
            "search": query,
            "language": "en",
            "published_before": to_published_before(cutoff),
            "limit": self.limit,
            "sort": "relevance_score",
        }
        with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
            response = client.get(NEWS_ALL_URL, params=params)
            # Not raise_for_status(): httpx puts the whole URL, token
            # included, into the exception message.
            if response.status_code != 200:
                raise NewsApiError(f"TheNewsAPI answered {response.status_code}")
            payload = response.json()

        articles = []
        for raw in payload.get("data", []):
            # title and url are NOT NULL in news_items.
            if not raw.get("title") or not raw.get("url"):
                continue
            articles.append(keep_article_fields(raw))
        return articles


def get_news_source(settings):
    if settings.news_source == "none":
        return NoNews(settings.news_articles)
    if settings.news_source == "thenewsapi" and settings.thenewsapi_token:
        return TheNewsApi(
            settings.thenewsapi_token,
            settings.news_articles,
            settings.http_timeout,
        )
    if settings.news_source == "thenewsapi":
        logger.warning("NEWS_SOURCE=thenewsapi but THENEWSAPI_TOKEN is empty, using fixture")
    return FixtureNews(settings.news_articles)


# Headlines are cached in news_items, so a market is fetched at most once.
# max_calls is the hard stop on paid calls per run: the free plan gives 100
# a day and one run must never eat all of them.
def fetch_news_for_markets(conn, source, markets, max_calls):
    cached = market_ids_with_news(conn)
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    processed = 0
    skipped = 0
    failed = []
    calls = 0

    for market in markets:
        market_id = market["id"]
        if market_id in cached:
            skipped += 1
            continue
        if source.uses_api and calls >= max_calls:
            skipped += 1
            continue
        snapshot = latest_snapshot(conn, market_id)
        # captured_at is the news cutoff, so no snapshot means no fetch.
        if snapshot is None:
            skipped += 1
            continue

        cutoff = snapshot["captured_at"]
        query = market["news_query"] or build_news_query(market["question"])
        try:
            if source.uses_api:
                calls += 1
            items = source.fetch(market_id, query, cutoff)
        # One failing market is logged and skipped, never crashes the batch.
        # Only the error type is logged, so a leaky message can't print a key.
        except Exception as error:
            logger.warning("News fetch failed for %s: %s", market_id, type(error).__name__)
            failed.append({"market_id": market_id, "reason": type(error).__name__})
            continue

        save_news_items(conn, market_id, filter_news_before(items, cutoff, source.limit), fetched_at)
        processed += 1

    return {"processed": processed, "skipped": skipped, "failed": failed}
