import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Anchored to this file, not the shell's current folder, so tests and
# python app.py find the fixture from anywhere.
FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "resolved_markets.json"

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"


class FixtureSource:
    def fetch(self):
        with open(FIXTURE_PATH) as f:
            return json.load(f)


# Gamma sends outcomes and outcomePrices as JSON text, e.g. '["Yes","No"]'
# and '["0.62","0.38"]', so both need json.loads before we can use them.
def parse_gamma_market(raw):
    try:
        outcomes = json.loads(raw["outcomes"])
        prices = [float(p) for p in json.loads(raw["outcomePrices"])]
    except (KeyError, TypeError, ValueError):
        return None
    if sorted(outcomes) != ["No", "Yes"] or len(prices) != 2:
        return None
    if not raw.get("question"):
        return None
    closed = bool(raw.get("closed"))
    return {
        "id": str(raw["id"]),
        "question": raw["question"],
        "rules": raw.get("description"),
        "category": raw.get("category"),
        "end_date": raw.get("endDate"),
        "news_query": None,
        "yes_price": prices[outcomes.index("Yes")],
        "captured_at": raw.get("updatedAt"),
        "status": "resolved" if closed else "open",
        "outcome": None,
        "source": "polymarket",
    }


class PolymarketSource:
    def __init__(self, limit, timeout, transport=None):
        self.limit = limit
        self.timeout = timeout
        self.transport = transport

    # Returns a summary instead of raising, so one bad call never crashes
    # a sync. The URL is never logged.
    def fetch(self):
        params = {"limit": self.limit, "closed": "false"}
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.get(GAMMA_MARKETS_URL, params=params)
                response.raise_for_status()
                raw_markets = response.json()
        except httpx.HTTPError as error:
            logger.warning("Polymarket fetch failed: %s", type(error).__name__)
            return {"rows": [], "skipped": 0,
                    "failed": [{"market_id": None, "reason": type(error).__name__}]}

        rows = []
        skipped = 0
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for raw in raw_markets:
            row = parse_gamma_market(raw)
            if row is None:
                skipped += 1
                continue
            if not row["captured_at"]:
                row["captured_at"] = now
            rows.append(row)
        return {"rows": rows, "skipped": skipped, "failed": []}


def get_source(settings):
    if settings.market_source == "polymarket":
        return PolymarketSource(settings.polymarket_limit, settings.http_timeout)
    return FixtureSource()
