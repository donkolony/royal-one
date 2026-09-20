"""Identity (`/me`) and adviser-side client management (`/clients`)."""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

import psycopg

from app.core.auth import Principal
from app.core.db import Row, fetch_all, fetch_one
from app.core.errors import not_found, validation
from app.core.http import Paging, order_by
from app.schemas.models import ClientPatch, ProfilePatch
from app.services import audit
from app.services.common import person_ref, require_client_in_scope, update_row


def _adviser_for(conn: psycopg.Connection, client_id: UUID) -> Optional[Dict[str, Any]]:
    row = fetch_one(
        conn,
        "select a.id, a.full_name, a.email, a.phone from clients c join profiles a on a.id = c.adviser_id where c.id = %s",
        (client_id,),
    )
    return person_ref(row) if row else None


def get_me(conn: psycopg.Connection, p: Principal) -> Dict[str, Any]:
    prof = fetch_one(conn, "select id, email, full_name, role, phone, created_at from profiles where id = %s", (p.id,))
    client = None
    if p.is_client:
        c = fetch_one(conn, "select * from clients where id = %s", (p.id,))
        if c:
            client = {
                "id": c["id"],
                "adviser": _adviser_for(conn, p.id),
                "date_of_birth": c["date_of_birth"],
                "drivers_licence_expiry": c["drivers_licence_expiry"],
                "client_since": c["client_since"],
                "last_annual_review_date": c["last_annual_review_date"],
            }
    return {**prof, "client": client, "advisor": {"id": p.id} if p.is_advisor else None, "owner": {"id": p.id} if p.is_owner else None}


def patch_me(conn: psycopg.Connection, p: Principal, body: ProfilePatch) -> Dict[str, Any]:
    fields = body.model_dump(exclude_unset=True)
    if "drivers_licence_expiry" in fields and not p.is_client:
        raise validation("drivers_licence_expiry", "extra_forbidden", "Only clients can set a driver's licence expiry.")
    if "phone" in fields:
        update_row(conn, "profiles", p.id, {"phone": fields["phone"]})
    if "drivers_licence_expiry" in fields:
        update_row(conn, "clients", p.id, {"drivers_licence_expiry": fields["drivers_licence_expiry"]})
    return get_me(conn, p)


_CLIENT_SELECT = """
select p.id, p.full_name, p.email, p.phone, p.created_at,
       c.date_of_birth, c.drivers_licence_expiry, c.client_since, c.last_annual_review_date,
       (select count(*) from policies where client_id = c.id) as n_policies,
       (select count(*) from claims where client_id = c.id and status not in ('draft', 'closed')) as n_open_claims,
       (select count(*) from goal_participants gp join goals g on g.id = gp.goal_id
         where gp.client_id = c.id and g.status = 'active') as n_active_goals,
       (select count(*) from requests where client_id = c.id and status in ('submitted', 'in_progress')) as n_pending_requests,
       (select count(*) from reminders where client_id = c.id and status = 'pending') as n_pending_reminders
from clients c join profiles p on p.id = c.id
"""


def _client_detail(r: Row) -> Dict[str, Any]:
    return {
        "id": r["id"], "full_name": r["full_name"], "email": r["email"], "phone": r["phone"],
        "date_of_birth": r["date_of_birth"], "drivers_licence_expiry": r["drivers_licence_expiry"],
        "client_since": r["client_since"], "last_annual_review_date": r["last_annual_review_date"],
        "counts": {
            "policies": r["n_policies"], "open_claims": r["n_open_claims"], "active_goals": r["n_active_goals"],
            "pending_requests": r["n_pending_requests"], "pending_reminders": r["n_pending_reminders"],
        },
        "created_at": r["created_at"],
    }


def list_clients(conn: psycopg.Connection, p: Principal, paging: Paging, search: Optional[str], sort: Optional[str]) -> Dict[str, Any]:
    order = order_by(sort, {"full_name": "p.full_name", "created_at": "p.created_at"}, "full_name")
    where, params = "c.id = any(%s)", [p.client_ids(conn)]
    if search:
        where += " and (p.full_name ilike %s or p.email ilike %s)"
        like = f"%{search}%"
        params += [like, like]
    total = fetch_one(conn, f"select count(*) as n from clients c join profiles p on p.id = c.id where {where}", params)["n"]
    rows = fetch_all(conn, f"{_CLIENT_SELECT} where {where} order by {order} limit %s offset %s", params + [paging.limit, paging.offset])
    return paging.envelope([_client_detail(r) for r in rows], total)


def get_client(conn: psycopg.Connection, p: Principal, client_id: UUID) -> Dict[str, Any]:
    require_client_in_scope(conn, p, client_id)
    row = fetch_one(conn, f"{_CLIENT_SELECT} where c.id = %s", (client_id,))
    if row is None:
        raise not_found("Client")
    audit.record_view(conn, p, "client.viewed", "client", client_id, client_id=client_id, summary=f"Opened the client file for {row['full_name']}")
    return _client_detail(row)


def patch_client(conn: psycopg.Connection, p: Principal, client_id: UUID, body: ClientPatch) -> Dict[str, Any]:
    require_client_in_scope(conn, p, client_id)
    fields = body.model_dump(exclude_unset=True)
    if "full_name" in fields and fields["full_name"] is None:
        raise validation("full_name", "invalid_value", "full_name cannot be cleared.")
    prof = {k: fields[k] for k in ("full_name", "phone") if k in fields}
    cl = {k: fields[k] for k in ("date_of_birth", "drivers_licence_expiry", "client_since", "last_annual_review_date") if k in fields}
    update_row(conn, "profiles", client_id, prof)
    update_row(conn, "clients", client_id, cl)
    audit.record(conn, p, "client.updated", "client", client_id, client_id=client_id,
                 summary="Updated the client's details", details={"fields": sorted(fields)})
    return get_client(conn, p, client_id)
