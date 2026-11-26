import pymssql
import pytest
from book.db import get_connection
from book.migrate import init_db
from book.repo import query


def test_fresh_db_has_book_tables_and_migration_record(tmp_db):
    with get_connection() as conn:
        tables = query(conn, "SELECT name FROM sys.tables").fetchall()
        assert {row["name"] for row in tables} == {
            "bets", "intel_cache", "schema_migrations"
        }
        assert query(conn, "SELECT version FROM schema_migrations").fetchall() == [{"version": 1}]


def test_second_init_preserves_the_original_migration_record(tmp_db):
    with get_connection() as conn:
        before = query(conn, "SELECT * FROM schema_migrations").fetchall()
    init_db()
    with get_connection() as conn:
        assert query(conn, "SELECT * FROM schema_migrations").fetchall() == before


def test_failed_migration_rolls_back_and_can_be_retried(tmp_db, tmp_path, monkeypatch):
    monkeypatch.setattr("book.migrate.MIGRATIONS", tmp_path)
    migration = tmp_path / "002_test.sql"
    create = "CREATE TABLE migration_probe (id INT PRIMARY KEY);"
    migration.write_text(create + " THROW 50001, 'test failure', 1;")
    with pytest.raises(pymssql.DatabaseError):
        init_db()
    with get_connection() as conn:
        assert query(conn, "SELECT name FROM sys.tables WHERE name='migration_probe'").fetchone() is None
        assert query(conn, "SELECT version FROM schema_migrations WHERE version=2").fetchone() is None
    migration.write_text(create)
    init_db()
    with get_connection() as conn:
        assert query(conn, "SELECT version FROM schema_migrations WHERE version=2").fetchone()
