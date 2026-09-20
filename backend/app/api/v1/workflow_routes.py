"""Workflow definitions, in-app notifications, and the DEMO controls (docs/api.md sections 5.18 and 5.19)."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query, Request
from pydantic import model_validator

from app.api.deps import settings_dep, storage_dep
from app.core.auth import Principal, get_principal, require_owner, require_staff
from app.core.config import Settings
from app.core.db import get_conn
from app.core.errors import ApiError, validation
from app.core.http import ok
from app.domain import workflows as W
from app.schemas.models import Body
from app.services import audit, insurer_sim, requests as requests_svc, workflow
from app.storage.base import Storage

router = APIRouter()


# ---------------------------------------------------------------------------------------------------- workflows
@router.get("/workflows", tags=["workflows"])
def list_workflows(p: Principal = Depends(get_principal)):
    return ok({"items": W.public_definitions()})


# ------------------------------------------------------------------------------------------------ notifications
@router.get("/notifications", tags=["notifications"])
def list_notifications(unread: bool = False, limit: int = Query(30, ge=1, le=100), conn: psycopg.Connection = Depends(get_conn),
                       p: Principal = Depends(get_principal)):
    return ok(workflow.list_notifications(conn, p, limit, unread))


@router.post("/notifications/read-all", tags=["notifications"])
def read_all(conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(workflow.mark_all_read(conn, p))


@router.post("/notifications/{notification_id}/read", tags=["notifications"])
def read_one(notification_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(workflow.mark_read(conn, p, notification_id))


# ------------------------------------------------------------------------------------------------- demo controls
class InsurerStepBody(Body):
    claim_id: Optional[UUID] = None
    request_id: Optional[UUID] = None

    @model_validator(mode="after")
    def _exactly_one(self) -> "InsurerStepBody":
        if (self.claim_id is None) == (self.request_id is None):
            raise ValueError("Send exactly one of claim_id or request_id.")
        return self


def _demo_only(settings: Settings) -> None:
    if not settings.demo_mode:
        raise ApiError(404, "not_found", "Route not found.")     # indistinguishable from a route that does not exist


@router.post("/demo/insurer-step", tags=["demo"])
def insurer_step(body: InsurerStepBody, conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep),
                 storage: Storage = Depends(storage_dep), p: Principal = Depends(require_staff)):
    """DEMO ONLY. The simulated insurer (or product provider) takes its next step on a claim or request."""
    _demo_only(settings)
    if body.claim_id:
        return ok(insurer_sim.step_claim(conn, settings, storage, p, body.claim_id))
    return ok(requests_svc.provider_step(conn, settings, storage, p, body.request_id))


@router.post("/demo/reset", tags=["demo"])
def reset_demo(request: Request, conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep),
               storage: Storage = Depends(storage_dep), p: Principal = Depends(require_owner)):
    """DEMO ONLY. Put every data table back to the seeded state (the approved-document library is kept)."""
    _demo_only(settings)
    from app import seed

    seed.reset_data(conn, keep_documents=True)
    seed.seed_all(conn, settings, storage)
    audit.record(conn, p, "demo.reset", "system", None, summary="The demo data was reset to the seeded state")
    return ok({"reset": True, "message": "Demo data reset to the seeded state."})
