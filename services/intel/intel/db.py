import time

import pymssql

from intel.config import database_options, get_settings


def retry_database(operation):
    deadline = time.monotonic() + 90
    delay = 1
    while True:
        try:
            return operation()
        except pymssql.OperationalError as exc:
            remaining = deadline - time.monotonic()
            if exc.args[0] not in (20002, 20003, 20006, 20009, 20017, 40613) or remaining <= 0:
                raise
            time.sleep(min(delay, remaining))
            delay = min(delay * 2, 16)


def connect():
    options = database_options(get_settings().database_url)
    return pymssql.connect(**options, as_dict=True, login_timeout=5, encryption="require")


def get_connection():
    return retry_database(connect)


def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
