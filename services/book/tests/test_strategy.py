from types import SimpleNamespace

from book.strategy import (
    compute_edge,
    entry_price,
    pick_side,
    should_bet,
    size_stake,
)


def book_settings():
    return SimpleNamespace(
        edge_threshold=0.08,
        min_confidence=0.6,
        min_info=0.4,
        base_stake=10,
        max_stake=50,
    )


def test_yes_bet_at_point_fifteen():
    settings = book_settings()
    edge = compute_edge(0.75, 0.60)
    assert round(edge, 2) == 0.15
    assert pick_side(edge) == "YES"
    assert entry_price("YES", 0.60) == 0.60
    assert should_bet(edge, 0.9, 0.9, settings)
    assert size_stake(edge, settings) == 18.75


def test_negative_edge_bets_no():
    settings = book_settings()
    edge = compute_edge(0.30, 0.45)
    assert round(edge, 2) == -0.15
    assert pick_side(edge) == "NO"
    assert entry_price("NO", 0.45) == 0.55
    assert should_bet(edge, 0.9, 0.9, settings)
    assert size_stake(edge, settings) == 18.75


def test_stake_caps_at_max():
    settings = book_settings()
    edge = compute_edge(0.95, 0.40)
    assert round(edge, 2) == 0.55
    assert size_stake(edge, settings) == 50


def test_small_edge_does_not_bet():
    settings = book_settings()
    edge = compute_edge(0.63, 0.60)
    assert round(edge, 2) == 0.03
    assert should_bet(edge, 0.9, 0.9, settings) is False


def test_exact_threshold_uses_the_number_directly():
    settings = book_settings()
    edge = 0.08
    assert should_bet(edge, 0.9, 0.9, settings)
    assert size_stake(edge, settings) == 10.00


def test_low_confidence_or_info_blocks_a_large_edge():
    settings = book_settings()
    edge = 0.20
    assert should_bet(edge, 0.5, 0.9, settings) is False
    assert should_bet(edge, 0.9, 0.3, settings) is False
