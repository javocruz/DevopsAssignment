from fastapi import APIRouter, Depends

from config import get_settings
from db import get_db
from intel.news import fetch_news_for_markets, get_news_source
from intel.repo import list_markets, save_markets
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
