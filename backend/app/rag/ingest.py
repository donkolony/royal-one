"""Ingest approved PDFs into `documents` / `document_chunks` (docs/ARCHITECT.md section 8.2).

Idempotent: a document is identified by the SHA-256 of its bytes. Re-running with an unchanged file only refreshes
its metadata. Pages without extractable text (scans) are skipped and reported; OCR is out of scope.
"""
from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import psycopg
from pypdf import PdfReader

from app.core.config import Settings
from app.core.db import execute, fetch_one
from app.domain import constants as C
from app.rag.chunking import chunk_page
from app.storage.base import Storage


@dataclass
class IngestReport:
    created: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    skipped_pages: Dict[str, List[int]] = field(default_factory=dict)


def extract_pages(data: bytes) -> List[str]:
    reader = PdfReader(io.BytesIO(data))
    return [(page.extract_text() or "") for page in reader.pages]


def ingest_document(conn: psycopg.Connection, storage: Storage, settings: Settings, data: bytes, meta: Dict[str, Any], report: IngestReport) -> None:
    title = meta["title"]
    if meta["category"] not in C.DOCUMENT_CATEGORIES:
        raise ValueError(f"{title}: category must be one of {C.DOCUMENT_CATEGORIES}")
    content_hash = hashlib.sha256(data).hexdigest()
    insurer_id = None
    if meta.get("insurer"):
        row = fetch_one(conn, "select id from insurers where name = %s", (meta["insurer"],))
        if row is None:
            raise ValueError(f"{title}: unknown insurer '{meta['insurer']}'")
        insurer_id = row["id"]

    existing = fetch_one(conn, "select id, status from documents where content_hash = %s", (content_hash,))
    if existing and existing["status"] == "indexed":
        execute(
            conn,
            "update documents set title=%s, category=%s, insurer_id=%s, version_label=%s, is_synthetic=%s, source_note=%s where id=%s",
            (title, meta["category"], insurer_id, meta.get("version_label"), meta.get("is_synthetic", True), meta.get("source_note"), existing["id"]),
        )
        report.unchanged.append(title)
        return
    if existing:  # a previous attempt failed half way: start clean
        execute(conn, "delete from documents where id = %s", (existing["id"],))

    doc = fetch_one(
        conn,
        "insert into documents (title, category, insurer_id, version_label, is_synthetic, source_note, content_hash, status) "
        "values (%s,%s,%s,%s,%s,%s,%s,'processing') returning id",
        (title, meta["category"], insurer_id, meta.get("version_label"), meta.get("is_synthetic", True), meta.get("source_note"), content_hash),
    )
    pages = extract_pages(data)
    n_chunks, skipped = 0, []
    for page_no, text in enumerate(pages, start=1):
        chunks = chunk_page(text)
        if not chunks:
            skipped.append(page_no)
        for idx, content in enumerate(chunks):
            execute(conn, "insert into document_chunks (document_id, page, chunk_index, content) values (%s,%s,%s,%s)", (doc["id"], page_no, idx, content))
            n_chunks += 1
    if skipped:
        report.skipped_pages[title] = skipped
    if n_chunks == 0:
        execute(conn, "update documents set status = 'failed', page_count = %s where id = %s", (len(pages), doc["id"]))
        report.failed.append(title)
        return
    path = f"documents/{doc['id']}.pdf"
    storage.put(settings.rag_docs_bucket, path, data, "application/pdf")
    execute(
        conn,
        "update documents set status = 'indexed', page_count = %s, storage_path = %s, indexed_at = %s where id = %s",
        (len(pages), path, datetime.now(timezone.utc), doc["id"]),
    )
    report.created.append(title)


def ingest_directory(conn: psycopg.Connection, storage: Storage, settings: Settings, directory: Path) -> IngestReport:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    report = IngestReport()
    for meta in manifest["documents"]:
        ingest_document(conn, storage, settings, (directory / meta["file"]).read_bytes(), meta, report)
    return report
