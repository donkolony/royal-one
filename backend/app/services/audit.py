"""The audit trail: one append-only, hash-chained log of every meaningful event (docs/AUDIT.md build step 1).

Rules
  * Written by the SERVICE layer, in the same transaction as the change it describes, so the two cannot disagree.
  * `summary` and `details` never carry document text, bank numbers, email bodies or tokens: ids, statuses and counts only.
  * Each row stores sha256(prev_hash + canonical content). `verify_chain` recomputes the chain. Tamper evidence is demo level:
    the database refuses UPDATE/DELETE/TRUNCATE (migration 0003), but an administrator could still drop those triggers.
  * A denied access attempt is written on a SEPARATE connection, because the request's own transaction rolls back when the
    404/403 is raised.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from app.core import clock
from app.core.auth import Principal
from app.core.db import Row, execute, fetch_all, fetch_one
from app.core.errors import validation
from app.core.http import Paging

log = logging.getLogger("app.audit")

GENESIS = ""
_LOCK_KEY = 7_400_115_001       # serialises appends so the chain has one order (pg_advisory_xact_lock)
VIEW_DEDUPE_MINUTES = 10        # a page that polls must not write a row every few seconds
EXPORT_MAX_ROWS = 10_000


def _json_default(o: Any) -> Any:
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, UUID):
        return str(o)
    return str(o)


def _stamp(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def compute_hash(prev_hash: str, e: Dict[str, Any]) -> str:
    """sha256 over the previous hash and the canonical JSON of the entry's content. Pure, so it can be tested."""
    body = {
        "occurred_at": _stamp(e["occurred_at"]),
        "actor_id": str(e["actor_id"]) if e["actor_id"] else None,
        "actor_role": e["actor_role"],
        "action": e["action"],
        "entity_type": e["entity_type"],
        "entity_id": e["entity_id"],
        "client_id": str(e["client_id"]) if e["client_id"] else None,
        "summary": e["summary"],
        "details": e["details"],
        "ip": e["ip"],
        "user_agent": e["user_agent"],
        "request_id": e["request_id"],
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------------------- writing
def record(
    conn: psycopg.Connection, actor: Optional[Principal], action: str, entity_type: str, entity_id: Any = None, *,
    summary: str, client_id: Optional[UUID] = None, details: Optional[Dict[str, Any]] = None, at: Optional[datetime] = None,
) -> int:
    """Append one entry. `actor=None` means the system itself (automation, the insurer simulator, scheduled checks).
    `at` exists only so the demo seed can write believable history; nothing in the API passes it."""
    execute(conn, "select pg_advisory_xact_lock(%s)", (_LOCK_KEY,))
    last = fetch_one(conn, "select hash from audit_log order by id desc limit 1")
    prev = last["hash"] if last else GENESIS
    clean = json.loads(json.dumps(details or {}, default=_json_default))   # what the database will hand back is what is hashed
    entry = {
        "occurred_at": at or clock.now(),
        "actor_id": actor.id if actor else None,
        "actor_role": actor.role if actor else "system",
        "action": action, "entity_type": entity_type,
        "entity_id": str(entity_id) if entity_id is not None else None,
        "client_id": client_id, "summary": summary[:500], "details": clean,
        "ip": actor.ip if actor else None, "user_agent": actor.user_agent if actor else None,
        "request_id": actor.request_id if actor else None,
    }
    row = fetch_one(
        conn,
        "insert into audit_log (occurred_at, actor_id, actor_role, action, entity_type, entity_id, client_id, summary, details, "
        "ip, user_agent, request_id, prev_hash, hash) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) returning id",
        (entry["occurred_at"], entry["actor_id"], entry["actor_role"], action, entity_type, entry["entity_id"], client_id,
         entry["summary"], Jsonb(clean), entry["ip"], entry["user_agent"], entry["request_id"], prev, compute_hash(prev, entry)),
    )
    return row["id"]


def record_view(
    conn: psycopg.Connection, actor: Principal, action: str, entity_type: str, entity_id: Any, *, summary: str,
    client_id: Optional[UUID] = None, details: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """Log that STAFF looked at something. The same person opening the same thing again within a few minutes is not
    logged again, so polling screens do not flood the trail."""
    if actor.is_client:
        return None
    seen = fetch_one(
        conn,
        "select 1 as x from audit_log where actor_id = %s and action = %s and entity_id = %s and occurred_at > %s limit 1",
        (actor.id, action, str(entity_id), clock.now() - timedelta(minutes=VIEW_DEDUPE_MINUTES)),
    )
    if seen:
        return None
    return record(conn, actor, action, entity_type, entity_id, summary=summary, client_id=client_id, details=details)


def record_denied(actor: Principal, entity_type: str, entity_id: Any, *, client_id: Optional[UUID] = None) -> None:
    """Log a refused attempt to open something outside the caller's scope. Best effort: it must never turn a clean 404 into a 500."""
    pool = actor._pool
    if pool is None:
        return
    try:
        with pool.connection() as conn:
            execute(conn, "set local lock_timeout = '2s'")   # never wait long on the chain lock the request itself may hold
            record(conn, actor, "access.denied", entity_type, entity_id, client_id=client_id,
                   summary=f"Refused: {actor.role} tried to open a {entity_type} outside their scope",
                   details={"reason": "outside_scope"})
    except Exception:  # noqa: BLE001 - logging must not break the response
        log.warning("could not record a denied access attempt", exc_info=True)


# --------------------------------------------------------------------------------------------------- reading
_SELECT = """
select l.*, a.full_name as actor_name, c.full_name as client_name
from audit_log l
left join profiles a on a.id = l.actor_id
left join profiles c on c.id = l.client_id
"""


def _scope(conn: psycopg.Connection, p: Principal) -> tuple[str, List[Any]]:
    if p.is_owner:
        return "true", []
    return "(l.client_id = any(%s) or l.actor_id = %s)", [p.client_ids(conn), p.id]


def _filters(
    conn: psycopg.Connection, p: Principal, *, client_id: Optional[UUID], actor_id: Optional[UUID], action: Optional[str],
    entity_type: Optional[str], date_from: Optional[date], date_to: Optional[date], q: Optional[str],
) -> tuple[str, List[Any]]:
    where, params = _scope(conn, p)
    parts = [where]
    if client_id:
        parts.append("l.client_id = %s")
        params.append(client_id)
    if actor_id:
        parts.append("l.actor_id = %s")
        params.append(actor_id)
    if action:
        parts.append("(l.action = %s or l.action like %s)")
        params += [action, action.rstrip(".") + ".%"]
    if entity_type:
        parts.append("l.entity_type = %s")
        params.append(entity_type)
    if date_from:
        parts.append("l.occurred_at >= %s")
        params.append(datetime.combine(date_from, time.min, tzinfo=clock.SAST))
    if date_to:
        parts.append("l.occurred_at < %s")
        params.append(datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=clock.SAST))
    if q:
        parts.append("l.summary ilike %s")
        params.append(f"%{q}%")
    return " and ".join(parts), params


def entry_object(r: Row) -> Dict[str, Any]:
    return {
        "id": r["id"], "occurred_at": r["occurred_at"],
        "actor": {"id": r["actor_id"], "full_name": r["actor_name"] or ("System" if not r["actor_id"] else None), "role": r["actor_role"]},
        "action": r["action"], "entity_type": r["entity_type"], "entity_id": r["entity_id"],
        "client": {"id": r["client_id"], "full_name": r["client_name"]} if r["client_id"] else None,
        "summary": r["summary"], "details": r["details"], "ip": r["ip"], "user_agent": r["user_agent"],
        "request_id": r["request_id"], "hash": r["hash"],
    }


def list_entries(
    conn: psycopg.Connection, p: Principal, paging: Paging, *, client_id: Optional[UUID] = None, actor_id: Optional[UUID] = None,
    action: Optional[str] = None, entity_type: Optional[str] = None, date_from: Optional[date] = None,
    date_to: Optional[date] = None, q: Optional[str] = None,
) -> Dict[str, Any]:
    clause, params = _filters(conn, p, client_id=client_id, actor_id=actor_id, action=action, entity_type=entity_type,
                              date_from=date_from, date_to=date_to, q=q)
    total = fetch_one(conn, f"select count(*) as n from audit_log l where {clause}", params)["n"]
    rows = fetch_all(conn, f"{_SELECT} where {clause} order by l.id desc limit %s offset %s", params + [paging.limit, paging.offset])
    return paging.envelope([entry_object(r) for r in rows], total)


def entries_for_client(conn: psycopg.Connection, client_id: UUID, limit: int = 500) -> List[Dict[str, Any]]:
    """Every entry about one client, newest first. The caller has already checked that the client is in scope."""
    rows = fetch_all(conn, f"{_SELECT} where l.client_id = %s order by l.id desc limit %s", (client_id, limit))
    return [entry_object(r) for r in rows]


def _csv_safe(v: Any) -> str:
    """Neutralise spreadsheet formula injection: a cell that starts with = + - @ is prefixed with an apostrophe."""
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


CSV_COLUMNS = ["id", "occurred_at_utc", "actor", "actor_role", "action", "entity_type", "entity_id", "client", "summary",
               "ip", "request_id", "hash"]


def export_csv(
    conn: psycopg.Connection, p: Principal, *, client_id: Optional[UUID] = None, actor_id: Optional[UUID] = None,
    action: Optional[str] = None, entity_type: Optional[str] = None, date_from: Optional[date] = None,
    date_to: Optional[date] = None, q: Optional[str] = None,
) -> str:
    clause, params = _filters(conn, p, client_id=client_id, actor_id=actor_id, action=action, entity_type=entity_type,
                              date_from=date_from, date_to=date_to, q=q)
    rows = fetch_all(conn, f"{_SELECT} where {clause} order by l.id limit %s", params + [EXPORT_MAX_ROWS])
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(CSV_COLUMNS)
    for r in rows:
        e = entry_object(r)
        w.writerow([_csv_safe(x) for x in (
            e["id"], _stamp(e["occurred_at"]), e["actor"]["full_name"], e["actor"]["role"], e["action"], e["entity_type"],
            e["entity_id"], e["client"]["full_name"] if e["client"] else "", e["summary"], e["ip"], e["request_id"], e["hash"])])
    record(conn, p, "audit.exported", "audit_log", None, client_id=client_id,
           summary=f"Exported {len(rows)} audit entries as CSV", details={"rows": len(rows), "client_id": client_id})
    return out.getvalue()


def verify_chain(conn: psycopg.Connection) -> Dict[str, Any]:
    """Recompute the whole chain. `ok` is false at the first row whose content or link does not match its stored hash."""
    prev, checked = GENESIS, 0
    for r in conn.execute("select * from audit_log order by id").fetchall():
        if r["prev_hash"] != prev or compute_hash(prev, r) != r["hash"]:
            return {"ok": False, "checked": checked, "first_bad_id": r["id"], "head": prev or None}
        prev, checked = r["hash"], checked + 1
    return {"ok": True, "checked": checked, "first_bad_id": None, "head": prev or None}


def parse_date(value: Optional[str], field: str) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise validation(field, "invalid_date", "Enter a date as YYYY-MM-DD.")
