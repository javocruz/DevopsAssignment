import os
from urllib.parse import urlsplit
from uuid import uuid4

import pytest


@pytest.fixture
def intel_test_db(monkeypatch):
    """Give each integration test a fresh database on the local SQL container."""
    import pymssql
    from intel.config import database_options
    from migrate import init_db

    url = os.environ.get("TEST_DATABASE_URL", "")
    if urlsplit(url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("Set TEST_DATABASE_URL to the local SQL Server master database")
    options = database_options(url)
    if options["database"] != "master":
        pytest.fail("TEST_DATABASE_URL must point to master to create disposable test databases")

    name = "intel_test_" + uuid4().hex
    with pymssql.connect(**options, autocommit=True, login_timeout=5) as admin:
        cursor = admin.cursor()
        cursor.execute(f"CREATE DATABASE [{name}]")
        try:
            monkeypatch.setenv("DATABASE_URL", urlsplit(url)._replace(path="/" + name).geturl())
            for key, value in {"DECIDER": "stub", "MARKET_SOURCE": "fixture",
                               "NEWS_SOURCE": "fixture", "ADMIN_TOKEN": ""}.items():
                monkeypatch.setenv(key, value)
            init_db()
            yield name
        finally:
            cursor.execute(f"DROP DATABASE [{name}]")
