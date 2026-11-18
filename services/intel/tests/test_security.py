TOKEN = "test-token"


def test_no_admin_token_leaves_post_open(client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    response = client.post("/markets/sync")
    assert response.status_code == 200


def test_right_header_allows_post(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", TOKEN)
    response = client.post(
        "/markets/sync", headers={"X-Admin-Token": TOKEN}
    )
    assert response.status_code == 200


def test_wrong_header_is_401(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", TOKEN)
    response = client.post(
        "/markets/sync", headers={"X-Admin-Token": "wrong-token"}
    )
    assert response.status_code == 401
    assert TOKEN not in response.text


def test_missing_header_is_401(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", TOKEN)
    response = client.post("/markets/sync")
    assert response.status_code == 401
    assert TOKEN not in response.text


def test_health_stays_open_when_token_is_set(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", TOKEN)
    response = client.get("/health")
    assert response.status_code == 200
