"""System, identity, dashboards, clients, insurers, policies, net worth, financial items, goals, reminders."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query

from app.api.deps import settings_dep
from app.core.auth import Principal, get_principal, require_advisor, require_client, require_staff
from app.core.config import Settings
from app.core.db import get_conn
from app.core.http import Paging, created, no_content, ok
from app.schemas.models import (
    ClientPatch, FinancialItemCreate, FinancialItemPatch, GoalCreate, GoalPatch, PolicyCreate, PolicyPatch,
    ProfilePatch, ReminderCreate, ReminderPatch,
)
from app.services import catalog, clients, dashboards, finance, goals, reminders

router = APIRouter()


# ------------------------------------------------------------------------------------------------ system
@router.get("/meta", tags=["system"])
def meta(settings: Settings = Depends(settings_dep)):
    return ok(catalog.build_meta(settings))


@router.get("/insurers", tags=["reference"])
def insurers(conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(catalog.list_insurers(conn))


# ---------------------------------------------------------------------------------------------- identity
@router.get("/me", tags=["identity"])
def get_me(conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(clients.get_me(conn, p))


@router.patch("/me", tags=["identity"])
def patch_me(body: ProfilePatch, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(clients.patch_me(conn, p, body))


# ------------------------------------------------------------------------------------------- dashboards
@router.get("/me/dashboard", tags=["dashboards"])
def me_dashboard(conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_client)):
    return ok(dashboards.client_dashboard(conn, p, p.id))


@router.get("/advisor/dashboard", tags=["dashboards"])
def advisor_dashboard(conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(dashboards.advisor_dashboard(conn, p))


# ------------------------------------------------------------------------------------- clients (adviser)
@router.get("/clients", tags=["clients"])
def list_clients(
    paging: Paging = Depends(), search: Optional[str] = Query(None, max_length=100), sort: Optional[str] = Query(None),
    conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff),
):
    return ok(clients.list_clients(conn, p, paging, search, sort))


@router.get("/clients/{client_id}", tags=["clients"])
def get_client(client_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff)):
    return ok(clients.get_client(conn, p, client_id))


@router.patch("/clients/{client_id}", tags=["clients"])
def patch_client(client_id: UUID, body: ClientPatch, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(clients.patch_client(conn, p, client_id, body))


@router.get("/clients/{client_id}/dashboard", tags=["clients"])
def client_dashboard(client_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_staff)):
    return ok(dashboards.client_dashboard(conn, p, client_id))


# ------------------------------------------------------------------------------------------------ policies
@router.get("/policies", tags=["policies"])
def list_policies(
    paging: Paging = Depends(), client_id: Optional[UUID] = None,
    category: Optional[Literal["motor", "life", "health", "funeral", "personal_other", "commercial", "investment", "retirement", "disability"]] = None,
    status: Optional[Literal["active", "pending", "lapsed", "cancelled"]] = None, sort: Optional[str] = Query(None),
    conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal),
):
    return ok(catalog.list_policies(conn, p, paging, client_id, category, status, sort))


@router.get("/policies/{policy_id}", tags=["policies"])
def get_policy(policy_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(catalog.get_policy(conn, p, policy_id))


@router.post("/policies", tags=["policies"])
def create_policy(body: PolicyCreate, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    pol = catalog.create_policy(conn, p, body)
    return created(pol, f"/api/v1/policies/{pol['id']}")


@router.patch("/policies/{policy_id}", tags=["policies"])
def patch_policy(policy_id: UUID, body: PolicyPatch, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(catalog.patch_policy(conn, p, policy_id, body))


# ------------------------------------------------------------------------------ net worth + financial items
@router.get("/net-worth", tags=["finance"])
def net_worth(client_id: Optional[UUID] = None, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(finance.net_worth(conn, p, client_id))


@router.get("/financial-items", tags=["finance"])
def list_financial_items(
    paging: Paging = Depends(), client_id: Optional[UUID] = None, kind: Optional[Literal["asset", "liability"]] = None,
    conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal),
):
    return ok(finance.list_items(conn, p, paging, client_id, kind))


@router.post("/financial-items", tags=["finance"])
def create_financial_item(body: FinancialItemCreate, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    item = finance.create_item(conn, p, body)
    return created(item, f"/api/v1/financial-items/{item['id']}")


@router.patch("/financial-items/{item_id}", tags=["finance"])
def patch_financial_item(item_id: UUID, body: FinancialItemPatch, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(finance.patch_item(conn, p, item_id, body))


@router.delete("/financial-items/{item_id}", tags=["finance"])
def delete_financial_item(item_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    finance.delete_item(conn, p, item_id)
    return no_content()


# -------------------------------------------------------------------------------------------------- goals
@router.get("/goals", tags=["goals"])
def list_goals(
    paging: Paging = Depends(), client_id: Optional[UUID] = None,
    status: Literal["active", "achieved", "archived", "all"] = "active", sort: Optional[str] = Query(None),
    conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal),
):
    return ok(goals.list_goals(conn, p, paging, client_id, status, sort))


@router.get("/goals/{goal_id}", tags=["goals"])
def get_goal(goal_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(goals.get_goal(conn, p, goal_id))


@router.post("/goals", tags=["goals"])
def create_goal(body: GoalCreate, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    goal = goals.create_goal(conn, p, body)
    return created(goal, f"/api/v1/goals/{goal['id']}")


@router.patch("/goals/{goal_id}", tags=["goals"])
def patch_goal(goal_id: UUID, body: GoalPatch, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(goals.patch_goal(conn, p, goal_id, body))


@router.delete("/goals/{goal_id}", tags=["goals"])
def delete_goal(goal_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    goals.archive_goal(conn, p, goal_id)
    return no_content()


# ---------------------------------------------------------------------------------------------- reminders
@router.get("/reminders", tags=["reminders"])
def list_reminders(
    paging: Paging = Depends(),
    status: Literal["pending", "done", "dismissed", "all"] = "pending", type: Optional[str] = None,
    audience: Optional[Literal["client", "advisor", "both"]] = None, client_id: Optional[UUID] = None,
    urgency: Optional[Literal["overdue", "due_soon", "upcoming"]] = None, due_from: Optional[date] = None,
    due_to: Optional[date] = None, sort: Optional[str] = Query(None),
    conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal),
):
    return ok(reminders.list_reminders(conn, p, paging, status=status, type_=type, audience=audience, client_id=client_id,
                                       urg=urgency, due_from=due_from, due_to=due_to, sort=sort))


@router.post("/reminders/run-check", tags=["reminders"])
def run_check(conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(reminders.run_check(conn, p))


@router.post("/reminders", tags=["reminders"])
def create_reminder(body: ReminderCreate, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    r = reminders.create_reminder(conn, p, body)
    return created(r, f"/api/v1/reminders/{r['id']}")


@router.patch("/reminders/{reminder_id}", tags=["reminders"])
def patch_reminder(reminder_id: UUID, body: ReminderPatch, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(reminders.patch_reminder(conn, p, reminder_id, body))


@router.post("/reminders/{reminder_id}/complete", tags=["reminders"])
def complete_reminder(reminder_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(get_principal)):
    return ok(reminders.complete_reminder(conn, p, reminder_id))


@router.delete("/reminders/{reminder_id}", tags=["reminders"])
def delete_reminder(reminder_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    reminders.delete_reminder(conn, p, reminder_id)
    return no_content()
