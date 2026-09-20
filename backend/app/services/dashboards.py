"""Dashboards (docs/api.md section 5.3): one call per home screen."""
from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any, Dict, List
from uuid import UUID

import psycopg

from app.core import clock
from app.core.auth import Principal
from app.core.db import fetch_all, fetch_one
from app.core.errors import not_found
from app.domain import constants as C
from app.services import audit, catalog, claims, finance, goals, reminders, requests as requests_svc
from app.services.common import person_ref, require_client_in_scope


def client_dashboard(conn: psycopg.Connection, viewer: Principal, client_id: UUID) -> Dict[str, Any]:
    """The client's dashboard, seen by the client themself or by their adviser."""
    require_client_in_scope(conn, viewer, client_id)
    client = fetch_one(conn, "select id, full_name, email, phone from profiles where id = %s", (client_id,))
    if client is None:
        raise not_found("Client")
    adviser = fetch_one(
        conn, "select a.id, a.full_name, a.email, a.phone from clients c join profiles a on a.id = c.adviser_id where c.id = %s", (client_id,)
    )
    pols = catalog.list_policies_for(conn, [client_id])

    exclude = "'closed'" if viewer.is_client else "'draft', 'closed'"
    audit.record_view(conn, viewer, "client.viewed", "client", client_id, client_id=client_id,
                      summary=f"Opened the client file for {client['full_name']}")
    claim_rows = fetch_all(
        conn,
        f"{claims._SELECT} where c.client_id = %s and c.status not in ({exclude}) order by c.updated_at desc, c.id",
        (client_id,),
    )
    req_rows = fetch_all(
        conn,
        f"{requests_svc._SELECT} where r.client_id = %s and r.status in ('submitted', 'in_progress') order by r.submitted_at desc, r.id",
        (client_id,),
    )
    return {
        "generated_at": clock.now(),
        "client": person_ref(client),
        "adviser": person_ref(adviser) if adviser else None,
        "net_worth": finance.compute_net_worth(conn, [client_id]),
        "policies": {"count": len(pols), "items": pols},
        "open_claims": {"count": len(claim_rows), "items": [claims.summary(r, viewer.role) for r in claim_rows]},
        "goals": {"items": goals.goals_for_clients(conn, [client_id])},
        "reminders": reminders.dashboard_reminders(conn, [client_id], client_view=viewer.is_client, within_days=60, limit=5),
        "pending_requests": {
            "count": len(req_rows),
            "items": [requests_svc.request_object(r, viewer.role) for r in req_rows[:5]],
        },
    }


def _ago(then: datetime) -> str:
    secs = max(0, int((clock.now() - then).total_seconds()))
    if secs < 3600:
        return f"{max(1, secs // 60)} min ago"
    if secs < 86400:
        return f"{secs // 3600} h ago"
    return f"{secs // 86400} d ago"


def _midnight(d) -> datetime:
    return datetime.combine(d, time.min, tzinfo=clock.SAST)


def advisor_dashboard(conn: psycopg.Connection, p: Principal) -> Dict[str, Any]:
    from app.email import service as email_service  # local import: the email module depends on claims data

    ids = p.client_ids(conn)
    today = clock.today()
    reminders.evaluate(conn, ids, today)

    status_counts = {r["status"]: r["n"] for r in fetch_all(
        conn, "select status, count(*) as n from claims where client_id = any(%s) and status <> 'draft' group by status", (ids,))}
    pending_requests = fetch_one(
        conn, "select count(*) as n from requests where client_id = any(%s) and status in ('submitted', 'in_progress')", (ids,))["n"]
    due_7d = fetch_one(
        conn, "select count(*) as n from reminders where client_id = any(%s) and status = 'pending' and due_date between %s and %s",
        (ids, today, today + timedelta(days=7)))["n"]
    overdue_rows = fetch_all(
        conn,
        f"{reminders._SELECT} where r.client_id = any(%s) and r.status = 'pending' and r.due_date < %s order by r.due_date, r.id",
        (ids, today),
    )

    attention: List[Dict[str, Any]] = []
    for r in overdue_rows:
        attention.append({
            "kind": "reminder", "id": r["id"], "title": r["title"],
            "subtitle": f"{r['client_name']} · overdue by {(today - r['due_date']).days} day(s)",
            "client": {"id": r["client_id"], "full_name": r["client_name"]}, "due_at": _midnight(r["due_date"]),
            "link": {"resource": "reminder", "id": r["id"]},
        })
    submitted = fetch_all(
        conn, f"{claims._SELECT} where c.client_id = any(%s) and c.status = 'submitted' order by c.submitted_at, c.id", (ids,))
    for r in submitted:
        attention.append({
            "kind": "claim", "id": r["id"], "title": f"New claim submitted: {r['reference']}",
            "subtitle": f"{r['client_name']} · {r['insurer_name'] or 'insurer not set'} · submitted {_ago(r['submitted_at'])}",
            "client": {"id": r["client_id"], "full_name": r["client_name"]}, "due_at": None,
            "link": {"resource": "claim", "id": r["id"]},
        })
    new_requests = fetch_all(
        conn, f"{requests_svc._SELECT} where r.client_id = any(%s) and r.status = 'submitted' order by r.submitted_at, r.id", (ids,))
    for r in new_requests:
        label = C.REQUEST_TYPE_BY_NAME[r["type"]]["label"]
        attention.append({
            "kind": "request", "id": r["id"], "title": f"New request: {label}",
            "subtitle": f"{r['client_name']} · submitted {_ago(r['submitted_at'])}",
            "client": {"id": r["client_id"], "full_name": r["client_name"]}, "due_at": None,
            "link": {"resource": "request", "id": r["id"]},
        })
    for t in email_service.flagged_unread(conn, p):
        attention.append({
            "kind": "email", "id": t["id"], "title": t["subject"], "subtitle": f"Flagged email · {_ago(t['last_message_at'])}",
            "client": t.get("client"), "due_at": None, "link": {"resource": "email_thread", "id": t["id"]},
        })
    stale = fetch_all(
        conn,
        f"{claims._SELECT} where c.client_id = any(%s) and c.status in ('registered', 'assessment', 'quotes', 'authorised', 'in_repair', 'completed') "
        "and c.status_changed_at <= now() - interval '7 days' order by c.status_changed_at, c.id",
        (ids,),
    )
    for r in stale:
        days = (clock.now() - r["status_changed_at"]).days
        attention.append({
            "kind": "claim", "id": r["id"], "title": f"Claim {r['reference']} has been in '{C.STATUS_BY_VALUE[r['status']]['advisor_label']}' for {days} days",
            "subtitle": f"{r['client_name']} · {r['insurer_name'] or 'insurer not set'}",
            "client": {"id": r["client_id"], "full_name": r["client_name"]}, "due_at": None,
            "link": {"resource": "claim", "id": r["id"]},
        })

    return {
        "generated_at": clock.now(),
        "counts": {
            "clients": len(ids),
            "open_claims": sum(n for s, n in status_counts.items() if s != "closed"),
            "pending_requests": pending_requests,
            "reminders_due_7d": due_7d,
            "overdue_reminders": len(overdue_rows),
        },
        "claims_by_status": [
            {"status": s, "label": C.STATUS_BY_VALUE[s]["advisor_label"], "count": status_counts.get(s, 0)} for s in C.PIPELINE_STATUSES
        ],
        "needs_attention": attention[:10],
        "upcoming_reminders": reminders.dashboard_reminders(conn, ids, client_view=False, within_days=14, limit=10)["upcoming"],
    }
