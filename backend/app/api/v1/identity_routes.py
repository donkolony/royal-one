"""The identity vault (docs/api.md section 5.19)."""
from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import settings_dep, storage_dep
from app.core.auth import Principal, get_principal, require_advisor
from app.core.config import Settings
from app.core.db import get_conn
from app.core.http import created, ok
from app.schemas.models import IdentityRejectBody, IdentityVerifyBody
from app.services import identity
from app.storage.base import Storage

router = APIRouter()


@router.get("/identity", tags=["identity-vault"])
def list_identity(client_id: Optional[UUID] = None, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(identity.list_for(conn, p, client_id))


@router.post("/identity", tags=["identity-vault"])
def upload_identity(
    doc_type: str = Form(...), file: UploadFile = File(...), expiry_date: Optional[date] = Form(None), client_id: Optional[UUID] = Form(None),
    conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep), storage: Storage = Depends(storage_dep),
    p: Principal = Depends(get_principal),
):
    data = file.file.read(settings.max_upload_bytes + 1)
    obj = identity.upload(conn, settings, storage, p, client_id=client_id, doc_type=doc_type, expiry_date=expiry_date,
                          filename=file.filename or "file", declared_type=file.content_type, data=data)
    return created(obj, f"/api/v1/identity?client_id={obj['client_id']}")


@router.get("/identity/{document_id}/url", tags=["identity-vault"])
def identity_url(document_id: UUID, conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep),
                 storage: Storage = Depends(storage_dep), p: Principal = Depends(get_principal)):
    return ok(identity.document_url(conn, settings, storage, p, document_id))


@router.post("/identity/{document_id}/verify", tags=["identity-vault"])
def verify_identity(document_id: UUID, body: IdentityVerifyBody, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(identity.verify(conn, p, document_id, body.expiry_date, body.issued_date))


@router.post("/identity/{document_id}/reject", tags=["identity-vault"])
def reject_identity(document_id: UUID, body: IdentityRejectBody, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(identity.reject(conn, p, document_id, body.reason.strip()))
