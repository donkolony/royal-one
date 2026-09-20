"""The owner's Business Health view and per-client health (docs/api.md section 5.17)."""
from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query

from app.core.auth import Principal, require_owner, require_staff
from app.core.db import get_conn
from app.core.http import Paging, ok
from app.services import owner

router = APIRouter()


@router.get("/owner/business-health", tags=["owner"])
def business_health(conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_owner)):
    return ok(owner.business_health(conn, p))


@router.get("/owner/drilldown", tags=["owner"])
def drilldown(metric: str = Query(..., max_length=60), paging: Paging = Depends(), conn: psycopg.Connection = Depends(get_conn),
              p: Principal = Depends(require_owner)):
    return ok(owner.drilldown(conn, p, metric, paging))


@router.get("/clients/{client_id}/health", tags=["clients"])
def client_health(client_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff)):
    return ok(owner.client_health_for(conn, p, client_id))
