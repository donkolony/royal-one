"""Load the synthetic demo dataset.

  python scripts/seed.py --reset          wipe demo data tables and reseed
  python scripts/seed.py --reset --auth   also create the demo users in Supabase Auth FIRST (required on Supabase,
                                          because profiles reference auth.users). Needs SEED_DEMO_PASSWORD.

All data is invented. Passwords are never printed.
"""
import argparse

import _bootstrap  # noqa: F401
import psycopg
from psycopg.rows import dict_row

from app import seed
from app.core.config import get_settings, validate_settings
from app.storage.base import MemoryStorage, SupabaseStorage


def create_auth_users(settings) -> None:
    from supabase import create_client

    password = settings.seed_demo_password
    if not password:
        raise SystemExit("Set SEED_DEMO_PASSWORD in backend/.env to create the demo users.")
    admin = create_client(settings.supabase_url, settings.supabase_service_role_key).auth.admin
    for u in seed.USERS:
        try:
            admin.create_user({"id": str(u["id"]), "email": u["email"], "password": password, "email_confirm": True})
            print(f"created auth user {u['email']}")
        except Exception as e:  # already exists is fine; anything else is shown
            print(f"auth user {u['email']}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="empty the demo data tables first")
    ap.add_argument("--auth", action="store_true", help="create the demo users in Supabase Auth first")
    args = ap.parse_args()
    settings = validate_settings(get_settings())
    if args.auth:
        create_auth_users(settings)
    storage = MemoryStorage() if settings.storage_backend == "memory" else SupabaseStorage(settings.supabase_url, settings.supabase_service_role_key)
    with psycopg.connect(settings.database_url, row_factory=dict_row, prepare_threshold=None) as conn:
        if args.reset:
            seed.reset_data(conn)
        try:
            seed.seed_demo(conn, settings, storage)
        except psycopg.errors.ForeignKeyViolation as e:
            raise SystemExit(f"{e}\nOn Supabase, profiles reference auth.users: rerun with --auth so the users exist first.")
        except psycopg.errors.UniqueViolation:
            raise SystemExit("Demo data already exists. Rerun with --reset to replace it.")
    print("Seeded demo data:", ", ".join(u["email"] for u in seed.USERS))
