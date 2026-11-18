import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from intel.db import init_db


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    init_db()
    return tmp_path


def load_app():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("intel_asgi", root / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


@pytest.fixture
def client(tmp_db):
    return TestClient(load_app())


@pytest.fixture
def cors_client(tmp_db, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:8080")
    return TestClient(load_app())
