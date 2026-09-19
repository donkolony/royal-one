"""Goals (docs/api.md section 5.8). Progress = min(100, round(current / target * 100, 1))."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

import psycopg

from app.core.auth import Principal
from app.core.db import Row, execute, fetch_all, fetch_one
from app.core.errors import not_found, validation
from app.core.http import Paging, order_by
from app.schemas.models import GoalCreate, GoalPatch
from app.services.common import progress_percent, resolve_client_filter, update_row


def _participants(conn: psycopg.Connection, goal_ids: List[UUID]) -> Dict[UUID, List[Dict[str, Any]]]:
    rows = fetch_all(
        conn,
        "select gp.goal_id, gp.client_id, p.full_name from goal_participants gp join profiles p on p.id = gp.client_id "
        "where gp.goal_id = any(%s) order by p.full_name",
        (goal_ids,),
    )
    out: Dict[UUID, List[Dict[str, Any]]] = {g: [] for g in goal_ids}
    for r in rows:
        out[r["goal_id"]].append({"client_id": r["client_id"], "full_name": r["full_name"]})
    return out


def goal_objects(conn: psycopg.Connection, rows: List[Row]) -> List[Dict[str, Any]]:
    parts = _participants(conn, [r["id"] for r in rows])
    return [
        {
            "id": r["id"], "title": r["title"], "description": r["description"], "category": r["category"],
            "type": "shared" if len(parts[r["id"]]) > 1 else "individual",
            "status": r["status"], "target_amount_cents": r["target_amount_cents"],
            "current_amount_cents": r["current_amount_cents"],
            "progress_percent": progress_percent(r["current_amount_cents"], r["target_amount_cents"]),
            "target_date": r["target_date"], "participants": parts[r["id"]], "created_by": r["created_by"],
            "created_at": r["created_at"], "updated_at": r["updated_at"],
        }
        for r in rows
    ]


def goals_for_clients(conn: psycopg.Connection, client_ids: List[UUID], status: Optional[str] = "active") -> List[Dict[str, Any]]:
    sql = "select distinct g.* from goals g join goal_participants gp on gp.goal_id = g.id where gp.client_id = any(%s)"
    params: List[Any] = [client_ids]
    if status and status != "all":
        sql += " and g.status = %s"
        params.append(status)
    return goal_objects(conn, fetch_all(conn, sql + " order by g.target_date nulls last, g.title", params))


def list_goals(conn: psycopg.Connection, p: Principal, paging: Paging, client_id: Optional[UUID], status: str, sort: Optional[str]) -> Dict[str, Any]:
    ids = resolve_client_filter(conn, p, client_id)
    order = order_by(sort, {"target_date": "g.target_date", "updated_at": "g.updated_at"}, "target_date")
    where, params = "gp.client_id = any(%s)", [ids]
    if status != "all":
        where += " and g.status = %s"
        params.append(status)
    base = f"from goals g where g.id in (select gp.goal_id from goal_participants gp join goals g on g.id = gp.goal_id where {where})"
    total = fetch_one(conn, f"select count(*) as n {base}", params)["n"]
    rows = fetch_all(conn, f"select g.* {base} order by {order} nulls last, g.id limit %s offset %s", params + [paging.limit, paging.offset])
    return paging.envelope(goal_objects(conn, rows), total)


def get_goal(conn: psycopg.Connection, p: Principal, goal_id: UUID) -> Dict[str, Any]:
    row = fetch_one(
        conn,
        "select g.* from goals g where g.id = %s and exists "
        "(select 1 from goal_participants gp where gp.goal_id = g.id and gp.client_id = any(%s))",
        (goal_id, p.client_ids(conn)),
    )
    if row is None:
        raise not_found("Goal")
    return goal_objects(conn, [row])[0]


def _check_participants(conn: psycopg.Connection, p: Principal, ids: List[UUID]) -> None:
    allowed = set(p.client_ids(conn))
    bad = [str(i) for i in ids if i not in allowed]
    if bad:
        # Not revealing whether the client exists: it is simply not one of the adviser's clients.
        raise validation("client_ids", "invalid_value", "Every client must be one of your assigned clients.")


def _set_participants(conn: psycopg.Connection, goal_id: UUID, ids: List[UUID]) -> None:
    execute(conn, "delete from goal_participants where goal_id = %s", (goal_id,))
    for cid in ids:
        execute(conn, "insert into goal_participants (goal_id, client_id) values (%s, %s)", (goal_id, cid))


def create_goal(conn: psycopg.Connection, p: Principal, body: GoalCreate) -> Dict[str, Any]:
    _check_participants(conn, p, body.client_ids)
    status = "achieved" if body.current_amount_cents >= body.target_amount_cents else "active"
    row = fetch_one(
        conn,
        "insert into goals (title, description, category, status, target_amount_cents, current_amount_cents, target_date, created_by) "
        "values (%s,%s,%s,%s,%s,%s,%s,%s) returning id",
        (body.title, body.description, body.category, status, body.target_amount_cents, body.current_amount_cents, body.target_date, p.id),
    )
    _set_participants(conn, row["id"], body.client_ids)
    return get_goal(conn, p, row["id"])


def patch_goal(conn: psycopg.Connection, p: Principal, goal_id: UUID, body: GoalPatch) -> Dict[str, Any]:
    current = get_goal(conn, p, goal_id)  # 404 when not a participant-visible goal
    fields = body.model_dump(exclude_unset=True)
    for k in ("title", "category", "target_amount_cents", "current_amount_cents", "status"):
        if k in fields and fields[k] is None:
            raise validation(k, "invalid_value", f"{k} cannot be cleared.")
    client_ids = fields.pop("client_ids", None)
    if client_ids is not None:
        if len(set(client_ids)) != len(client_ids):
            raise validation("client_ids", "invalid_value", "client_ids must be distinct.")
        _check_participants(conn, p, client_ids)
    target = fields.get("target_amount_cents", current["target_amount_cents"])
    cur = fields.get("current_amount_cents", current["current_amount_cents"])
    status = fields.get("status", current["status"])
    if status == "active" and cur >= target:
        fields["status"] = "achieved"  # api.md 5.8 side effect
    elif status == "achieved" and cur < target and "status" not in body.model_fields_set:
        fields["status"] = "active"
    update_row(conn, "goals", goal_id, fields)
    if client_ids is not None:
        _set_participants(conn, goal_id, client_ids)
    return get_goal(conn, p, goal_id)


def archive_goal(conn: psycopg.Connection, p: Principal, goal_id: UUID) -> None:
    get_goal(conn, p, goal_id)
    update_row(conn, "goals", goal_id, {"status": "archived"})
