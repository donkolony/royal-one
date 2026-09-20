"""Motor claims and client requests."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.api.deps import settings_dep, storage_dep
from app.core.auth import Principal, get_principal, require_advisor, require_client, require_staff
from app.core.config import Settings
from app.core.db import get_conn
from app.core.errors import validation
from app.core.http import Paging, created, no_content, ok
from app.domain import constants as C
from app.schemas.models import (
    ClaimCreate, ClaimPatch, HireCarPatch, InsurerDetailsPatch, RepairDateBody, RepairDetailsPatch, RequestCreate,
    RequestPatch, ReviewBody, TransitionBody, UpdateBody,
)
from app.services import claims, requests as requests_svc
from app.storage.base import Storage

router = APIRouter()


def _read_upload(file: UploadFile, settings: Settings, label: Optional[str]) -> bytes:
    if label is not None and len(label) > 120:
        raise validation("label", "too_long", "Use at most 120 characters.")
    return file.file.read(settings.max_upload_bytes + 1)  # one extra byte so oversize is detected without buffering it all


# ------------------------------------------------------------------------------------------------ claims
@router.get("/claims/checklist", tags=["claims"])
def checklist(p: Principal = Depends(get_principal)):
    return ok({"items": C.CHECKLIST})


@router.get("/claims/pipeline", tags=["claims"])
def pipeline(client_id: Optional[UUID] = None, include_closed: bool = False,
             conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff)):
    return ok(claims.pipeline(conn, p, client_id, include_closed))


@router.post("/claims", tags=["claims"])
def create_claim(body: ClaimCreate, conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep),
                 storage: Storage = Depends(storage_dep), p: Principal = Depends(require_client)):
    claim = claims.create_draft(conn, settings, storage, p, body)
    return created(claim, f"/api/v1/claims/{claim['id']}")


@router.get("/claims", tags=["claims"])
def list_claims(
    paging: Paging = Depends(), client_id: Optional[UUID] = None, status: List[str] = Query(default=[]),
    open: Optional[bool] = None, search: Optional[str] = Query(None, max_length=100), sort: Optional[str] = Query(None),
    conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal),
):
    return ok(claims.list_claims(conn, p, paging, client_id=client_id, statuses=status, open_=open, search=search, sort=sort))


@router.get("/claims/{claim_id}", tags=["claims"])
def get_claim(claim_id: UUID, conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep),
              storage: Storage = Depends(storage_dep), p: Principal = Depends(get_principal)):
    return ok(claims.open_claim(conn, settings, storage, p, claim_id))


@router.patch("/claims/{claim_id}", tags=["claims"])
def patch_claim(claim_id: UUID, body: ClaimPatch, conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep),
                storage: Storage = Depends(storage_dep), p: Principal = Depends(require_client)):
    return ok(claims.patch_draft(conn, settings, storage, p, claim_id, body))


@router.post("/claims/{claim_id}/attachments", tags=["claims"])
def upload_claim_attachment(
    claim_id: UUID, file: UploadFile = File(...), kind: str = Form(...), label: Optional[str] = Form(None),
    conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep),
    storage: Storage = Depends(storage_dep), p: Principal = Depends(require_client),
):
    data = _read_upload(file, settings, label)
    obj = claims.upload_attachment(conn, settings, storage, p, claim_id, kind=kind, label=label or None,
                                   filename=file.filename or "file", declared_type=file.content_type, data=data)
    return created(obj, f"/api/v1/claims/{claim_id}")


@router.delete("/claims/{claim_id}/attachments/{attachment_id}", tags=["claims"])
def delete_claim_attachment(claim_id: UUID, attachment_id: UUID, conn: psycopg.Connection = Depends(get_conn),
                            settings: Settings = Depends(settings_dep), storage: Storage = Depends(storage_dep),
                            p: Principal = Depends(require_client)):
    claims.delete_attachment(conn, settings, storage, p, claim_id, attachment_id)
    return no_content()


@router.post("/claims/{claim_id}/submit", tags=["claims"])
def submit_claim(claim_id: UUID, conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep),
                 storage: Storage = Depends(storage_dep), p: Principal = Depends(require_client)):
    return ok(claims.submit(conn, settings, storage, p, claim_id))


@router.patch("/claims/{claim_id}/insurer-details", tags=["claims"])
def insurer_details(claim_id: UUID, body: InsurerDetailsPatch, conn: psycopg.Connection = Depends(get_conn),
                    settings: Settings = Depends(settings_dep), storage: Storage = Depends(storage_dep),
                    p: Principal = Depends(require_advisor)):
    return ok(claims.patch_insurer_details(conn, settings, storage, p, claim_id, body))


@router.post("/claims/{claim_id}/transitions", tags=["claims"])
def transition(claim_id: UUID, body: TransitionBody, conn: psycopg.Connection = Depends(get_conn),
               settings: Settings = Depends(settings_dep), storage: Storage = Depends(storage_dep),
               p: Principal = Depends(require_advisor)):
    return ok(claims.transition(conn, settings, storage, p, claim_id, body))


@router.patch("/claims/{claim_id}/repair-details", tags=["claims"])
def repair_details(claim_id: UUID, body: RepairDetailsPatch, conn: psycopg.Connection = Depends(get_conn),
                   settings: Settings = Depends(settings_dep), storage: Storage = Depends(storage_dep),
                   p: Principal = Depends(require_advisor)):
    return ok(claims.patch_repair_details(conn, settings, storage, p, claim_id, body))


@router.post("/claims/{claim_id}/repair-date", tags=["claims"])
def repair_date(claim_id: UUID, body: RepairDateBody, conn: psycopg.Connection = Depends(get_conn),
                settings: Settings = Depends(settings_dep), storage: Storage = Depends(storage_dep),
                p: Principal = Depends(require_client)):
    return ok(claims.choose_repair_date(conn, settings, storage, p, claim_id, body))


@router.patch("/claims/{claim_id}/hire-car", tags=["claims"])
def hire_car(claim_id: UUID, body: HireCarPatch, conn: psycopg.Connection = Depends(get_conn),
             settings: Settings = Depends(settings_dep), storage: Storage = Depends(storage_dep),
             p: Principal = Depends(require_advisor)):
    return ok(claims.patch_hire_car(conn, settings, storage, p, claim_id, body))


@router.post("/claims/{claim_id}/updates", tags=["claims"])
def post_update(claim_id: UUID, body: UpdateBody, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    ev = claims.post_update(conn, p, claim_id, body)
    return created(ev, f"/api/v1/claims/{claim_id}")


@router.post("/claims/{claim_id}/review", tags=["claims"])
def review(claim_id: UUID, body: ReviewBody, conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep),
           storage: Storage = Depends(storage_dep), p: Principal = Depends(require_client)):
    return ok(claims.review(conn, settings, storage, p, claim_id, body))


# ---------------------------------------------------------------------------------------------- requests
@router.get("/requests/types", tags=["requests"])
def request_types(p: Principal = Depends(get_principal)):
    return ok(requests_svc.list_types())


@router.post("/requests", tags=["requests"])
def create_request(body: RequestCreate, conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep),
                   storage: Storage = Depends(storage_dep), p: Principal = Depends(require_client)):
    req = requests_svc.create(conn, settings, storage, p, body)
    return created(req, f"/api/v1/requests/{req['id']}")


@router.get("/requests", tags=["requests"])
def list_requests(
    paging: Paging = Depends(), client_id: Optional[UUID] = None, type: Optional[str] = None,
    status: List[str] = Query(default=[]), open: Optional[bool] = None, sort: Optional[str] = Query(None),
    conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal),
):
    return ok(requests_svc.list_requests(conn, p, paging, client_id=client_id, type_=type, statuses=status, open_=open, sort=sort))


@router.get("/requests/{request_id}", tags=["requests"])
def get_request(request_id: UUID, conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep),
                storage: Storage = Depends(storage_dep), p: Principal = Depends(get_principal)):
    return ok(requests_svc.get_request(conn, settings, storage, p, request_id))


@router.patch("/requests/{request_id}", tags=["requests"])
def patch_request(request_id: UUID, body: RequestPatch, conn: psycopg.Connection = Depends(get_conn),
                  settings: Settings = Depends(settings_dep), storage: Storage = Depends(storage_dep),
                  p: Principal = Depends(require_advisor)):
    return ok(requests_svc.patch_request(conn, settings, storage, p, request_id, body))


@router.post("/requests/{request_id}/attachments", tags=["requests"])
def upload_request_attachment(
    request_id: UUID, file: UploadFile = File(...), kind: str = Form("other"), label: Optional[str] = Form(None),
    conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep),
    storage: Storage = Depends(storage_dep), p: Principal = Depends(require_client),
):
    data = _read_upload(file, settings, label)
    obj = requests_svc.upload_attachment(conn, settings, storage, p, request_id, kind=kind, label=label or None,
                                         filename=file.filename or "file", declared_type=file.content_type, data=data)
    return created(obj, f"/api/v1/requests/{request_id}")
