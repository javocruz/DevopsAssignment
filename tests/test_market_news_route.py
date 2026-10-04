from fastapi.testclient import TestClient

from app import app


def load_offline_data(client):
    assert client.post("/markets/sync").status_code == 200
    assert client.post("/news/fetch").status_code == 200


def test_news_route_returns_headlines_newest_first_and_before_cutoff(tmp_db):
    client = TestClient(app)
    load_offline_data(client)

    for market in client.get("/markets").json():
        body = client.get(f"/markets/{market['id']}/news").json()
        assert body["market_id"] == market["id"]
        dates = [item["published_at"] for item in body["items"]]
        assert dates == sorted(dates, reverse=True)
        # The look-ahead guard: nothing the page shows is newer than the price date.
        assert all(date < body["cutoff"] for date in dates)


def test_news_route_has_at_least_one_market_with_headlines(tmp_db):
    client = TestClient(app)
    load_offline_data(client)

    counts = [
        len(client.get(f"/markets/{market['id']}/news").json()["items"])
        for market in client.get("/markets").json()
    ]
    assert max(counts) > 0


def test_news_route_unknown_market_is_404(tmp_db):
    response = TestClient(app).get("/markets/not-a-real-market/news")
    assert response.status_code == 404
