import json
import logging
from datetime import date

from intel.news import filter_news_before
from intel.repo import estimate_exists, latest_snapshot, list_markets, list_news_items, save_estimate

logger = logging.getLogger(__name__)

HEADLINE_KEYS = ("title", "description", "published_at")


# Pure. Only the date part counts, so the time of day never adds or loses a day.
def days_to_resolution(end_date, as_of):
    days = (date.fromisoformat(end_date[:10]) - date.fromisoformat(as_of[:10])).days
    return max(0, days)


# Pure. This dict is exactly what the decider gets to see. outcome, yes_price,
# status and market_id stay out: the answer, the market's opinion, and a
# label that could hint at either.
def build_state(market, snapshot, news, context_level):
    state = {
        "question": market["question"],
        "rules": market["rules"],
        "category": market["category"],
        "end_date": market["end_date"],
        "as_of": snapshot["captured_at"],
        "days_to_resolution": days_to_resolution(market["end_date"], snapshot["captured_at"]),
    }
    if market["analyst_notes"]:
        state["analyst_notes"] = market["analyst_notes"]
    if context_level == "news":
        state["headlines"] = [{key: item.get(key) for key in HEADLINE_KEYS} for item in news]
    return state


# Pure. Jev's state field is text, so the dict becomes labeled lines.
# Empty fields are left out instead of printing "None" to the decider.
def render_state(state):
    lines = [f"Question: {state['question']}"]
    if state["rules"]:
        lines.append(f"Resolution rules: {state['rules']}")
    if state["category"]:
        lines.append(f"Category: {state['category']}")
    lines.append(f"Market closes: {state['end_date'][:10]}")
    lines.append(f"Today: {state['as_of'][:10]} ({state['days_to_resolution']} days before close)")
    if state.get("analyst_notes"):
        lines.append(f"Analyst notes: {state['analyst_notes']}")
    headlines = state.get("headlines")
    if headlines:
        lines.append("Recent headlines (newest first):")
        for item in sorted(headlines, key=lambda h: h["published_at"], reverse=True):
            lines.append(render_headline(item))
    return "\n".join(lines)


def render_headline(item):
    line = f"- {item['published_at'][:10]}: {item['title']}"
    if item["description"]:
        line += f" | {item['description']}"
    return line


# Only cached news_items are read here, never the news API. news_source is
# passed in for its limit, which is NEWS_ARTICLES.
def load_news(conn, market_id, snapshot, news_source, context_level):
    if context_level != "news":
        return []
    items = list_news_items(conn, market_id)
    return filter_news_before(items, snapshot["captured_at"], news_source.limit)


def run_estimates(conn, decider, news_source, context_level, limit, now):
    processed = 0
    skipped = 0
    failed = []
    attempted = 0

    for market in list_markets(conn):
        market_id = market["id"]
        snapshot = latest_snapshot(conn, market_id)
        # No snapshot means no price and no as_of date, so nothing to ask.
        if snapshot is None:
            skipped += 1
            continue
        # Checked before calling the decider, so a re-run never pays for a
        # Jev call whose answer INSERT OR IGNORE would throw away.
        if estimate_exists(conn, market_id, snapshot["id"], decider.name, context_level):
            skipped += 1
            continue
        if attempted >= limit:
            skipped += 1
            continue

        attempted += 1
        try:
            news = load_news(conn, market_id, snapshot, news_source, context_level)
            state = build_state(market, snapshot, news, context_level)
            decision = decider.decide(market_id, render_state(state), snapshot["yes_price"])
            # The dict is stored, not the text, so it can be checked and re-rendered later.
            save_estimate(
                conn, market_id, snapshot["id"], decider.name, context_level,
                decision, json.dumps(state), now,
            )
        # One failing market is logged and skipped, never crashes the batch.
        # Only the error type is logged, so a leaky message can't print a key.
        except Exception as error:
            logger.warning("Estimate failed for %s: %s", market_id, type(error).__name__)
            failed.append({"market_id": market_id, "reason": type(error).__name__})
            continue
        processed += 1

    return {"processed": processed, "skipped": skipped, "failed": failed}
