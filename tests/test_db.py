import pytest

from db import SCHEMA_VERSION, get_connection, get_schema_version, init_db

EXPECTED_TABLES = {"markets", "price_snapshots", "news_items", "estimates", "bets"}


def table_names(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row["name"] for row in rows}


def test_fresh_db_gets_version_1_and_5_tables(tmp_db):
    conn = get_connection()
    assert get_schema_version(conn) == SCHEMA_VERSION == 1
    assert table_names(conn) == EXPECTED_TABLES
    conn.close()


def test_second_init_is_a_no_op(tmp_db):
    init_db()
    conn = get_connection()
    assert get_schema_version(conn) == 1
    assert table_names(conn) == EXPECTED_TABLES
    conn.close()


def test_wrong_version_raises(tmp_db):
    conn = get_connection()
    conn.execute("PRAGMA user_version = 2")
    conn.close()
    with pytest.raises(RuntimeError, match="v2, app expects v1"):
        init_db()
