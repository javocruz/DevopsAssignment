def compute_edge(jev_prob, market_price):
    return jev_prob - market_price


def should_bet(edge, confidence, info_score, settings):
    return (
        abs(edge) >= settings.edge_threshold
        and confidence >= settings.min_confidence
        and info_score >= settings.min_info
    )


# Zero is not a Yes. Only a positive edge means Jev is above the market.
def pick_side(edge):
    if edge > 0:
        return "YES"
    return "NO"


def entry_price(side, market_price):
    if side == "YES":
        return market_price
    return 1 - market_price


# Stake grows with the edge, then stops at max_stake. Dividing by the
# threshold is why EDGE_THRESHOLD must be greater than 0.
def size_stake(edge, settings):
    raw = settings.base_stake * abs(edge) / settings.edge_threshold
    return round(min(settings.max_stake, raw), 2)
