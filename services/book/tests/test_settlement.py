from book.settlement import settle_bet


def test_yes_win_pays_the_shares_minus_stake():
    assert settle_bet("YES", 10, 0.40, 1) == ("won", 15.00)


def test_yes_loss_loses_the_stake():
    assert settle_bet("YES", 10, 0.40, 0) == ("lost", -10.00)


def test_no_win_rounds_profit_to_cents():
    assert settle_bet("NO", 18.75, 0.55, 0) == ("won", 15.34)


def test_no_loss_loses_the_stake():
    assert settle_bet("NO", 18.75, 0.55, 1) == ("lost", -18.75)
