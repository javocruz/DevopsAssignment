import logging

import pymssql


def test_health_ok_logs_method_path_status_and_request_id(book_client, caplog):
    with caplog.at_level(logging.INFO, logger="edgebook.access"):
        response = book_client.get("/health", headers={"X-Request-ID": "req-9"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["db"] == "ok"
    assert "GET /health 200" in caplog.text
    assert "req-9" in caplog.text


def test_health_is_503_when_the_database_cannot_be_opened(book_client, monkeypatch):
    def broken():
        raise pymssql.OperationalError("cannot open")

    monkeypatch.setattr("book.db.get_connection", broken)
    response = book_client.get("/health")
    assert response.status_code == 503
    assert response.json()["db"] == "down"


def test_cors_preflight_allows_content_type(book_cors_client):
    response = book_cors_client.options(
        "/portfolio",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert "content-type" in response.headers["access-control-allow-headers"].lower()
