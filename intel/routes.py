from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from config import get_settings
from db import get_db
from intel.decider import get_decider
from intel.estimates import run_estimates
from intel.news import fetch_news_for_markets, get_news_source
from intel.repo import list_estimate_records, list_markets, save_markets
from intel.sources import FixtureSource, get_source

router = APIRouter()


@router.post("/markets/sync")
def sync_markets(conn=Depends(get_db)):
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


# No admin check yet: require_admin arrives in C17.
@router.post("/news/fetch")
def fetch_news(conn=Depends(get_db)):
    settings = get_settings()
    source = get_news_source(settings)
    return fetch_news_for_markets(
        conn, source, list_markets(conn), settings.news_max_calls_per_run
    )


CONTEXT_LEVELS = ("basic", "news")


# No admin check yet: require_admin arrives in C17.
@router.post("/estimates/run")
def run_estimates_route(context: str = "basic", conn=Depends(get_db)):
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
