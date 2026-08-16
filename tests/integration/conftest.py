import os
import time

import psycopg2
import pytest


@pytest.fixture(scope="session", autouse=True)
def wait_for_disposable_postgresql():
    """Remove CI startup races before destructive integration tests begin."""
    dsn = os.environ.get("CATALOGUE_TEST_DB_DSN")
    if not dsn:
        yield
        return

    deadline = time.monotonic() + 60
    while True:
        try:
            conn = psycopg2.connect(dsn, connect_timeout=3)
            conn.close()
            break
        except psycopg2.OperationalError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)
    yield
