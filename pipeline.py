from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from book.repo import place_bets, settle_bets
from config import get_settings
from db import get_db
from intel.repo import list_estimate_records, list_resolutions

router = APIRouter()


def run_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# No admin check yet: require_admin arrives in C17.
@router.post("/pipeline/auto-bet")
def auto_bet(conn=Depends(get_db)):
    estimates = list_estimate_records(conn)
    return place_bets(conn, estimates, get_settings(), run_time())


# No admin check yet: require_admin arrives in C17.
@router.post("/pipeline/settle")
def settle(conn=Depends(get_db)):
    resolutions = list_resolutions(conn)
    return settle_bets(conn, resolutions, run_time())
