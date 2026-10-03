from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from book.repo import place_bets, settle_bets
from book.scoring import brier_score, calibration_buckets
from config import get_settings
from db import get_db
from intel.repo import list_estimate_records, list_resolutions
from security import require_admin

router = APIRouter()

DECIDERS = ("stub", "jev")
CONTEXT_LEVELS = ("basic", "news")


def run_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.post("/pipeline/auto-bet")
def auto_bet(conn=Depends(get_db), _admin=Depends(require_admin)):
    estimates = list_estimate_records(conn)
    return place_bets(conn, estimates, get_settings(), run_time())


@router.post("/pipeline/settle")
def settle(conn=Depends(get_db), _admin=Depends(require_admin)):
    resolutions = list_resolutions(conn)
    return settle_bets(conn, resolutions, run_time())


# One decider and one context. Mixing them would make the score meaningless.
def scored_rows(estimates, resolutions, decider, context_level):
    outcome_by_market = {
        resolution.market_id: resolution.outcome for resolution in resolutions
    }
    rows = []
    for estimate in estimates:
        if estimate.decider != decider or estimate.context_level != context_level:
            continue
        # No outcome yet, so this forecast cannot be scored.
        if estimate.market_id not in outcome_by_market:
            continue
        rows.append((estimate, outcome_by_market[estimate.market_id]))
    return rows


@router.get("/scorecard")
def get_scorecard(decider: str = "stub", context: str = "basic", conn=Depends(get_db)):
    if decider not in DECIDERS or context not in CONTEXT_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"decider must be one of {DECIDERS} and context must be one of {CONTEXT_LEVELS}",
        )
    rows = scored_rows(
        list_estimate_records(conn), list_resolutions(conn), decider, context
    )
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
