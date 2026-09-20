"""The audit trail: search, export, and chain verification (docs/api.md section 5.15)."""
from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query, Response

from app.core.auth import Principal, require_owner, require_staff
from app.core.db import get_conn
from app.core.http import Paging, ok
from app.services import audit

router = APIRouter()


def _filters(
    client_id: Optional[UUID] = None, actor_id: Optional[UUID] = None, action: Optional[str] = Query(None, max_length=80),
    entity_type: Optional[str] = Query(None, max_length=40), date_from: Optional[date] = None, date_to: Optional[date] = None,
    q: Optional[str] = Query(None, max_length=100),
) -> dict:
    return dict(client_id=client_id, actor_id=actor_id, action=action, entity_type=entity_type, date_from=date_from,
                date_to=date_to, q=q)


@router.get("/audit", tags=["audit"])
def list_audit(paging: Paging = Depends(), f: dict = Depends(_filters), conn: psycopg.Connection = Depends(get_conn),
               p: Principal = Depends(require_staff)):
    return ok(audit.list_entries(conn, p, paging, **f))


@router.get("/audit/export", tags=["audit"])
def export_audit(f: dict = Depends(_filters), conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff)):
    body = audit.export_csv(conn, p, **f)
    return Response(content=body, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="royal-square-audit-log.csv"'})


@router.get("/audit/verify", tags=["audit"])
def verify_audit(conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_owner)):
    return ok(audit.verify_chain(conn))
