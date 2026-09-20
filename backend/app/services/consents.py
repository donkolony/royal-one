"""Consents (docs/AUDIT.md build step 6): an append-only history; the current state is the newest row per purpose.

`NOTICE_VERSION` names the privacy notice text the client saw. The notice is a DRAFT FOR LEGAL REVIEW (docs/api.md 5.20 and the in-app
privacy page); recording a consent here is a record of what the person said, not a claim that the firm's process is compliant.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

import psycopg

from app.core.auth import Principal
from app.core.db import fetch_all, fetch_one
from app.core.errors import forbidden, validation
from app.services import audit, workflow
from app.services.common import require_client_in_scope

PURPOSES = {
    "data_processing": "Use my personal information to provide and administer my policies, claims and advice.",
    "marketing": "Contact me about other products and services that may suit me.",
    "insurer_sharing": "Share my information with my insurers and product providers so they can process my policies and claims.",
}
NOTICE_VERSION = "v1-demo-draft"


def current(conn: psycopg.Connection, client_id: UUID) -> Dict[str, Optional[Dict[str, Any]]]:
    rows = fetch_all(conn, "select distinct on (purpose) purpose, status, method, notice_version, recorded_at from consents where client_id = %s "
                           "order by purpose, recorded_at desc", (client_id,))
    by = {r["purpose"]: r for r in rows}
    return {k: ({"status": by[k]["status"], "method": by[k]["method"], "notice_version": by[k]["notice_version"], "recorded_at": by[k]["recorded_at"]} if k in by else None)
            for k in PURPOSES}


def list_for(conn: psycopg.Connection, p: Principal, client_id: Optional[UUID]) -> Dict[str, Any]:
    cid = p.id if p.is_client else client_id
    if cid is None:
        raise validation("client_id", "required", "client_id is required.")
    if not p.is_client:
        require_client_in_scope(conn, p, cid)
    hist = fetch_all(conn, "select c.id, c.purpose, c.status, c.method, c.notice_version, c.recorded_at, u.full_name as recorded_by from consents c "
                           "left join profiles u on u.id = c.recorded_by where c.client_id = %s order by c.recorded_at desc, c.id", (cid,))
    return {"client_id": cid, "notice_version": NOTICE_VERSION, "notice_is_draft": True, "purposes": PURPOSES, "current": current(conn, cid), "history": hist}


def change(conn: psycopg.Connection, p: Principal, client_id: Optional[UUID], purpose: str, status: str, method: str) -> Dict[str, Any]:
    if p.is_client:
        cid = p.id
        if method != "in_app":
            raise validation("method", "invalid_value", "You record your own consent in the app.")
    elif p.is_advisor:
        if client_id is None:
            raise validation("client_id", "required", "client_id is required.")
        cid = require_client_in_scope(conn, p, client_id)
        if method == "in_app":
            raise validation("method", "invalid_value", "An adviser records a consent taken in person or in writing.")
    else:
        raise forbidden("The owner cannot record a consent on someone else's behalf.")
    fetch_one(conn, "insert into consents (client_id, purpose, status, notice_version, method, recorded_by) values (%s,%s,%s,%s,%s,%s) returning id",
              (cid, purpose, status, NOTICE_VERSION, method, p.id))
    audit.record(conn, p, "consent.changed", "consent", None, client_id=cid, summary=f"Consent for '{purpose}' {status}",
                 details={"purpose": purpose, "status": status, "method": method, "notice_version": NOTICE_VERSION})
    if p.is_client and status == "withdrawn":
        workflow.tell_one(conn, "advisor", cid, kind="consent", title=f"{p.full_name} withdrew a consent", body=f"Purpose: {purpose.replace('_', ' ')}.",
                          link={"resource": "client", "id": cid})
    return list_for(conn, p, cid)
