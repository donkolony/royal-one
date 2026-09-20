"""Compliance: advice records, consents, the client compliance pack, timelines, retention (docs/api.md section 5.20)."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Response

from app.api.deps import llm_dep, settings_dep
from app.core.auth import Principal, get_principal, require_advisor, require_client, require_owner, require_staff
from app.core.config import Settings
from app.core.db import get_conn
from app.core.http import created, ok
from app.core.rate_limit import llm_rate_limit
from app.llm.base import LLMRouter
from app.schemas.models import AcknowledgeBody, AdviceDraftBody, AdviceRecordBody, ConsentBody
from app.services import advice, audit, compliance, consents

router = APIRouter()


# ---------------------------------------------------------------------------------------------- advice records
@router.get("/advice-records", tags=["compliance"])
def list_advice(client_id: Optional[UUID] = None, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(advice.list_records(conn, p, client_id))


@router.post("/advice-records/draft", tags=["compliance"])
def draft_advice(body: AdviceDraftBody, conn: psycopg.Connection = Depends(get_conn), llm: LLMRouter = Depends(llm_dep), p: Principal = Depends(llm_rate_limit)):
    return ok(advice.draft(conn, llm, p, body))


@router.post("/advice-records", tags=["compliance"])
def record_advice(body: AdviceRecordBody, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    r = advice.record(conn, p, body)
    return created(r, f"/api/v1/advice-records?client_id={body.client_id}")


@router.post("/advice-records/{record_id}/acknowledge", tags=["compliance"])
def acknowledge(record_id: UUID, body: AcknowledgeBody, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(advice.acknowledge(conn, p, record_id, body.method))


# ------------------------------------------------------------------------------------------------------ consents
@router.get("/consents", tags=["compliance"])
def list_consents(client_id: Optional[UUID] = None, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(consents.list_for(conn, p, client_id))


@router.post("/consents", tags=["compliance"])
def change_consent(body: ConsentBody, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(consents.change(conn, p, body.client_id, body.purpose, body.status, body.method))


# ------------------------------------------------------------------------------------- pack, timeline, overview
@router.get("/clients/{client_id}/compliance", tags=["compliance"])
def compliance_pack(client_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff)):
    return ok(compliance.build_pack(conn, p, client_id, fmt="json"))


@router.get("/clients/{client_id}/compliance/pack.pdf", tags=["compliance"])
def compliance_pack_pdf(client_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff)):
    pack = compliance.build_pack(conn, p, client_id, fmt="pdf")
    return Response(content=compliance.render_pdf(pack), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{pack["reference"]}.pdf"'})


@router.get("/clients/{client_id}/timeline", tags=["compliance"])
def client_timeline(client_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff)):
    return ok(compliance.timeline(conn, p, client_id))


@router.get("/me/timeline", tags=["compliance"])
def my_timeline(conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_client)):
    return ok(compliance.timeline(conn, p, None))


@router.get("/compliance/overview", tags=["compliance"])
def compliance_overview(conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff)):
    return ok(compliance.overview(conn, p))


@router.get("/compliance/retention", tags=["compliance"])
def retention(conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep), p: Principal = Depends(require_owner)):
    return ok(compliance.retention_review(conn, p, settings))
