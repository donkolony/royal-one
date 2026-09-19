"""PostgreSQL access: one pooled connection per request, hand-written SQL."""
from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Sequence

import psycopg
from fastapi import Request
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

Row = Dict[str, Any]


def make_pool(database_url: str, min_size: int = 1, max_size: int = 8) -> ConnectionPool:
    # prepare_threshold=None turns off server-side prepared statements, which do not work behind
    # a transaction-mode pooler (the kind Supabase offers for external hosts).
    return ConnectionPool(
        conninfo=database_url,
        min_size=min_size,
        max_size=max_size,
        kwargs={"row_factory": dict_row, "prepare_threshold": None},
        timeout=15,
        open=True,
    )


def get_conn(request: Request) -> Iterator[psycopg.Connection]:
    """FastAPI dependency. One transaction per request: commit on success, roll back on any exception."""
    with request.app.state.pool.connection() as conn:
        yield conn


def fetch_all(conn: psycopg.Connection, sql: str, params: Sequence[Any] | Dict[str, Any] | None = None) -> List[Row]:
    return conn.execute(sql, params).fetchall()


def fetch_one(conn: psycopg.Connection, sql: str, params: Sequence[Any] | Dict[str, Any] | None = None) -> Optional[Row]:
    return conn.execute(sql, params).fetchone()


def execute(conn: psycopg.Connection, sql: str, params: Sequence[Any] | Dict[str, Any] | None = None) -> int:
    return conn.execute(sql, params).rowcount
