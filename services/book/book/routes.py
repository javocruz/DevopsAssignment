from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from book.config import get_settings
from book.db import get_db
from book.intel_client import IntelUnavailable, fetch_estimates, fetch_resolutions
from book.repo import list_bets, place_bets, settle_bets, total_pnl
from book.scoring import brier_score, calibration_buckets
from book.security import require_admin

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parents[1] / "templates")
)

DECIDERS = ("stub", "jev")
CONTEXT_LEVELS = ("basic", "news")


def run_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def intel_or_503(load):
    try:
        return load()
    except IntelUnavailable:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "intel_unavailable",
                "detail": "Intel is starting up or down, try again in a minute",
            },
        )


@router.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


@router.get("/portfolio")
def get_portfolio(conn=Depends(get_db)):
    return {"bets": list_bets(conn), "total_pnl": total_pnl(conn)}


@router.post("/pipeline/auto-bet")
def auto_bet(request: Request, conn=Depends(get_db), _admin=Depends(require_admin)):
    request_id = getattr(request.state, "request_id", None)
    estimates = intel_or_503(lambda: fetch_estimates(request_id))
    return place_bets(conn, estimates, get_settings(), run_time())


@router.post("/pipeline/settle")
def settle(request: Request, conn=Depends(get_db), _admin=Depends(require_admin)):
    request_id = getattr(request.state, "request_id", None)
    resolutions = intel_or_503(lambda: fetch_resolutions(request_id))
    return settle_bets(conn, resolutions, run_time())


def scored_rows(estimates, resolutions, decider, context_level):
    outcome_by_market = {
        resolution.market_id: resolution.outcome for resolution in resolutions
    }
    rows = []
    for estimate in estimates:
        if estimate.decider != decider or estimate.context_level != context_level:
            continue
        if estimate.market_id not in outcome_by_market:
            continue
        rows.append((estimate, outcome_by_market[estimate.market_id]))
    return rows


@router.get("/scorecard")
def get_scorecard(request: Request, decider: str = "stub", context: str = "basic"):
    if decider not in DECIDERS or context not in CONTEXT_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"decider must be one of {DECIDERS} and context must be one of {CONTEXT_LEVELS}",
        )
    request_id = getattr(request.state, "request_id", None)
    estimates = intel_or_503(lambda: fetch_estimates(request_id))
    resolutions = intel_or_503(lambda: fetch_resolutions(request_id))
    rows = scored_rows(estimates, resolutions, decider, context)
    jev_probs = [estimate.jev_prob for estimate, _outcome in rows]
    market_prices = [estimate.market_price for estimate, _outcome in rows]
    outcomes = [outcome for _estimate, outcome in rows]
    return {
        "decider": decider,
        "context_level": context,
        "count": len(rows),
        "jev_brier": brier_score(jev_probs, outcomes),
        "market_brier": brier_score(market_prices, outcomes),
        "jev_calibration": calibration_buckets(jev_probs, outcomes),
        "market_calibration": calibration_buckets(market_prices, outcomes),
    }
