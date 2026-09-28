import pytest

from db import init_db


# Each test gets its own empty DB in a temp folder, never ./data.
@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    init_db()
    return tmp_path
