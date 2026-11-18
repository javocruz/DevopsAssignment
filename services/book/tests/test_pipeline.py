from pathlib import Path

BOOK_DIR = Path(__file__).resolve().parents[1] / "book"


def test_offline_pipeline_settles_every_bet(bridged):
    intel, book = bridged
    assert intel.post("/markets/sync").status_code == 200
    assert intel.post("/news/fetch").status_code == 200
    assert intel.post("/estimates/run").status_code == 200

    first = book.post("/pipeline/auto-bet")
    assert first.status_code == 200
    settled = book.post("/pipeline/settle")
    assert settled.status_code == 200

    portfolio = book.get("/portfolio").json()
    bets = portfolio["bets"]
    assert first.json()["processed"] >= 1
    assert len(bets) == first.json()["processed"]
    for bet in bets:
        assert bet["status"] in ("won", "lost")
        assert isinstance(bet["pnl"], float)
    assert portfolio["total_pnl"] == round(sum(bet["pnl"] for bet in bets), 2)

    second = book.post("/pipeline/auto-bet")
    assert second.status_code == 200
    assert second.json()["processed"] == 0
    again = book.get("/portfolio").json()
    assert len(again["bets"]) == len(bets)

    second_settle = book.post("/pipeline/settle")
    assert second_settle.status_code == 200
    after = book.get("/portfolio").json()
    assert [(bet["id"], bet["status"], bet["pnl"]) for bet in after["bets"]] == [
        (bet["id"], bet["status"], bet["pnl"]) for bet in bets
    ]


def test_book_does_not_import_intel():
    for path in BOOK_DIR.glob("*.py"):
        text = path.read_text()
        assert "import intel" not in text
        assert "from intel" not in text
