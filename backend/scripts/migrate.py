"""Apply supabase/migrations/*.sql in order. Safe to re-run.  Usage: python scripts/migrate.py"""
import _bootstrap  # noqa: F401

from app.core.config import get_settings
from app.core.migrate import apply_migrations

if __name__ == "__main__":
    url = get_settings().database_url
    if not url:
        raise SystemExit("DATABASE_URL is not set (see backend/.env.example).")
    applied = apply_migrations(url)
    print("Applied:", ", ".join(applied) if applied else "nothing (already up to date)")
