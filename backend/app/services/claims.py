"""Motor claims (docs/api.md section 5.10): drafts, submission, tracking, the adviser pipeline.

The status table in `allowed_transitions` is the single source for what the API offers AND what it enforces.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import psycopg

from app.core import clock
from app.core.auth import Principal
from app.core.config import Settings
from app.core.db import Row, execute, fetch_all, fetch_one
from app.core.errors import bad_state, field_error, not_found, validation, validation_many
from app.core.http import Paging, order_by
from app.domain import constants as C
from app.schemas.models import (
    ClaimCreate, ClaimPatch, HireCarPatch, InsurerDetailsPatch, RepairDateBody, RepairDetailsPatch, ReviewBody,
    TransitionBody, UpdateBody,
)
from app.services import attachments as att
from app.services.common import insurer_ref, resolve_client_filter, update_row
from app.storage.base import Storage

_SELECT = """
select c.*, cl.full_name as client_name, i.name as insurer_name
from claims c
join profiles cl on cl.id = c.client_id
left join insurers i on i.id = c.insurer_id
"""


# ------------------------------------------------------------------------------------------ loading
def load_claim(conn: psycopg.Connection, p: Principal, claim_id: UUID, lock: bool = False) -> Row:
    """Load one claim within the caller's scope. Advisers never see drafts (api.md 2.3)."""
    sql = f"{_SELECT} where c.id = %s and c.client_id = any(%s)"
    if p.is_advisor:
        sql += " and c.status <> 'draft'"
    if lock:
        sql += " for update of c"
    row = fetch_one(conn, sql, (claim_id, p.client_ids(conn)))
    if row is None:
        raise not_found("Claim")
    return row


def status_label(status: str, role: str) -> str:
    return C.STATUS_BY_VALUE[status]["client_label" if role == "client" else "advisor_label"]


def summary(row: Row, role: str) -> Dict[str, Any]:
    return {
        "id": row["id"], "reference": row["reference"],
        "client": {"id": row["client_id"], "full_name": row["client_name"]},
        "insurer": insurer_ref(row), "status": row["status"], "status_label": status_label(row["status"], role),
        "claim_number": row["insurer_claim_number"], "incident_occurred_at": row["incident_occurred_at"],
        "incident_location_text": row["incident_location_text"], "hire_car_status": row["hire_car_status"],
        "days_in_status": max(0, (clock.now() - row["status_changed_at"]).days),
        "submitted_at": row["submitted_at"], "updated_at": row["updated_at"],
    }


# ---------------------------------------------------------------------------- rules: missing fields
_MISSING_MESSAGES = {
    "insurer_id": "Choose your insurer.",
    "incident.occurred_at": "Enter the date and time of the incident.",
    "incident.location_text": "Enter where it happened.",
    "incident.description": "Describe what happened.",
    "police.reported": "Say whether you reported it to the police.",
    "police.case_number": "Enter the police case number.",
    "driver.is_policyholder": "Say whether the policyholder was driving.",
    "driver.full_name": "Enter the driver's name.",
    "driver.relationship_to_policyholder": "Say how the driver is related to the policyholder.",
    "vehicle_use": "Say whether the vehicle was used for personal or business use.",
    "attachments.photo": "Add at least one photo.",
    "attachments.drivers_licence": "Upload the driver's licence.",
}


def _blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def missing_fields(row: Row, kinds: set) -> List[str]:
    """Paths still required to submit. One function used by GET/PATCH (progress) and submit (enforcement)."""
    out: List[str] = []
    if row["insurer_id"] is None:
        out.append("insurer_id")
    for path, col in (("incident.occurred_at", "incident_occurred_at"), ("incident.location_text", "incident_location_text"),
                      ("incident.description", "incident_description")):
        if _blank(row[col]):
            out.append(path)
    if row["police_reported"] is None:
        out.append("police.reported")
    elif row["police_reported"] and _blank(row["police_case_number"]):
        out.append("police.case_number")
    if row["driver_is_policyholder"] is None:
        out.append("driver.is_policyholder")
    if _blank(row["driver_full_name"]):
        out.append("driver.full_name")
    if row["driver_is_policyholder"] is False and _blank(row["driver_relationship"]):
        out.append("driver.relationship_to_policyholder")
    if row["vehicle_use"] is None:
        out.append("vehicle_use")
    if not (kinds & C.PHOTO_KINDS):
        out.append("attachments.photo")
    if "drivers_licence" not in kinds:
        out.append("attachments.drivers_licence")
    return out


# ---------------------------------------------------------------------------- rules: transitions
def allowed_transitions(row: Row, role: str, missing: List[str]) -> List[Dict[str, Any]]:
    status = row["status"]
    idx = C.STATUS_ORDER.index(status)
    if role == "client":
        if status == "draft":
            return [{"to_status": "submitted", "direction": "forward", "label": "Send to Royal Square", "requires": missing, "actor": "client"}]
        if status == "completed":
            return [{"to_status": "closed", "direction": "forward", "label": "Sign off and close", "requires": [], "actor": "client"}]
        return []
    out: List[Dict[str, Any]] = []
    if 1 <= idx <= 7:
        to = C.STATUS_ORDER[idx + 1]
        requires = ["insurer_details.claim_number"] if to == "registered" and _blank(row["insurer_claim_number"]) else []
        out.append({"to_status": to, "direction": "forward", "label": C.FORWARD_LABELS[to], "requires": requires, "actor": "advisor"})
    if 2 <= idx <= 7:
        prev = C.STATUS_ORDER[idx - 1]
        out.append({"to_status": prev, "direction": "back", "label": f"Move back to {C.STATUS_BY_VALUE[prev]['advisor_label'].lower()}", "requires": [], "actor": "advisor"})
    return out


def _police(row: Row) -> Dict[str, Any]:
    base = row["incident_occurred_at"] or row["created_at"]
    deadline = base + timedelta(hours=C.POLICE_REPORT_WINDOW_HOURS)
    if row["police_reported"] is True:
        state = "met"
    elif row["status"] not in ("draft", "submitted"):
        state = "not_applicable"
    else:
        state = "overdue" if clock.now() > deadline else "pending"
    return {
        "reported": row["police_reported"], "case_number": row["police_case_number"], "station": row["police_station"],
        "reported_at": row["police_reported_at"], "report_deadline_at": deadline, "deadline_status": state,
    }


def _timeline(conn: psycopg.Connection, claim_id: UUID, client_view: bool) -> List[Dict[str, Any]]:
    sql = (
        "select e.*, a.full_name as actor_name, a.role as actor_role from claim_events e "
        "left join profiles a on a.id = e.actor_id where e.claim_id = %s"
    )
    if client_view:
        sql += " and e.visible_to_client"
    return [event_object(r) for r in fetch_all(conn, sql + " order by e.created_at, e.id", (claim_id,))]


def event_object(r: Row) -> Dict[str, Any]:
    return {
        "id": r["id"], "type": r["type"], "title": r["title"], "message": r["message"],
        "visible_to_client": r["visible_to_client"], "from_status": r["from_status"], "to_status": r["to_status"],
        "actor": {"id": r["actor_id"], "full_name": r["actor_name"], "role": r["actor_role"]} if r["actor_id"] else None,
        "created_at": r["created_at"],
    }


def detail(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, row: Row) -> Dict[str, Any]:
    role = p.role
    kinds = att.kinds_for_claim(conn, row["id"])
    missing = missing_fields(row, kinds) if row["status"] == "draft" else []
    review = None
    if row["review_rating"] is not None:
        review = {"rating": row["review_rating"], "comment": row["review_comment"], "submitted_at": row["review_submitted_at"]}
    out = summary(row, role)
    out.update({
        "policy_id": row["policy_id"],
        "incident": {
            "occurred_at": row["incident_occurred_at"], "location_text": row["incident_location_text"],
            "location_lat": row["incident_location_lat"], "location_lng": row["incident_location_lng"],
            "description": row["incident_description"],
        },
        "police": _police(row),
        "driver": {
            "is_policyholder": row["driver_is_policyholder"], "full_name": row["driver_full_name"],
            "relationship_to_policyholder": row["driver_relationship"],
        },
        "vehicle_use": row["vehicle_use"],
        "witnesses": row["witnesses"], "third_parties": row["third_parties"],
        "insurer_details": {
            "claim_number": row["insurer_claim_number"], "handler_name": row["insurer_handler_name"],
            "handler_email": row["insurer_handler_email"], "handler_phone": row["insurer_handler_phone"],
        },
        "repair": {
            "repairer_name": row["repair_repairer_name"], "repairer_phone": row["repair_repairer_phone"],
            "quote_amount_cents": row["repair_quote_amount_cents"], "authorised_amount_cents": row["repair_authorised_amount_cents"],
            "drop_off_date": row["repair_drop_off_date"], "estimated_completion_date": row["repair_estimated_completion_date"],
            "completed_at": row["repair_completed_at"],
        },
        "hire_car": {
            "status": row["hire_car_status"], "provider": row["hire_car_provider"],
            "delivery_date": row["hire_car_delivery_date"], "return_date": row["hire_car_return_date"],
        },
        "review": review,
        "missing_fields": missing,
        "allowed_transitions": allowed_transitions(row, role, missing),
        "attachments": att.list_for(conn, settings, storage, claim_id=row["id"]),
        "timeline": _timeline(conn, row["id"], client_view=p.is_client),
        "created_at": row["created_at"], "closed_at": row["closed_at"],
    })
    return out


def get_claim(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, claim_id: UUID) -> Dict[str, Any]:
    return detail(conn, settings, storage, p, load_claim(conn, p, claim_id))


def add_event(
    conn: psycopg.Connection, claim_id: UUID, type_: str, title: str, *, message: Optional[str] = None, visible: bool = True,
    from_status: Optional[str] = None, to_status: Optional[str] = None, actor_id: Optional[UUID] = None,
) -> Row:
    return fetch_one(
        conn,
        "insert into claim_events (claim_id, type, title, message, visible_to_client, from_status, to_status, actor_id) "
        "values (%s,%s,%s,%s,%s,%s,%s,%s) returning id",
        (claim_id, type_, title, message, visible, from_status, to_status, actor_id),
    )


# ------------------------------------------------------------------------------------------- lists
def list_claims(
    conn: psycopg.Connection, p: Principal, paging: Paging, *, client_id: Optional[UUID], statuses: List[str], open_: Optional[bool],
    search: Optional[str], sort: Optional[str],
) -> Dict[str, Any]:
    ids = resolve_client_filter(conn, p, client_id)
    order = order_by(sort, {"updated_at": "c.updated_at", "submitted_at": "c.submitted_at"}, "-updated_at")
    where, params = ["c.client_id = any(%s)"], [ids]
    if p.is_advisor:
        where.append("c.status <> 'draft'")
    if statuses:
        for s in statuses:
            if s not in C.STATUS_ORDER:
                raise validation("status", "invalid_value", f"Unknown status '{s}'.")
        where.append("c.status = any(%s)")
        params.append(statuses)
    if open_:
        where.append("c.status not in ('draft', 'closed')" if p.is_advisor else "c.status <> 'closed'")
    if search:
        where.append("(c.reference ilike %s or c.insurer_claim_number ilike %s or cl.full_name ilike %s)")
        like = f"%{search}%"
        params += [like, like, like]
    clause = " and ".join(where)
    total = fetch_one(conn, f"select count(*) as n from claims c join profiles cl on cl.id = c.client_id where {clause}", params)["n"]
    rows = fetch_all(conn, f"{_SELECT} where {clause} order by {order} nulls last, c.id limit %s offset %s", params + [paging.limit, paging.offset])
    return paging.envelope([summary(r, p.role) for r in rows], total)


def pipeline(conn: psycopg.Connection, p: Principal, client_id: Optional[UUID], include_closed: bool) -> Dict[str, Any]:
    ids = resolve_client_filter(conn, p, client_id)
    statuses = C.PIPELINE_STATUSES + (["closed"] if include_closed else [])
    counts = {r["status"]: r["n"] for r in fetch_all(
        conn, "select status, count(*) as n from claims where client_id = any(%s) and status = any(%s) group by status", (ids, statuses))}
    rows = fetch_all(
        conn,
        f"{_SELECT} where c.client_id = any(%s) and c.status = any(%s) order by c.submitted_at nulls last, c.id",
        (ids, statuses),
    )
    columns = []
    for s in statuses:
        claims = [summary(r, "advisor") for r in rows if r["status"] == s][:50]
        columns.append({"status": s, "label": status_label(s, "advisor"), "count": counts.get(s, 0), "claims": claims})
    return {"columns": columns}


# --------------------------------------------------------------------------------------- client: draft
def create_draft(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, body: ClaimCreate) -> Dict[str, Any]:
    insurer_id = body.insurer_id
    if body.policy_id:
        pol = fetch_one(conn, "select category, insurer_id from policies where id = %s and client_id = %s", (body.policy_id, p.id))
        if pol is None or pol["category"] != "motor":
            raise validation("policy_id", "invalid_value", "Choose one of your motor policies.")
        insurer_id = insurer_id or pol["insurer_id"]
    if insurer_id and fetch_one(conn, "select 1 as x from insurers where id = %s", (insurer_id,)) is None:
        raise validation("insurer_id", "invalid_value", "Unknown insurer.")
    row = fetch_one(conn, "insert into claims (client_id, policy_id, insurer_id) values (%s,%s,%s) returning id", (p.id, body.policy_id, insurer_id))
    add_event(conn, row["id"], "created", "Claim started", actor_id=p.id)
    return get_claim(conn, settings, storage, p, row["id"])


def _require_draft(row: Row) -> None:
    if row["status"] != "draft":
        raise bad_state("This claim has been sent to Royal Square and can no longer be edited.")


_NESTED = {
    "incident": {"occurred_at": "incident_occurred_at", "location_text": "incident_location_text", "location_lat": "incident_location_lat",
                 "location_lng": "incident_location_lng", "description": "incident_description"},
    "police": {"reported": "police_reported", "case_number": "police_case_number", "station": "police_station", "reported_at": "police_reported_at"},
    "driver": {"is_policyholder": "driver_is_policyholder", "full_name": "driver_full_name", "relationship_to_policyholder": "driver_relationship"},
}


def patch_draft(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, claim_id: UUID, body: ClaimPatch) -> Dict[str, Any]:
    row = load_claim(conn, p, claim_id, lock=True)
    _require_draft(row)
    data = body.model_dump(exclude_unset=True)
    cols: Dict[str, Any] = {}
    for group, mapping in _NESTED.items():
        for key, value in (data.get(group) or {}).items():
            cols[mapping[key]] = value
    if "insurer_id" in data:
        if data["insurer_id"] is not None and fetch_one(conn, "select 1 as x from insurers where id = %s", (data["insurer_id"],)) is None:
            raise validation("insurer_id", "invalid_value", "Unknown insurer.")
        cols["insurer_id"] = data["insurer_id"]
    if "vehicle_use" in data:
        cols["vehicle_use"] = data["vehicle_use"]
    for arr in ("witnesses", "third_parties"):
        if arr in data:
            cols[arr] = data[arr] or []
    update_row(conn, "claims", claim_id, cols, jsonb=("witnesses", "third_parties"))
    return get_claim(conn, settings, storage, p, claim_id)


def upload_attachment(
    conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, claim_id: UUID, *, kind: str,
    label: Optional[str], filename: str, declared_type: Optional[str], data: bytes,
) -> Dict[str, Any]:
    row = load_claim(conn, p, claim_id, lock=True)
    if row["status"] == "closed":
        raise bad_state("This claim is closed.")
    obj = att.store(conn, settings, storage, p, claim_id=claim_id, kind=kind, label=label, filename=filename,
                    declared_type=declared_type, data=data, max_count=settings.max_attachments_per_claim)
    if row["status"] != "draft":
        add_event(conn, claim_id, "attachment_added", "Document added", message=label or obj["filename"], actor_id=p.id)
    return obj


def delete_attachment(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, claim_id: UUID, attachment_id: UUID) -> None:
    row = load_claim(conn, p, claim_id, lock=True)
    _require_draft(row)
    a = fetch_one(conn, "select id, storage_path from attachments where id = %s and claim_id = %s", (attachment_id, claim_id))
    if a is None:
        raise not_found("Attachment")
    execute(conn, "delete from attachments where id = %s", (attachment_id,))
    storage.delete(settings.attachments_bucket, [a["storage_path"]])


def submit(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, claim_id: UUID) -> Dict[str, Any]:
    row = load_claim(conn, p, claim_id, lock=True)
    if row["status"] != "draft":
        raise bad_state("This claim has already been sent.")
    missing = missing_fields(row, att.kinds_for_claim(conn, claim_id))
    if missing:
        raise validation_many([field_error(m, "required", _MISSING_MESSAGES[m]) for m in missing])
    n = fetch_one(conn, "select nextval('claim_reference_seq') as n")["n"]
    reference = f"CLM-{clock.today().year}-{n:04d}"
    execute(
        conn,
        "update claims set status = 'submitted', reference = %s, submitted_at = now(), status_changed_at = now(), updated_at = now() where id = %s",
        (reference, claim_id),
    )
    add_event(conn, claim_id, "submitted", "Claim sent to Royal Square", from_status="draft", to_status="submitted", actor_id=p.id)
    return get_claim(conn, settings, storage, p, claim_id)


def choose_repair_date(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, claim_id: UUID, body: RepairDateBody) -> Dict[str, Any]:
    row = load_claim(conn, p, claim_id, lock=True)
    if row["status"] != "authorised":
        raise bad_state("You can choose a repair date once the repairs have been approved.")
    update_row(conn, "claims", claim_id, {"repair_drop_off_date": body.drop_off_date})
    add_event(conn, claim_id, "repair_date_chosen", "Repair date chosen", message=f"Vehicle goes in on {body.drop_off_date.day} {body.drop_off_date.strftime('%b %Y')}.", actor_id=p.id)
    return get_claim(conn, settings, storage, p, claim_id)


def review(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, claim_id: UUID, body: ReviewBody) -> Dict[str, Any]:
    row = load_claim(conn, p, claim_id, lock=True)
    if row["status"] != "completed":
        raise bad_state("You can review a claim once the repairs are finished.")
    execute(
        conn,
        "update claims set review_rating = %s, review_comment = %s, review_submitted_at = now(), status = 'closed', "
        "status_changed_at = now(), closed_at = now(), updated_at = now() where id = %s",
        (body.rating, body.comment, claim_id),
    )
    add_event(conn, claim_id, "review_submitted", "Review received. Claim closed", message=f"Rating: {body.rating}/5", from_status="completed", to_status="closed", actor_id=p.id)
    return get_claim(conn, settings, storage, p, claim_id)


# ------------------------------------------------------------------------------------- adviser actions
def patch_insurer_details(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, claim_id: UUID, body: InsurerDetailsPatch) -> Dict[str, Any]:
    row = load_claim(conn, p, claim_id, lock=True)
    mapping = {"claim_number": "insurer_claim_number", "handler_name": "insurer_handler_name",
               "handler_email": "insurer_handler_email", "handler_phone": "insurer_handler_phone"}
    cols = {mapping[k]: v for k, v in body.model_dump(exclude_unset=True).items()}
    changed = {c: v for c, v in cols.items() if row[c] != v}
    if changed:
        update_row(conn, "claims", claim_id, changed)
        msg = f"Claim number {cols['insurer_claim_number']}" if cols.get("insurer_claim_number") else None
        add_event(conn, claim_id, "insurer_details_updated", "Insurer details updated", message=msg, actor_id=p.id)
    return get_claim(conn, settings, storage, p, claim_id)


def transition(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, claim_id: UUID, body: TransitionBody) -> Dict[str, Any]:
    row = load_claim(conn, p, claim_id, lock=True)
    options = {t["to_status"]: t for t in allowed_transitions(row, "advisor", [])}
    opt = options.get(body.to_status)
    if opt is None:
        raise bad_state(f"A claim that is '{row['status']}' cannot move to '{body.to_status}'.")
    if opt["requires"]:
        raise validation_many([field_error(r, "required", "Record the insurer's claim number first.") for r in opt["requires"]])
    to = body.to_status
    closing = ", closed_at = now()" if to == "closed" else ""
    execute(conn, f"update claims set status = %s, status_changed_at = now(), updated_at = now(){closing} where id = %s", (to, claim_id))
    label = C.STATUS_BY_VALUE[to]["client_label"]
    title = label if opt["direction"] == "forward" else f"Status corrected: {label}"
    message = body.note or (f"Claim number {row['insurer_claim_number']}" if to == "registered" else None)
    add_event(conn, claim_id, "status_changed", title, message=message, visible=body.visible_to_client,
              from_status=row["status"], to_status=to, actor_id=p.id)
    return get_claim(conn, settings, storage, p, claim_id)


def patch_repair_details(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, claim_id: UUID, body: RepairDetailsPatch) -> Dict[str, Any]:
    load_claim(conn, p, claim_id, lock=True)
    mapping = {"repairer_name": "repair_repairer_name", "repairer_phone": "repair_repairer_phone", "quote_amount_cents": "repair_quote_amount_cents",
               "authorised_amount_cents": "repair_authorised_amount_cents", "estimated_completion_date": "repair_estimated_completion_date",
               "completed_at": "repair_completed_at"}
    update_row(conn, "claims", claim_id, {mapping[k]: v for k, v in body.model_dump(exclude_unset=True).items()})
    return get_claim(conn, settings, storage, p, claim_id)


def patch_hire_car(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, claim_id: UUID, body: HireCarPatch) -> Dict[str, Any]:
    row = load_claim(conn, p, claim_id, lock=True)
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is None:
        raise validation("status", "invalid_value", "status cannot be cleared.")
    mapping = {"status": "hire_car_status", "provider": "hire_car_provider", "delivery_date": "hire_car_delivery_date", "return_date": "hire_car_return_date"}
    cols = {mapping[k]: v for k, v in data.items()}
    if any(row[c] != v for c, v in cols.items()):
        update_row(conn, "claims", claim_id, cols)
        new_status = data.get("status", row["hire_car_status"])
        title = C.HIRE_CAR_LABELS[new_status] if data.get("status") and data["status"] != row["hire_car_status"] else "Hire car details updated"
        add_event(conn, claim_id, "hire_car_updated", title, actor_id=p.id)
    return get_claim(conn, settings, storage, p, claim_id)


def post_update(conn: psycopg.Connection, p: Principal, claim_id: UUID, body: UpdateBody) -> Dict[str, Any]:
    load_claim(conn, p, claim_id, lock=True)
    visible = body.visible_to_client if body.visible_to_client is not None else body.type == "repair_update"
    title = "Repair update" if body.type == "repair_update" else "Note added"
    ev = add_event(conn, claim_id, body.type, title, message=body.message, visible=visible, actor_id=p.id)
    execute(conn, "update claims set updated_at = now() where id = %s", (claim_id,))
    r = fetch_one(conn, "select e.*, a.full_name as actor_name, a.role as actor_role from claim_events e left join profiles a on a.id = e.actor_id where e.id = %s", (ev["id"],))
    return event_object(r)
