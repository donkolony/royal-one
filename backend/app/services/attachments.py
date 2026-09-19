"""Uploading and reading attachments (claims and requests). Validation order (ARCHITECT 7.2):
size, then content signature, then signature vs declared type, then allowed types for the `kind`."""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import psycopg

from app.core import clock
from app.core.auth import Principal
from app.core.config import Settings
from app.core.db import Row, fetch_all, fetch_one
from app.core.errors import ApiError, validation
from app.domain import constants as C
from app.storage.base import Storage, safe_filename
from app.storage.sniff import sniff_content_type


def attachment_objects(conn: psycopg.Connection, settings: Settings, storage: Storage, rows: List[Row]) -> List[Dict[str, Any]]:
    urls = storage.signed_urls(settings.attachments_bucket, [r["storage_path"] for r in rows], settings.signed_url_ttl_seconds)
    expires = clock.now() + timedelta(seconds=settings.signed_url_ttl_seconds)
    return [
        {
            "id": r["id"], "kind": r["kind"], "label": r["label"], "filename": r["filename"],
            "content_type": r["content_type"], "size_bytes": r["size_bytes"], "uploaded_by": r["uploaded_by"],
            "uploaded_at": r["uploaded_at"], "url": urls[r["storage_path"]], "url_expires_at": expires,
        }
        for r in rows
    ]


def list_for(conn: psycopg.Connection, settings: Settings, storage: Storage, *, claim_id: Optional[UUID] = None, request_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
    col, val = ("claim_id", claim_id) if claim_id else ("request_id", request_id)
    rows = fetch_all(conn, f"select * from attachments where {col} = %s order by uploaded_at, id", (val,))
    return attachment_objects(conn, settings, storage, rows)


def kinds_for_claim(conn: psycopg.Connection, claim_id: UUID) -> set:
    return {r["kind"] for r in fetch_all(conn, "select distinct kind from attachments where claim_id = %s", (claim_id,))}


def validate_upload(kind: str, declared_type: Optional[str], data: bytes, max_bytes: int) -> str:
    """Return the verified content type, or raise the API error the contract specifies."""
    if kind not in C.ATTACHMENT_KINDS:
        raise validation("kind", "invalid_value", f"kind must be one of: {', '.join(C.ATTACHMENT_KINDS)}.")
    if len(data) == 0:
        raise validation("file", "required", "The file is empty.")
    if len(data) > max_bytes:
        raise ApiError(413, "payload_too_large", f"Files can be at most {max_bytes // (1024 * 1024)} MB.")
    sniffed = sniff_content_type(data)
    if sniffed is None:
        raise ApiError(415, "unsupported_media_type", "This file type is not supported.")
    declared = (declared_type or "").split(";")[0].strip().lower()
    if declared != sniffed:
        raise ApiError(415, "unsupported_media_type", "The file content does not match its declared type.")
    if sniffed not in C.allowed_content_types(kind):
        raise ApiError(415, "unsupported_media_type", f"A {kind} cannot be a {sniffed} file.")
    return sniffed


def store(
    conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, *, claim_id: Optional[UUID] = None,
    request_id: Optional[UUID] = None, kind: str, label: Optional[str], filename: str, declared_type: Optional[str],
    data: bytes, max_count: int,
) -> Dict[str, Any]:
    content_type = validate_upload(kind, declared_type, data, settings.max_upload_bytes)
    col, val = ("claim_id", claim_id) if claim_id else ("request_id", request_id)
    n = fetch_one(conn, f"select count(*) as n from attachments where {col} = %s", (val,))["n"]
    if n >= max_count:
        raise validation("file", "too_many", f"At most {max_count} attachments are allowed here.")
    att_id = uuid4()
    prefix = f"claims/{claim_id}" if claim_id else f"requests/{request_id}"
    path = f"{prefix}/{att_id}-{safe_filename(filename)}"
    # Insert first, store second: if the upload fails the exception rolls the row back.
    row = fetch_one(
        conn,
        "insert into attachments (id, claim_id, request_id, kind, label, storage_path, filename, content_type, size_bytes, uploaded_by) "
        "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) returning *",
        (att_id, claim_id, request_id, kind, label, path, safe_filename(filename), content_type, len(data), p.id),
    )
    storage.put(settings.attachments_bucket, path, data, content_type)
    return attachment_objects(conn, settings, storage, [row])[0]
