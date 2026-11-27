import logging

import pymssql


def test_health_ok_logs_method_path_status_and_request_id(client, caplog):
    with caplog.at_level(logging.INFO, logger="edgebook.access"):
        response = client.get("/health", headers={"X-Request-ID": "req-1"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok", "version": "dev"}
    assert "GET /health 200" in caplog.text
    assert "req-1" in caplog.text


def test_health_uses_git_sha(client, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "abc123")
    assert client.get("/health").json()["version"] == "abc123"


def test_health_is_503_when_the_database_cannot_be_opened(client, monkeypatch):
    def broken():
        raise pymssql.OperationalError("cannot open")

    monkeypatch.setattr("intel.db.get_connection", broken)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["db"] == "down"


def test_cors_preflight_allows_content_type(cors_client):
    response = cors_client.options(
        "/markets/sync",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert "content-type" in response.headers["access-control-allow-headers"].lower()
