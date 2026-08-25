"""
Lakán DLSU-D — database layer (PostgreSQL via psycopg 3 + connection pool).

All database access in the app goes through this module so the engine is
swappable in one place. Reads DATABASE_URL from the environment, e.g.:

    DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require

(Neon connection strings already include sslmode=require; local Postgres
does not need it.)
"""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
_pool: ConnectionPool | None = None


def init_pool() -> ConnectionPool | None:
    """Create the connection pool once. Safe to call repeatedly."""
    global _pool
    if _pool is not None:
        return _pool
    if not DATABASE_URL:
        print("⚠️  DATABASE_URL not set — database features are disabled")
        return None
    try:
        _pool = ConnectionPool(
            DATABASE_URL,
            min_size=1,
            max_size=5,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        print("✅ Postgres connection pool created")
    except Exception as e:
        print(f"⚠️  Postgres connection error: {e}")
        _pool = None
    return _pool


def pool_is_up() -> bool:
    return _pool is not None


@contextmanager
def get_conn():
    """Yield a pooled connection (commits on success, rolls back on error).

    Yields None when no database is configured, so callers can degrade
    gracefully the same way the old MySQL code did.
    """
    pool = init_pool()
    if pool is None:
        yield None
        return
    with pool.connection() as conn:
        yield conn


def query(sql: str, params=None) -> list[dict]:
    """Run a SELECT and return a list of dict rows ([] on any failure)."""
    try:
        with get_conn() as conn:
            if conn is None:
                return []
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
    except Exception as e:
        print(f"⚠️  query error: {e}")
        return []


def query_one(sql: str, params=None) -> dict | None:
    """Run a SELECT and return the first row or None."""
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params=None) -> int:
    """Run a single write statement in its own transaction.

    Returns the affected row count, or -1 on failure / no database.
    """
    try:
        with get_conn() as conn:
            if conn is None:
                return -1
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.rowcount
    except Exception as e:
        print(f"⚠️  execute error: {e}")
        return -1
