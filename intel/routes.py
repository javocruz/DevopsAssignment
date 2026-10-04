from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from config import get_settings
from db import get_db
from intel.decider import get_decider
from intel.estimates import run_estimates
from intel.news import fetch_news_for_markets, get_news_source
from intel.repo import (
    get_market,
    latest_snapshot,
    list_estimate_records,
    list_markets,
    list_news_items,
    save_markets,
)
from intel.sources import FixtureSource, get_source
from security import require_admin

router = APIRouter()


@router.post("/markets/sync")
def sync_markets(conn=Depends(get_db), _admin=Depends(require_admin)):
    source = get_source(get_settings())
    result = source.fetch()
    # FixtureSource returns a plain list, PolymarketSource returns a summary.
    if isinstance(source, FixtureSource):
        result = {"rows": result, "skipped": 0, "failed": []}
    save_markets(conn, result["rows"])
    return {
        "processed": len(result["rows"]),
        "skipped": result["skipped"],
        "failed": result["failed"],
    }


@router.get("/markets")
def get_markets(conn=Depends(get_db)):
    return [dict(row) for row in list_markets(conn)]


# Read-only. Returns the saved headlines for one market, newest first, plus the
# price date they must be older than, so the page can show the look-ahead guard.
# An unknown id is a 404, so a typo is not mistaken for "no news".
@router.get("/markets/{market_id}/news")
def get_market_news(market_id: str, conn=Depends(get_db)):
    if get_market(conn, market_id) is None:
        raise HTTPException(status_code=404, detail="Unknown market")
    snapshot = latest_snapshot(conn, market_id)
    cutoff = snapshot["captured_at"] if snapshot else None
    items = list_news_items(conn, market_id)
    items.sort(key=lambda item: item["published_at"], reverse=True)
    return {"market_id": market_id, "cutoff": cutoff, "items": items}


@router.post("/news/fetch")
def fetch_news(conn=Depends(get_db), _admin=Depends(require_admin)):
    settings = get_settings()
    source = get_news_source(settings)
    return fetch_news_for_markets(
        conn, source, list_markets(conn), settings.news_max_calls_per_run
    )


CONTEXT_LEVELS = ("basic", "news")


@router.post("/estimates/run")
def run_estimates_route(
    context: str = "basic", conn=Depends(get_db), _admin=Depends(require_admin)
):
    if context not in CONTEXT_LEVELS:
        raise HTTPException(status_code=400, detail=f"context must be one of {CONTEXT_LEVELS}")
    settings = get_settings()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return run_estimates(
        conn, get_decider(settings), get_news_source(settings),
        context, settings.estimate_batch_limit, now,
    )


# Plain dicts so the route returns JSON. No ?min_edge= here: edge is Book
# math (compute_edge, C11) and intel must not import book.
@router.get("/estimates")
def get_estimates(conn=Depends(get_db)):
    return [asdict(record) for record in list_estimate_records(conn)]
