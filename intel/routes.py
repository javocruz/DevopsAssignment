from fastapi import APIRouter, Depends

from config import get_settings
from db import get_db
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
