"""Pytest configuration — test database isolation.

The engine binds to ``settings.DATABASE_URL`` (read from the environment) at
import time, so the database URL must be overridden here, before any
``aether.*`` module is imported during test collection.

Every pytest invocation starts against a brand-new database file. This keeps
fixed test IDs (agents, experience nodes, fragments, ...) from colliding with
stale state left behind by previous runs, and keeps tests away from any
developer/production database.
"""

import os
import pytest
import pytest_asyncio

TESTS_DIR = os.path.dirname(__file__)
TEST_DATA_DIR = os.path.join(TESTS_DIR, ".test_data")
VECTOR_STORE_PATH = os.path.join(TEST_DATA_DIR, "vectors", "store.pkl")

# Override before aether.storage.database first binds the engine.
os.environ["DATABASE_URL"] = (
    f"sqlite+aiosqlite:////{os.path.join(TEST_DATA_DIR, 'aether_test.db')}"
)
os.environ["AETHER_VECTOR_STORE_PATH"] = VECTOR_STORE_PATH

# Fresh start: remove any state left behind by a previous invocation
# including the WAL/shm sidecar files that can survive an interrupted run.
os.makedirs(os.path.dirname(VECTOR_STORE_PATH), exist_ok=True)
DB_PATH = os.path.join(TEST_DATA_DIR, "aether_test.db")
for path in (
    DB_PATH,
    f"{DB_PATH}-wal",
    f"{DB_PATH}-shm",
    VECTOR_STORE_PATH,
):
    if os.path.exists(path):
        os.remove(path)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _cleanup_engine():
    """Close all engine connections when the run finishes."""
    yield
    from aether.storage.database import engine
    await engine.dispose()