"""Start a throwaway local PostgreSQL (bundled by the `pgserver` dev package), apply the migrations and print a
DATABASE_URL. For offline development without Supabase. Data lives in backend/.localdb (gitignored).

  python scripts/dev_db.py            # start (or reuse) and print the URL
  python scripts/dev_db.py --stop     # stop it
"""
import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
import pgserver

from app.core.migrate import apply_migrations

PGDATA = Path(__file__).resolve().parents[1] / ".localdb"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stop", action="store_true")
    args = ap.parse_args()
    server = pgserver.get_server(PGDATA, cleanup_mode="stop" if args.stop else None)
    if args.stop:
        server.cleanup()
        print("stopped")
    else:
        uri = server.get_uri()
        applied = apply_migrations(uri)
        print("migrations applied:", applied or "already up to date")
        print("DATABASE_URL=" + uri)
