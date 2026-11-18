def settle_bet(side, stake, entry_price, outcome):
    shares = stake / entry_price
    won = (side == "YES" and outcome == 1) or (side == "NO" and outcome == 0)
    if won:
        return ("won", round(shares - stake, 2))
    return ("lost", round(-stake, 2))
