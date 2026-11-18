import httpx

from book.config import get_settings
from book.contracts import Estimate, Resolution


class IntelUnavailable(Exception):
    pass


def fetch_estimates(request_id=None):
    return [_estimate(row) for row in _get("/estimates", request_id)]


def fetch_resolutions(request_id=None):
    return [_resolution(row) for row in _get("/resolutions", request_id)]


def _estimate(row):
    return Estimate(
        estimate_id=row["estimate_id"],
        market_id=row["market_id"],
        question=row["question"],
        market_price=row["market_price"],
        jev_prob=row["jev_prob"],
        info_score=row["info_score"],
        confidence=row["confidence"],
        decider=row["decider"],
        context_level=row["context_level"],
        created_at=row["created_at"],
    )


def _resolution(row):
    return Resolution(
        market_id=row["market_id"],
        outcome=row["outcome"],
        resolved_at=row["resolved_at"],
    )


# One retry, then the caller turns this into a 503. Caching is a later commit.
def _get(path, request_id=None):
    settings = get_settings()
    headers = {}
    if request_id:
        headers["X-Request-ID"] = request_id
    last_error = None
    for _attempt in (1, 2):
        try:
            with httpx.Client(base_url=settings.intel_url, timeout=settings.intel_timeout_s) as client:
                response = client.get(path, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            last_error = exc
    raise IntelUnavailable(str(last_error))
