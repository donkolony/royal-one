"""The workflow engine (docs/AUDIT.md build step 4, brief section C).

The definitions are data (domain/workflows.py). This module is the small amount of code that reads them:
  * `transitions`     what a person in a given role may do next, and what is still missing (one table for offering AND enforcing)
  * `notices_for`     who must be told when a status changes
  * `tell`            write the in-app notifications (there is no email or SMS in this build, docs/api.md 1.9)
  * request timelines the same idea as a claim's, so a client never has to chase

The claim and the request services call it; neither hard-codes a status table any more.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import psycopg

from app.core.auth import Principal
from app.core.db import Row, execute, fetch_all, fetch_one
from app.core.errors import not_found
from app.domain import workflows as W
from psycopg.types.json import Jsonb


def _blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


# ------------------------------------------------------------------------------------------------- transitions
def transitions(status: str, role: str, facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The motor-claim moves available from `status` to `role`. `facts` supplies the values a transition `requires`:
    "missing_fields" is the draft's list of unfilled required fields; any other name is looked up and must be non-blank."""
    out = []
    for t in W.MOTOR_CLAIM_TRANSITIONS:
        if t.from_status != status or t.actor != role:
            continue
        unmet: List[str] = []
        for need in t.requires:
            if need == "missing_fields":
                unmet += list(facts.get("missing_fields", []))
            elif _blank(facts.get(need)):
                unmet.append(need)
        label = t.label.format(label=W.STATUS_BY_VALUE[t.to_status]["advisor_label"].lower()) if "{label}" in t.label else t.label
        out.append({"to_status": t.to_status, "direction": t.direction, "label": label, "requires": unmet, "actor": t.actor})
    return out


def claim_notices(from_status: str, to_status: str, actor: str) -> Tuple[W.Notice, ...]:
    for t in W.MOTOR_CLAIM_TRANSITIONS:
        if (t.from_status, t.to_status, t.actor) == (from_status, to_status, actor):
            return t.notify
    return ()


def request_transition_notices(from_status: str, to_status: str) -> Tuple[W.Notice, ...]:
    for t in W.REQUEST_TRANSITIONS:
        if (t.from_status, t.to_status) == (from_status, to_status):
            return t.notify
    return ()


def request_move_allowed(from_status: str, to_status: str) -> bool:
    return any((t.from_status, t.to_status) == (from_status, to_status) for t in W.REQUEST_TRANSITIONS)


# ---------------------------------------------------------------------------------------------- notifications
def _recipient(conn: psycopg.Connection, to: str, client_id: UUID) -> Optional[UUID]:
    if to == "client":
        return client_id
    row = fetch_one(conn, "select adviser_id from clients where id = %s", (client_id,))
    return row["adviser_id"] if row else None


def tell(conn: psycopg.Connection, notices: Tuple[W.Notice, ...], client_id: UUID, ctx: Dict[str, Any], *, kind: str, link: Dict[str, Any]) -> None:
    """Write one notification per notice. Placeholders in title and body come from `ctx`."""
    for n in notices:
        who = _recipient(conn, n.to, client_id)
        if who is None:
            continue
        execute(conn, "insert into notifications (recipient_id, kind, title, body, link, client_id) values (%s,%s,%s,%s,%s,%s)",
                (who, kind, n.title.format(**ctx), n.body.format(**ctx) or None, Jsonb(link, dumps=lambda o: json.dumps(o, default=str)), client_id))


def tell_one(conn: psycopg.Connection, to: str, client_id: UUID, *, kind: str, title: str, body: Optional[str], link: Dict[str, Any]) -> None:
    tell(conn, (W.Notice(to, title.replace("{", "{{").replace("}", "}}"), (body or "").replace("{", "{{").replace("}", "}}")),), client_id, {}, kind=kind, link=link)


def list_notifications(conn: psycopg.Connection, p: Principal, limit: int = 30, unread_only: bool = False) -> Dict[str, Any]:
    where = "recipient_id = %s" + (" and read_at is null" if unread_only else "")
    rows = fetch_all(conn, f"select id, kind, title, body, link, client_id, created_at, read_at from notifications where {where} order by created_at desc limit %s", (p.id, limit))
    unread = fetch_one(conn, "select count(*) as n from notifications where recipient_id = %s and read_at is null", (p.id,))["n"]
    return {"items": rows, "unread_count": unread}


def mark_read(conn: psycopg.Connection, p: Principal, notification_id: UUID) -> Dict[str, Any]:
    if execute(conn, "update notifications set read_at = coalesce(read_at, now()) where id = %s and recipient_id = %s", (notification_id, p.id)) == 0:
        raise not_found("Notification")
    return {"ok": True}


def mark_all_read(conn: psycopg.Connection, p: Principal) -> Dict[str, Any]:
    n = execute(conn, "update notifications set read_at = now() where recipient_id = %s and read_at is null", (p.id,))
    return {"marked": n}


# ---------------------------------------------------------------------------------------------- request timeline
def add_request_event(
    conn: psycopg.Connection, request_id: UUID, type_: str, title: str, *, message: Optional[str] = None, visible: bool = True,
    from_status: Optional[str] = None, to_status: Optional[str] = None, actor_id: Optional[UUID] = None,
) -> None:
    execute(conn, "insert into request_events (request_id, type, title, message, visible_to_client, from_status, to_status, actor_id) values (%s,%s,%s,%s,%s,%s,%s,%s)",
            (request_id, type_, title, message, visible, from_status, to_status, actor_id))


def request_timeline(conn: psycopg.Connection, request_id: UUID, client_view: bool) -> List[Dict[str, Any]]:
    sql = ("select e.*, a.full_name as actor_name, a.role as actor_role from request_events e left join profiles a on a.id = e.actor_id "
           "where e.request_id = %s" + (" and e.visible_to_client" if client_view else "") + " order by e.created_at, e.id")
    return [{
        "id": r["id"], "type": r["type"], "title": r["title"], "message": r["message"], "visible_to_client": r["visible_to_client"],
        "from_status": r["from_status"], "to_status": r["to_status"], "created_at": r["created_at"],
        "actor": {"id": r["actor_id"], "full_name": r["actor_name"], "role": r["actor_role"]} if r["actor_id"] else None,
    } for r in fetch_all(conn, sql, (request_id,))]
