"""Reminders (docs/api.md section 5.9).

Rule-based reminders are computed on read (ARCHITECT section 6): `evaluate` is idempotent, so calling it on every
list/dashboard request is safe. `dedupe_key` (unique) makes concurrent evaluations harmless.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import psycopg

from app.core import clock
from app.core.auth import Principal
from app.core.db import Row, execute, fetch_all, fetch_one
from app.core.errors import bad_state, conflict, not_found, validation
from app.core.http import Paging, order_by
from app.domain import constants as C
from app.schemas.models import ReminderCreate, ReminderPatch
from app.services.common import require_client_in_scope, resolve_client_filter, update_row


# ------------------------------------------------------------------------------------------ date helpers
def _with_year(d: date, year: int) -> date:
    try:
        return d.replace(year=year)
    except ValueError:  # 29 February in a non-leap year
        return date(year, 2, 28)


def add_years(d: date, years: int) -> date:
    return _with_year(d, d.year + years)


def next_occurrence(d: date, today: date) -> date:
    candidate = _with_year(d, today.year)
    return candidate if candidate >= today else _with_year(d, today.year + 1)


def fmt(d: date) -> str:
    return f"{d.day} {d.strftime('%b %Y')}"


# --------------------------------------------------------------------------------------------- candidates
@dataclass(frozen=True)
class Candidate:
    type: str
    client_id: UUID
    related_resource: str
    related_id: UUID
    due: date
    audience: str
    title: str
    description: Optional[str] = None

    @property
    def group(self) -> Tuple[str, UUID, UUID]:
        return (self.type, self.client_id, self.related_id)

    @property
    def dedupe_key(self) -> str:
        return f"{self.type}:{self.client_id}:{self.related_id}:{self.due.isoformat()}"


def compute_candidates(conn: psycopg.Connection, client_ids: List[UUID], today: date) -> List[Candidate]:
    out: List[Candidate] = []
    clients = fetch_all(
        conn,
        "select c.*, p.full_name from clients c join profiles p on p.id = c.id where c.id = any(%s)",
        (client_ids,),
    )
    for c in clients:
        cid, name = c["id"], c["full_name"]
        if c["drivers_licence_expiry"]:
            d = c["drivers_licence_expiry"]
            out.append(Candidate("licence_expiry", cid, "client", cid, d, "client",
                                 f"Driving licence expires on {fmt(d)}", "Renew it before it expires to stay covered while driving."))
        if c["last_annual_review_date"]:
            d = add_years(c["last_annual_review_date"], 1)
            out.append(Candidate("annual_review", cid, "client", cid, d, "advisor",
                                 f"Annual financial review due for {name}", f"Last review: {fmt(c['last_annual_review_date'])}."))
        if c["date_of_birth"]:
            d = next_occurrence(c["date_of_birth"], today)
            out.append(Candidate("birthday", cid, "client", cid, d, "advisor", f"{name}'s birthday on {fmt(d)}"))
        if c["client_since"]:
            d = next_occurrence(c["client_since"], today)
            if d.year > c["client_since"].year:
                out.append(Candidate("anniversary", cid, "client", cid, d, "advisor",
                                     f"{name}: {d.year - c['client_since'].year} year(s) as a client on {fmt(d)}"))

    pols = fetch_all(
        conn,
        "select id, client_id, product_name, category, status, renewal_date, valuation_certificate_date from policies "
        "where client_id = any(%s) and status in ('active', 'pending')",
        (client_ids,),
    )
    for p in pols:
        if p["valuation_certificate_date"]:
            d = add_years(p["valuation_certificate_date"], 2)
            out.append(Candidate("valuation_certificate", p["client_id"], "policy", p["id"], d, "both",
                                 f"Valuation certificate due for {p['product_name']}",
                                 f"The last certificate is dated {fmt(p['valuation_certificate_date'])}."))
        if p["category"] == "retirement" and p["status"] == "active" and p["renewal_date"]:
            d = p["renewal_date"]
            out.append(Candidate("retirement_fee_renewal", p["client_id"], "policy", p["id"], d, "advisor",
                                 f"Retirement fee renewal: {p['product_name']}"))

    claims = fetch_all(
        conn,
        "select id, client_id, incident_occurred_at, created_at from claims "
        "where client_id = any(%s) and status in ('draft', 'submitted') and coalesce(police_reported, false) = false",
        (client_ids,),
    )
    for cl in claims:
        base: datetime = cl["incident_occurred_at"] or cl["created_at"]
        d = (base + timedelta(hours=C.POLICE_REPORT_WINDOW_HOURS)).astimezone(clock.SAST).date()
        out.append(Candidate("claim_police_report", cl["client_id"], "claim", cl["id"], d, "client",
                             "Report the accident to the police within 48 hours",
                             "Keep the police case number. You will need it for your claim."))
    return out


def _in_window(c: Candidate, today: date) -> bool:
    lead = C.REMINDER_TYPE_BY_NAME[c.type]["lead_days"] or 0
    return (c.due - today).days <= lead and (today - c.due).days <= C.MAX_OVERDUE_DAYS


def evaluate(conn: psycopg.Connection, client_ids: List[UUID], today: Optional[date] = None) -> Dict[str, int]:
    today = today or clock.today()
    if not client_ids:
        return {"evaluated_clients": 0, "created": 0, "already_existing": 0}
    candidates = compute_candidates(conn, client_ids, today)

    # Dismiss pending rule reminders whose source date changed or no longer applies.
    current = {c.group: c.due for c in candidates}
    stale = fetch_all(
        conn,
        "select id, type, client_id, related_id, due_date from reminders "
        "where client_id = any(%s) and source = 'rule' and status = 'pending'",
        (client_ids,),
    )
    for r in stale:
        if current.get((r["type"], r["client_id"], r["related_id"])) != r["due_date"]:
            execute(conn, "update reminders set status = 'dismissed', updated_at = now() where id = %s", (r["id"],))

    created = existing = 0
    for c in candidates:
        if not _in_window(c, today):
            continue
        row = fetch_one(
            conn,
            "insert into reminders (client_id, type, title, description, due_date, audience, source, related_resource, related_id, dedupe_key) "
            "values (%s,%s,%s,%s,%s,%s,'rule',%s,%s,%s) on conflict (dedupe_key) do nothing returning id",
            (c.client_id, c.type, c.title, c.description, c.due, c.audience, c.related_resource, c.related_id, c.dedupe_key),
        )
        if row:
            created += 1
        else:
            existing += 1
    return {"evaluated_clients": len(client_ids), "created": created, "already_existing": existing}


# --------------------------------------------------------------------------------------------- serialisation
_SELECT = "select r.*, p.full_name as client_name from reminders r join profiles p on p.id = r.client_id"


def urgency(due: date, today: date) -> str:
    if due < today:
        return "overdue"
    if (due - today).days <= C.DUE_SOON_DAYS:
        return "due_soon"
    return "upcoming"


def reminder_object(r: Row, today: date) -> Dict[str, Any]:
    return {
        "id": r["id"], "type": r["type"], "title": r["title"], "description": r["description"],
        "due_date": r["due_date"], "audience": r["audience"], "status": r["status"],
        "urgency": urgency(r["due_date"], today), "source": r["source"],
        "client": {"id": r["client_id"], "full_name": r["client_name"]},
        "related": {"resource": r["related_resource"], "id": r["related_id"]} if r["related_id"] else None,
        "completed_at": r["completed_at"], "created_at": r["created_at"],
    }


def _load(conn: psycopg.Connection, p: Principal, reminder_id: UUID) -> Row:
    sql, params = f"{_SELECT} where r.id = %s and r.client_id = any(%s)", [reminder_id, p.client_ids(conn)]
    if p.is_client:
        sql += " and r.audience in ('client', 'both')"
    row = fetch_one(conn, sql, params)
    if row is None:
        raise not_found("Reminder")
    return row


# --------------------------------------------------------------------------------------------- operations
def list_reminders(
    conn: psycopg.Connection, p: Principal, paging: Paging, *, status: str, type_: Optional[str], audience: Optional[str],
    client_id: Optional[UUID], urg: Optional[str], due_from: Optional[date], due_to: Optional[date], sort: Optional[str],
) -> Dict[str, Any]:
    ids = resolve_client_filter(conn, p, client_id)
    evaluate(conn, ids)
    today = clock.today()
    order = order_by(sort, {"due_date": "r.due_date"}, "due_date")
    where, params = ["r.client_id = any(%s)"], [ids]
    if p.is_client:
        where.append("r.audience in ('client', 'both')")
    elif audience:
        where.append("r.audience = %s")
        params.append(audience)
    if status != "all":
        where.append("r.status = %s")
        params.append(status)
    if type_:
        where.append("r.type = %s")
        params.append(type_)
    if due_from:
        where.append("r.due_date >= %s")
        params.append(due_from)
    if due_to:
        where.append("r.due_date <= %s")
        params.append(due_to)
    if urg == "overdue":
        where.append("r.due_date < %s")
        params.append(today)
    elif urg == "due_soon":
        where.append("r.due_date >= %s and r.due_date <= %s")
        params += [today, today + timedelta(days=C.DUE_SOON_DAYS)]
    elif urg == "upcoming":
        where.append("r.due_date > %s")
        params.append(today + timedelta(days=C.DUE_SOON_DAYS))
    clause = " and ".join(where)
    total = fetch_one(conn, f"select count(*) as n from reminders r where {clause}", params)["n"]
    rows = fetch_all(conn, f"{_SELECT} where {clause} order by {order}, r.id limit %s offset %s", params + [paging.limit, paging.offset])
    return paging.envelope([reminder_object(r, today) for r in rows], total)


def dashboard_reminders(conn: psycopg.Connection, client_ids: List[UUID], client_view: bool, within_days: int, limit: int) -> Dict[str, Any]:
    """Pending reminders due within `within_days` (overdue ones included), soonest first, plus the overdue count."""
    evaluate(conn, client_ids)
    today = clock.today()
    aud = " and r.audience in ('client', 'both')" if client_view else ""
    base = f"r.client_id = any(%s) and r.status = 'pending'{aud}"
    overdue = fetch_one(conn, f"select count(*) as n from reminders r where {base} and r.due_date < %s", (client_ids, today))["n"]
    rows = fetch_all(
        conn,
        f"{_SELECT} where {base} and r.due_date <= %s order by r.due_date, r.id limit %s",
        (client_ids, today + timedelta(days=within_days), limit),
    )
    return {"overdue_count": overdue, "upcoming": [reminder_object(r, today) for r in rows]}


def create_reminder(conn: psycopg.Connection, p: Principal, body: ReminderCreate) -> Dict[str, Any]:
    require_client_in_scope(conn, p, body.client_id)
    row = fetch_one(
        conn,
        "insert into reminders (client_id, type, title, description, due_date, audience, source, created_by) "
        "values (%s,%s,%s,%s,%s,%s,'manual',%s) returning id",
        (body.client_id, body.type, body.title, body.description, body.due_date, body.audience, p.id),
    )
    return reminder_object(_load(conn, p, row["id"]), clock.today())


def patch_reminder(conn: psycopg.Connection, p: Principal, reminder_id: UUID, body: ReminderPatch) -> Dict[str, Any]:
    _load(conn, p, reminder_id)
    fields = body.model_dump(exclude_unset=True)
    for k in ("title", "due_date", "audience", "status"):
        if k in fields and fields[k] is None:
            raise validation(k, "invalid_value", f"{k} cannot be cleared.")
    if fields.get("status") == "pending":
        fields["completed_at"] = None
    update_row(conn, "reminders", reminder_id, fields)
    return reminder_object(_load(conn, p, reminder_id), clock.today())


def complete_reminder(conn: psycopg.Connection, p: Principal, reminder_id: UUID) -> Dict[str, Any]:
    row = _load(conn, p, reminder_id)
    if row["status"] != "pending":
        raise bad_state(f"This reminder is already {row['status']}.")
    execute(conn, "update reminders set status = 'done', completed_at = now(), completed_by = %s, updated_at = now() where id = %s", (p.id, reminder_id))
    return reminder_object(_load(conn, p, reminder_id), clock.today())


def delete_reminder(conn: psycopg.Connection, p: Principal, reminder_id: UUID) -> None:
    row = _load(conn, p, reminder_id)
    if row["source"] != "manual":
        raise conflict("Reminders created by the system cannot be deleted. Dismiss them instead.")
    execute(conn, "delete from reminders where id = %s", (reminder_id,))


def run_check(conn: psycopg.Connection, p: Principal) -> Dict[str, int]:
    return evaluate(conn, p.client_ids(conn))
