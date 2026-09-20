"""The approved-document library (adviser only, docs/api.md section 5.12)."""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, Optional
from uuid import UUID

import psycopg

from app.core import clock
from app.core.auth import Principal
from app.core.config import Settings
from app.core.db import Row, fetch_all, fetch_one
from app.core.errors import not_found
from app.core.http import Paging, order_by
from app.services import audit
from app.storage.base import Storage

_SELECT = "select d.*, i.name as insurer_name from documents d left join insurers i on i.id = d.insurer_id"


def document_object(r: Row) -> Dict[str, Any]:
    return {
        "id": r["id"], "title": r["title"], "category": r["category"],
        "insurer": {"id": r["insurer_id"], "name": r["insurer_name"]} if r["insurer_id"] else None,
        "page_count": r["page_count"], "version_label": r["version_label"], "is_synthetic": r["is_synthetic"],
        "source_note": r["source_note"], "status": r["status"], "indexed_at": r["indexed_at"],
    }


def list_documents(conn: psycopg.Connection, paging: Paging, category: Optional[str], insurer_id: Optional[UUID], search: Optional[str], sort: Optional[str]) -> Dict[str, Any]:
    order = order_by(sort, {"title": "d.title", "indexed_at": "d.indexed_at"}, "title")
    where, params = ["true"], []
    if category:
        where.append("d.category = %s")
        params.append(category)
    if insurer_id:
        where.append("d.insurer_id = %s")
        params.append(insurer_id)
    if search:
        where.append("d.title ilike %s")
        params.append(f"%{search}%")
    clause = " and ".join(where)
    total = fetch_one(conn, f"select count(*) as n from documents d where {clause}", params)["n"]
    rows = fetch_all(conn, f"{_SELECT} where {clause} order by {order}, d.id limit %s offset %s", params + [paging.limit, paging.offset])
    return paging.envelope([document_object(r) for r in rows], total)


def _load(conn: psycopg.Connection, document_id: UUID) -> Row:
    row = fetch_one(conn, f"{_SELECT} where d.id = %s", (document_id,))
    if row is None:
        raise not_found("Document")
    return row


def get_document(conn: psycopg.Connection, document_id: UUID) -> Dict[str, Any]:
    return document_object(_load(conn, document_id))


def document_url(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, document_id: UUID) -> Dict[str, Any]:
    row = _load(conn, document_id)
    if not row["storage_path"] or row["status"] != "indexed":
        raise not_found("Document file")
    audit.record(conn, p, "document.viewed", "rag_document", document_id, summary=f"Opened the approved document '{row['title']}'",
                 details={"title": row["title"]})
    return {
        "url": storage.signed_url(settings.rag_docs_bucket, row["storage_path"], settings.signed_url_ttl_seconds),
        "expires_at": clock.now() + timedelta(seconds=settings.signed_url_ttl_seconds),
        "content_type": "application/pdf",
    }
