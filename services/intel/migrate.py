import logging
from pathlib import Path

from intel.db import connect, retry_database

MIGRATIONS = Path(__file__).with_name("migrations")
log = logging.getLogger(__name__)


def apply_migrations():
    with connect() as conn:
        cursor = conn.cursor()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            # Hold the lock through commit so concurrent starts agree on what ran.
            cursor.execute("""
                DECLARE @result int;
                EXEC @result = sp_getapplock @Resource='intel_migrations',
                    @LockMode='Exclusive', @LockOwner='Transaction';
                IF @result < 0 THROW 50000, 'Could not lock migrations', 1;
                IF OBJECT_ID('dbo.schema_migrations', 'U') IS NULL
                    CREATE TABLE dbo.schema_migrations (
                        version INT PRIMARY KEY,
                        applied_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
                    );
            """)
            version = int(path.name[:3])
            cursor.execute("SELECT version FROM dbo.schema_migrations WHERE version=%s", (version,))
            if cursor.fetchone() is not None:
                conn.commit()
                continue

            cursor.execute(path.read_text())
            cursor.execute("INSERT INTO dbo.schema_migrations (version) VALUES (%s)", (version,))
            conn.commit()
            log.info("Applied %s", path.name)


def init_db():
    retry_database(apply_migrations)
