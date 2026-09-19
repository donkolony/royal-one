"""Index the approved documents in data/rag-docs/ for the assistant. Idempotent (documents are keyed by content hash).
  python scripts/ingest_docs.py [--dir path/to/folder]      (the folder needs a manifest.json)
"""
import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
import psycopg
from psycopg.rows import dict_row

from app.core.config import REPO_DIR, get_settings, validate_settings
from app.rag.ingest import ingest_directory
from app.storage.base import MemoryStorage, SupabaseStorage

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(REPO_DIR / "data" / "rag-docs"))
    args = ap.parse_args()
    settings = validate_settings(get_settings())
    storage = MemoryStorage() if settings.storage_backend == "memory" else SupabaseStorage(settings.supabase_url, settings.supabase_service_role_key)
    with psycopg.connect(settings.database_url, row_factory=dict_row, prepare_threshold=None) as conn:
        report = ingest_directory(conn, storage, settings, Path(args.dir))
    print("created:", report.created or "-")
    print("unchanged:", report.unchanged or "-")
    print("failed:", report.failed or "-")
    if report.skipped_pages:
        print("pages with no extractable text (skipped):", report.skipped_pages)
