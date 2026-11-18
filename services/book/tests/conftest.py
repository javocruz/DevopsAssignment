import importlib.util
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from book.db import init_db

SERVICE = Path(__file__).resolve().parents[1]
INTEL = SERVICE.parent / "intel"


def load_app(root, name):
    spec = importlib.util.spec_from_file_location(name, root / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    init_db()
    return tmp_path


@pytest.fixture
def apps(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from intel.db import init_db as init_intel
    init_intel()
    init_db()
    intel = TestClient(load_app(INTEL, "intel_asgi"))
    book = TestClient(load_app(SERVICE, "book_asgi"))
    return intel, book


@pytest.fixture
def book_client(tmp_db):
    return TestClient(load_app(SERVICE, "book_asgi_client"))


@pytest.fixture
def book_cors_client(tmp_db, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:8080")
    return TestClient(load_app(SERVICE, "book_asgi_cors"))


@pytest.fixture
def bridged(apps, monkeypatch):
    intel, book = apps
    bridge(monkeypatch, intel)
    return intel, book


def bridge(monkeypatch, intel_client):
    class Fake:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, path, **kwargs):
            response = intel_client.get(path, headers=kwargs.get("headers"))
            if response.status_code >= 400:
                request = httpx.Request("GET", "http://intel" + path)
                raise httpx.HTTPStatusError(
                    "intel", request=request, response=httpx.Response(response.status_code)
                )
            return response

    monkeypatch.setattr("book.intel_client.httpx.Client", Fake)
