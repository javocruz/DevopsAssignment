from fastapi.testclient import TestClient

from app import app

TOKEN = "test-token"


def test_no_admin_token_leaves_post_open(tmp_db, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    response = TestClient(app).post("/markets/sync")
    assert response.status_code == 200


def test_right_header_allows_post(tmp_db, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", TOKEN)
    response = TestClient(app).post(
        "/markets/sync", headers={"X-Admin-Token": TOKEN}
    )
    assert response.status_code == 200


def test_wrong_header_is_401(tmp_db, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", TOKEN)
    response = TestClient(app).post(
        "/markets/sync", headers={"X-Admin-Token": "wrong-token"}
    )
    assert response.status_code == 401
    assert TOKEN not in response.text


def test_missing_header_is_401(tmp_db, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", TOKEN)
    response = TestClient(app).post("/markets/sync")
    assert response.status_code == 401
    assert TOKEN not in response.text


def test_healthz_stays_open_when_token_is_set(tmp_db, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", TOKEN)
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
