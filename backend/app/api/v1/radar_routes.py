"""Opportunity Radar (docs/api.md section 5.16)."""
from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query

from app.api.deps import llm_dep
from app.core.auth import Principal, require_advisor, require_staff
from app.core.db import get_conn
from app.core.http import Paging, created, ok
from app.core.rate_limit import llm_rate_limit
from app.llm.base import LLMRouter
from app.schemas.models import LifeEventBody, OutcomeBody, OutreachBody, OutreachDraftBody, SnoozeBody
from app.services import radar

router = APIRouter()


# Static paths first: they must be registered before /opportunities/{opportunity_id}.
@router.get("/opportunities/summary", tags=["opportunities"])
def summary(conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff)):
    return ok(radar.summary(conn, p))


@router.get("/opportunities/assumptions", tags=["opportunities"])
def assumptions(p: Principal = Depends(require_staff)):
    return ok(radar.assumptions())


@router.get("/opportunities", tags=["opportunities"])
def list_opportunities(
    paging: Paging = Depends(), status: Literal["live", "open", "snoozed", "actioned", "won", "lost", "expired", "all"] = "live",
    signal: Optional[str] = Query(None, max_length=40), client_id: Optional[UUID] = None, adviser_id: Optional[UUID] = None,
    sort: Literal["value", "surfaced"] = "value", conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff),
):
    return ok(radar.list_opportunities(conn, p, paging, status=status, signal=signal, client_id=client_id, adviser_id=adviser_id, sort=sort))


@router.get("/opportunities/{opportunity_id}", tags=["opportunities"])
def get_opportunity(opportunity_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff)):
    return ok(radar.get_opportunity(conn, p, opportunity_id))


@router.post("/opportunities/{opportunity_id}/task", tags=["opportunities"])
def create_task(opportunity_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(radar.create_task(conn, p, opportunity_id))


@router.post("/opportunities/{opportunity_id}/draft", tags=["opportunities"])
def draft(opportunity_id: UUID, body: OutreachDraftBody, conn: psycopg.Connection = Depends(get_conn), llm: LLMRouter = Depends(llm_dep),
          p: Principal = Depends(llm_rate_limit)):
    return ok(radar.draft(conn, llm, p, opportunity_id, body.channel))


@router.post("/opportunities/{opportunity_id}/outreach", tags=["opportunities"])
def outreach(opportunity_id: UUID, body: OutreachBody, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(radar.log_outreach(conn, p, opportunity_id, body.channel, body.note))


@router.post("/opportunities/{opportunity_id}/snooze", tags=["opportunities"])
def snooze(opportunity_id: UUID, body: SnoozeBody, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(radar.snooze(conn, p, opportunity_id, body.days))


@router.post("/opportunities/{opportunity_id}/outcome", tags=["opportunities"])
def outcome(opportunity_id: UUID, body: OutcomeBody, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(radar.record_outcome(conn, p, opportunity_id, body.outcome, body.reason.strip(), body.actual_annual_value_cents))


@router.post("/opportunities/{opportunity_id}/reopen", tags=["opportunities"])
def reopen(opportunity_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(radar.reopen(conn, p, opportunity_id))


@router.get("/clients/{client_id}/life-events", tags=["opportunities"])
def list_life_events(client_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff)):
    return ok(radar.list_life_events(conn, p, client_id))


@router.post("/clients/{client_id}/life-events", tags=["opportunities"])
def record_life_event(client_id: UUID, body: LifeEventBody, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    ev = radar.record_life_event(conn, p, client_id, body.kind, body.occurred_on, body.note)
    return created(ev, f"/api/v1/clients/{client_id}/life-events")
