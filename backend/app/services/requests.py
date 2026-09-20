"""Client requests (docs/api.md section 5.11). Payloads are validated against the same field definitions that
GET /requests/types serves, so the forms the frontend builds and the checks the server runs cannot drift."""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from app.core import clock
from app.core.auth import Principal
from app.core.config import Settings
from app.core.db import Row, execute, fetch_all, fetch_one
from app.core.errors import bad_state, field_error, not_found, validation, validation_many
from app.core.http import Paging, order_by
from app.domain import constants as C
from app.schemas.models import RequestCreate, RequestPatch
from app.domain import workflows as W
from app.services import attachments as att, audit, workflow
from app.services.common import not_found_logged, resolve_client_filter
from app.storage.base import Storage

TERMINAL = ("completed", "declined")


# ------------------------------------------------------------------------------------ payload validation
class _Ctx:
    def __init__(self, conn: psycopg.Connection, client_id: UUID):
        self.conn, self.client_id, self.errors = conn, client_id, []

    def err(self, path: str, code: str, msg: str) -> None:
        self.errors.append(field_error(path, code, msg))


def _parse_date(v: Any) -> Optional[date]:
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v)
        except ValueError:
            return None
    return None


def _check_value(ctx: _Ctx, path: str, spec: Dict[str, Any], v: Any, payload: Dict[str, Any]) -> Any:
    t = spec["type"]
    if t in ("string", "text"):
        if not isinstance(v, str) or not v.strip():
            ctx.err(path, "required" if v in (None, "") else "invalid_type", "Enter a value.")
            return None
        v = v.strip()
        if len(v) > spec.get("max_length", 2000):
            ctx.err(path, "too_long", f"Use at most {spec.get('max_length', 2000)} characters.")
        if spec.get("pattern") and not re.match(spec["pattern"], v):
            ctx.err(path, "invalid_format", "This is not in the expected format.")
        return v
    if t == "date":
        d = _parse_date(v)
        if d is None:
            ctx.err(path, "invalid_date", "Enter a date as YYYY-MM-DD.")
            return None
        if spec.get("not_before"):
            other = _parse_date(payload.get(spec["not_before"]))
            if other and d < other:
                ctx.err(path, "too_small", f"This cannot be before {spec['not_before']}.")
        return d.isoformat()
    if t == "integer":
        if isinstance(v, bool) or not isinstance(v, int):
            ctx.err(path, "invalid_type", "Enter a whole number.")
            return None
        if "min" in spec and v < spec["min"]:
            ctx.err(path, "too_small", f"Must be at least {spec['min']}.")
        if "max" in spec and v > spec["max"]:
            ctx.err(path, "too_large", f"Must be at most {spec['max']}.")
        return v
    if t == "boolean":
        if not isinstance(v, bool):
            ctx.err(path, "invalid_type", "Must be true or false.")
        return v
    if t == "enum":
        if v not in spec["options"]:
            ctx.err(path, "invalid_value", f"Choose one of: {', '.join(spec['options'])}.")
        return v
    if t == "uuid":
        try:
            u = UUID(str(v))
        except ValueError:
            ctx.err(path, "invalid_uuid", "Not a valid id.")
            return None
        if spec.get("ref"):
            row = fetch_one(ctx.conn, "select category from policies where id = %s and client_id = %s", (u, ctx.client_id))
            if row is None or (spec["ref"] == "motor_policy" and row["category"] != "motor"):
                ctx.err(path, "invalid_value", "Choose one of your policies." if spec["ref"] == "policy" else "Choose one of your motor policies.")
        return str(u)
    if t in ("string_list", "date_list", "object_list"):
        if not isinstance(v, list):
            ctx.err(path, "invalid_type", "Must be a list.")
            return None
        if len(v) < spec.get("min_items", 0):
            ctx.err(path, "too_short", f"Add at least {spec['min_items']}.")
        if len(v) > spec.get("max_items", 100):
            ctx.err(path, "too_long", f"Add at most {spec['max_items']}.")
        out: List[Any] = []
        for i, item in enumerate(v):
            ipath = f"{path}[{i}]"
            if t == "string_list":
                out.append(_check_value(ctx, ipath, {"type": "string", "max_length": spec.get("max_length", 200)}, item, payload))
            elif t == "date_list":
                d = _check_value(ctx, ipath, {"type": "date"}, item, payload)
                if d and spec.get("not_in_past") and date.fromisoformat(d) < clock.today():
                    ctx.err(ipath, "too_small", "Choose a date that is today or later.")
                out.append(d)
            else:
                out.append(_check_object(ctx, ipath, spec["item_fields"], item))
        return out
    ctx.err(path, "invalid", "Unsupported field.")
    return None


def _check_object(ctx: _Ctx, path: str, fields: List[Dict[str, Any]], obj: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(obj, dict):
        ctx.err(path, "invalid_type", "Must be an object.")
        return None
    known = {f["name"] for f in fields}
    for k in obj:
        if k not in known:
            ctx.err(f"{path}.{k}", "extra_forbidden", "Unknown field.")
    out: Dict[str, Any] = {}
    for f in fields:
        v = obj.get(f["name"])
        fpath = f"{path}.{f['name']}"
        if v is None:
            if f.get("required"):
                ctx.err(fpath, "required", "This field is required.")
            out[f["name"]] = None
            continue
        out[f["name"]] = _check_value(ctx, fpath, f, v, obj)
    return out


def validate_payload(conn: psycopg.Connection, client_id: UUID, type_def: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    ctx = _Ctx(conn, client_id)
    cleaned = _check_object(ctx, "payload", type_def["fields"], payload) or {}
    if ctx.errors:
        raise validation_many(ctx.errors)
    return cleaned


# --------------------------------------------------------------------------------------- serialisation
def mask_account(number: str) -> str:
    return "*" * max(0, len(number) - 4) + number[-4:]


def _payload_for(row: Row, role: str) -> Dict[str, Any]:
    payload = dict(row["payload"])
    if row["type"] == "bank_details_change" and role == "client" and isinstance(payload.get("account_number"), str):
        payload["account_number"] = mask_account(payload["account_number"])
    return payload


_SELECT = "select r.*, p.full_name as client_name from requests r join profiles p on p.id = r.client_id"


def request_object(row: Row, role: str) -> Dict[str, Any]:
    d = C.REQUEST_TYPE_BY_NAME[row["type"]]
    return {
        "id": row["id"], "type": row["type"], "type_label": d["label"], "status": row["status"],
        "client": {"id": row["client_id"], "full_name": row["client_name"]},
        "payload": _payload_for(row, role), "client_note": row["client_note"], "adviser_response": row["adviser_response"],
        "requires_verification": d["requires_verification"], "insurer_forward": d["insurer_forward"],
        "submitted_at": row["submitted_at"], "updated_at": row["updated_at"], "completed_at": row["completed_at"],
    }


def _load(conn: psycopg.Connection, p: Principal, request_id: UUID, lock: bool = False) -> Row:
    sql = f"{_SELECT} where r.id = %s and r.client_id = any(%s)" + (" for update of r" if lock else "")
    row = fetch_one(conn, sql, (request_id, p.client_ids(conn)))
    if row is None:
        raise not_found_logged(conn, p, "request", request_id, "Request")
    return row


def _detail(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, row: Row) -> Dict[str, Any]:
    out = request_object(row, p.role)
    out["attachments"] = att.list_for(conn, settings, storage, request_id=row["id"])
    out["timeline"] = workflow.request_timeline(conn, row["id"], client_view=p.is_client)
    return out


# --------------------------------------------------------------------------------------------- operations
def list_types() -> Dict[str, Any]:
    return {"items": C.REQUEST_TYPES}


def create(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, body: RequestCreate) -> Dict[str, Any]:
    type_def = C.REQUEST_TYPE_BY_NAME[body.type]
    cleaned = validate_payload(conn, p.id, type_def, body.payload)
    row = fetch_one(
        conn,
        "insert into requests (client_id, type, payload, client_note) values (%s,%s,%s,%s) returning id",
        (p.id, body.type, Jsonb(cleaned), body.client_note),
    )
    audit.record(conn, p, "request.created", "request", row["id"], client_id=p.id, summary=f"Submitted a request: {type_def['label']}",
                 details={"type": body.type})
    workflow.add_request_event(conn, row["id"], "created", "Request received", to_status="submitted", actor_id=p.id)
    if type_def["insurer_forward"]:
        workflow.add_request_event(conn, row["id"], "forwarded", "Passed to your product provider (simulated)",
                                   message="Demo: no real provider is contacted in this prototype.", to_status="submitted")
    workflow.tell(conn, W.REQUEST_NOTIFY_ON_CREATE, p.id, {"label": type_def["label"], "client": p.full_name}, kind="new_request",
                  link={"resource": "request", "id": row["id"]})
    return _detail(conn, settings, storage, p, _load(conn, p, row["id"]))


def list_requests(
    conn: psycopg.Connection, p: Principal, paging: Paging, *, client_id: Optional[UUID], type_: Optional[str],
    statuses: List[str], open_: Optional[bool], sort: Optional[str],
) -> Dict[str, Any]:
    ids = resolve_client_filter(conn, p, client_id)
    order = order_by(sort, {"submitted_at": "r.submitted_at"}, "-submitted_at")
    where, params = ["r.client_id = any(%s)"], [ids]
    if type_:
        if type_ not in C.REQUEST_TYPE_BY_NAME:
            raise validation("type", "invalid_value", "Unknown request type.")
        where.append("r.type = %s")
        params.append(type_)
    if statuses:
        where.append("r.status = any(%s)")
        params.append(statuses)
    if open_:
        where.append("r.status in ('submitted', 'in_progress')")
    clause = " and ".join(where)
    total = fetch_one(conn, f"select count(*) as n from requests r where {clause}", params)["n"]
    rows = fetch_all(conn, f"{_SELECT} where {clause} order by {order}, r.id limit %s offset %s", params + [paging.limit, paging.offset])
    return paging.envelope([request_object(r, p.role) for r in rows], total)


def get_request(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, request_id: UUID) -> Dict[str, Any]:
    return _detail(conn, settings, storage, p, _load(conn, p, request_id))


def patch_request(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, request_id: UUID, body: RequestPatch) -> Dict[str, Any]:
    row = _load(conn, p, request_id, lock=True)
    data = body.model_dump(exclude_unset=True)
    if row["status"] in TERMINAL:
        raise bad_state(f"This request is already {row['status']} and cannot be changed.")
    new_status = data.get("status") or row["status"]
    if "status" in data and data["status"] is None:
        raise validation("status", "invalid_value", "status cannot be cleared.")
    if data.get("status") == row["status"]:
        raise bad_state(f"This request is already {row['status']}.")
    if new_status != row["status"] and not workflow.request_move_allowed(row["status"], new_status):
        raise bad_state(f"A request that is '{row['status']}' cannot move to '{new_status}'.")
    response = data["adviser_response"] if "adviser_response" in data else row["adviser_response"]
    if new_status == "declined" and not (response and response.strip()):
        raise validation("adviser_response", "required", "Explain why the request is declined.")
    completed_at = "now()" if new_status == "completed" else "completed_at"
    execute(
        conn,
        f"update requests set status = %s, adviser_response = %s, handled_by = %s, completed_at = {completed_at}, updated_at = now() where id = %s",
        (new_status, response, p.id, request_id),
    )
    audit.record(conn, p, "request.updated", "request", request_id, client_id=row["client_id"],
                 summary=f"Set a {C.REQUEST_TYPE_BY_NAME[row['type']]['label']} request to {new_status}",
                 details={"from": row["status"], "to": new_status, "responded": bool(response)})
    label = C.REQUEST_TYPE_BY_NAME[row["type"]]["label"]
    link = {"resource": "request", "id": request_id}
    if new_status != row["status"]:
        status_label = next(s["client_label"] for s in W.REQUEST_STATUSES if s["value"] == new_status)
        workflow.add_request_event(conn, request_id, "status_changed", status_label, message=response if "adviser_response" in data else None,
                                   from_status=row["status"], to_status=new_status, actor_id=p.id)
        workflow.tell(conn, workflow.request_transition_notices(row["status"], new_status), row["client_id"], {"label": label}, kind="request_update", link=link)
    elif "adviser_response" in data and response:
        workflow.add_request_event(conn, request_id, "note", "Message from your adviser", message=response, actor_id=p.id)
        workflow.tell_one(conn, "client", row["client_id"], kind="request_update", title="Your adviser replied", body=f"{label}.", link=link)
    return _detail(conn, settings, storage, p, _load(conn, p, request_id))


def upload_attachment(
    conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, request_id: UUID, *, kind: str,
    label: Optional[str], filename: str, declared_type: Optional[str], data: bytes,
) -> Dict[str, Any]:
    row = _load(conn, p, request_id, lock=True)
    if row["status"] not in ("submitted", "in_progress"):
        raise bad_state("This request is closed.")
    limit = min(settings.max_attachments_per_request, C.REQUEST_TYPE_BY_NAME[row["type"]]["max_attachments"])
    obj = att.store(conn, settings, storage, p, request_id=request_id, kind=kind, label=label, filename=filename,
                     declared_type=declared_type, data=data, max_count=limit)
    audit.record(conn, p, "document.uploaded", "attachment", obj["id"], client_id=row["client_id"],
                 summary=f"Uploaded a {kind} to a {C.REQUEST_TYPE_BY_NAME[row['type']]['label']} request",
                 details={"request_id": request_id, "kind": kind, "content_type": obj["content_type"], "size_bytes": obj["size_bytes"]})
    return obj


# ------------------------------------------------------------------------------------------ simulated provider
_PROVIDER_STEPS = {
    "submitted": ("in_progress", "Provider acknowledged (simulated)", "Demo provider: request received.", None),
    "in_progress": ("completed", "Provider responded (simulated)", "Demo provider: done. Your adviser will share the result with you.",
                    "Completed by the simulated provider. Your adviser will share the result with you."),
}


def provider_step(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, request_id: UUID) -> Dict[str, Any]:
    """DEMO ONLY (behind the DEMO_MODE flag): the simulated provider answers a request that is marked `insurer_forward`.
    Uses the same events, notifications and audit as a real status change, so the client's screen updates by itself."""
    row = _load(conn, p, request_id, lock=True)
    d = C.REQUEST_TYPE_BY_NAME[row["type"]]
    if not d["insurer_forward"]:
        raise bad_state("This request is handled by your adviser, not by a product provider.")
    step = _PROVIDER_STEPS.get(row["status"])
    if step is None:
        raise bad_state(f"The simulated provider has nothing left to do for a request that is {row['status']}.")
    to, title, message, response = step
    execute(conn, "update requests set status = %s, adviser_response = coalesce(%s, adviser_response), "
                  "completed_at = case when %s = 'completed' then now() else completed_at end, updated_at = now() where id = %s",
            (to, response, to, request_id))
    workflow.add_request_event(conn, request_id, "insurer_update", title, message=message, from_status=row["status"], to_status=to)
    audit.record(conn, None, "request.status_changed", "request", request_id, client_id=row["client_id"],
                 summary=f"Simulated provider moved a {d['label']} request to {to}", details={"from": row["status"], "to": to, "simulated": True})
    link = {"resource": "request", "id": request_id}
    workflow.tell_one(conn, "client", row["client_id"], kind="request_update", title=title, body=f"{d['label']}.", link=link)
    workflow.tell_one(conn, "advisor", row["client_id"], kind="request_update", title=title, body=f"{d['label']} for {row['client_name']}.", link=link)
    return _detail(conn, settings, storage, p, _load(conn, p, request_id))
