"""Dev-only. Run by hand to rebuild fixtures/resolved_markets.json.

    python scripts/build_fixture.py --dry-run   # Polymarket only, free
    python scripts/build_fixture.py             # also spends news calls

One market costs one TheNewsAPI call, and the free plan gives 100 a day.
So every finished market is appended to the file as soon as it succeeds and
ids already in the file are skipped: a crash never spends the budget twice.

All the free work (markets, prices) happens before the first news call, so a
market that fails on its price never wastes one.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings  # noqa: E402
from intel.news import TheNewsApi, build_news_query, filter_news_before  # noqa: E402
from intel.sources import FIXTURE_PATH, GAMMA_MARKETS_URL  # noqa: E402

PRICES_HISTORY_URL = "https://clob.polymarket.com/prices-history"

TARGET_MARKETS = 35
MAX_NEWS_CALLS = 45
HEADLINES_PER_MARKET = 3

# Markets are ranked by volume, so the most traded ones come first: they are
# the ones the news actually wrote about.
CANDIDATE_PAGES = 6
PAGE_SIZE = 100

# How far before the close the snapshot price is taken. A closed market's
# outcomePrices is the resolution (0 or 1), never a usable snapshot.
SNAPSHOT_DAYS_BEFORE_END = 14
SNAPSHOT_WINDOW_DAYS = 3
PRICE_FIDELITY_MINUTES = 60

# build_news_query keeps the first 5 non-stopwords, which is wrong for some
# questions. These are the hand-written replacements, listed in
# docs/context/08-decisions.md.
HAND_QUERIES = {
    "253642": "republican presidential nominee 2024",
    "253641": "democratic presidential nominee 2024",
    "512340": "ciuca romania presidential election",
    "546814": "zelenskyy suit",
    "2270330": "us iran peace deal",
    "1706788": "us iran ceasefire",
    "680392": "government shutdown",
    "1180303": "khamenei supreme leader",
    "507242": "pennsylvania presidential polls",
    "529278": "fitzgerald irish presidential election",
    "601697": "fed interest rate decision",
    "601700": "fed interest rate decision",
    "654415": "fed interest rate decision",
    "570360": "fed interest rate decision",
    "504494": "fed interest rate decision",
    "570363": "fed interest rate decision",
}


# Rows without a "news" list are the 5 handmade C5 markets. They are dropped
# so the rebuilt file only holds real Polymarket markets.
def load_fixture():
    if not FIXTURE_PATH.exists():
        return []
    rows = json.loads(FIXTURE_PATH.read_text())
    return [row for row in rows if "news" in row]


def write_fixture(rows):
    FIXTURE_PATH.write_text(json.dumps(rows, indent=2) + "\n")


def gamma_closed_markets(client, offset):
    params = {
        "limit": PAGE_SIZE,
        "offset": offset,
        "closed": "true",
        "order": "volumeNum",
        "ascending": "false",
    }
    response = client.get(GAMMA_MARKETS_URL, params=params)
    response.raise_for_status()
    return response.json()


# A closed binary market only qualifies if its final prices are a clean 1/0:
# that pair IS the resolution, and it tells us the outcome.
def candidate(raw):
    try:
        outcomes = json.loads(raw["outcomes"])
        prices = [float(p) for p in json.loads(raw["outcomePrices"])]
        tokens = json.loads(raw["clobTokenIds"])
    except (KeyError, TypeError, ValueError):
        return None
    if sorted(outcomes) != ["No", "Yes"] or len(prices) != 2 or len(tokens) != 2:
        return None
    if not raw.get("question") or not raw.get("endDate") or not raw.get("startDate"):
        return None

    yes_index = outcomes.index("Yes")
    final_yes = prices[yes_index]
    if final_yes not in (0.0, 1.0):
        return None
    return {
        "id": str(raw["id"]),
        "question": raw["question"],
        "rules": raw.get("description"),
        "category": raw.get("category"),
        "end_date": raw["endDate"],
        "start_date": raw["startDate"],
        "yes_token": tokens[yes_index],
        "outcome": int(final_yes),
    }


def parse_time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def as_utc_text(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Asks the CLOB for the Yes token's price history in a short window that ends
# SNAPSHOT_DAYS_BEFORE_END before the close, then takes the newest point that
# is still a real probability. 0 or 1 would be the resolution leaking in.
def snapshot_before_resolution(client, row):
    end = parse_time(row["end_date"])
    start = parse_time(row["start_date"])
    target = max(end - timedelta(days=SNAPSHOT_DAYS_BEFORE_END),
                 start + timedelta(hours=12))
    if target >= end:
        return None

    params = {
        "market": row["yes_token"],
        "startTs": int((target - timedelta(days=SNAPSHOT_WINDOW_DAYS)).timestamp()),
        "endTs": int(target.timestamp()),
        "fidelity": PRICE_FIDELITY_MINUTES,
    }
    response = client.get(PRICES_HISTORY_URL, params=params)
    response.raise_for_status()
    history = response.json().get("history", [])

    for point in reversed(history):
        price = float(point["p"])
        if 0 < price < 1:
            captured = datetime.fromtimestamp(int(point["t"]), tz=timezone.utc)
            return round(price, 4), as_utc_text(captured)
    return None


# Exactly HEADLINES_PER_MARKET headlines, all published before captured_at.
# filter_news_before is the guard: the API already filters, but the fixture
# is what the tests trust.
def three_headlines(news, row):
    items = news.fetch(row["id"], row["news_query"], row["captured_at"])
    kept = filter_news_before(items, row["captured_at"], HEADLINES_PER_MARKET)
    if len(kept) < HEADLINES_PER_MARKET:
        return None
    return kept


def collect_candidates(client, already_have):
    seen_questions = set()
    rows = []
    for page in range(CANDIDATE_PAGES):
        for raw in gamma_closed_markets(client, page * PAGE_SIZE):
            row = candidate(raw)
            if row is None or row["id"] in already_have:
                continue
            if row["question"] in seen_questions:
                continue
            seen_questions.add(row["question"])
            rows.append(row)
    return rows


def priced_candidates(client, candidates, wanted):
    rows = []
    for row in candidates:
        if len(rows) >= wanted:
            break
        try:
            priced = snapshot_before_resolution(client, row)
        except httpx.HTTPError as error:
            print(f"  price failed {row['id']}: {type(error).__name__}")
            continue
        if priced is None:
            continue
        row["yes_price"], row["captured_at"] = priced
        row["news_query"] = HAND_QUERIES.get(row["id"]) or build_news_query(row["question"])
        rows.append(row)
    return rows


def fixture_row(row, headlines):
    return {
        "id": row["id"],
        "question": row["question"],
        "rules": row["rules"],
        "category": row["category"],
        "end_date": row["end_date"],
        "news_query": row["news_query"],
        "yes_price": row["yes_price"],
        "captured_at": row["captured_at"],
        "status": "resolved",
        "outcome": row["outcome"],
        "news": headlines,
    }


def main():
    dry_run = "--dry-run" in sys.argv
    settings = get_settings()
    if not dry_run and not settings.thenewsapi_token:
        raise SystemExit("THENEWSAPI_TOKEN is empty, refusing to run")

    fixture = load_fixture()
    already_have = {row["id"] for row in fixture}
    print(f"fixture has {len(fixture)} markets")

    with httpx.Client(timeout=settings.http_timeout) as client:
        candidates = collect_candidates(client, already_have)
        print(f"{len(candidates)} closed binary candidates")
        # Ask for more than we need: some will not yield 3 headlines.
        wanted = min(MAX_NEWS_CALLS, TARGET_MARKETS - len(fixture) + 10)
        priced = priced_candidates(client, candidates, wanted)
    print(f"{len(priced)} with a pre-resolution price")

    if dry_run:
        for row in priced:
            print(f"  {row['id']} {row['yes_price']} outcome={row['outcome']} "
                  f"cat={row['category']}\n    q: {row['question']}\n    query: {row['news_query']}")
        return

    news = TheNewsApi(settings.thenewsapi_token, HEADLINES_PER_MARKET, settings.http_timeout)
    calls = 0
    for row in priced:
        if len(fixture) >= TARGET_MARKETS or calls >= MAX_NEWS_CALLS:
            break
        calls += 1
        try:
            headlines = three_headlines(news, row)
        # One failing market is logged and skipped. Only the type, never the
        # URL: the token is in it.
        except Exception as error:
            print(f"  news failed {row['id']}: {type(error).__name__}")
            continue
        if headlines is None:
            print(f"  only <{HEADLINES_PER_MARKET} headlines for {row['id']}, skipped")
            continue
        fixture.append(fixture_row(row, headlines))
        # Written now, not at the end, so a crash keeps what the calls bought.
        write_fixture(fixture)
        print(f"  saved {row['id']} ({len(fixture)} markets, {calls} news calls)")

    print(f"done: {len(fixture)} markets, {calls} news calls spent")


if __name__ == "__main__":
    main()
