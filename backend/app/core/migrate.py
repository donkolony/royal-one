"""Minimal ordered SQL migration runner. Applied files are recorded in `schema_migrations`."""
from __future__ import annotations

from pathlib import Path
from typing import List

import psycopg

from app.core.config import REPO_DIR

MIGRATIONS_DIR = REPO_DIR / "supabase" / "migrations"


def apply_migrations(database_url: str, directory: Path = MIGRATIONS_DIR) -> List[str]:
    """Apply every unapplied *.sql file in filename order. Returns the filenames applied now."""
    applied_now: List[str] = []
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "create table if not exists schema_migrations (filename text primary key, applied_at timestamptz not null default now())"
        )
        done = {r[0] for r in conn.execute("select filename from schema_migrations").fetchall()}
        for path in sorted(directory.glob("*.sql")):
            if path.name in done:
                continue
            # One transaction per file: a failing file leaves nothing half applied.
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("insert into schema_migrations (filename) values (%s)", (path.name,))
            applied_now.append(path.name)
    return applied_now
