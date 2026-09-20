"""Insurers, policies and the static `/meta` reference document."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

import psycopg

from app.core.auth import Principal
from app.core.config import Settings
from app.core.db import Row, fetch_all, fetch_one
from app.core.errors import not_found, validation
from app.core.http import Paging, order_by
from app.domain import constants as C
from app.schemas.models import PolicyCreate, PolicyPatch
from app.services import audit
from app.services.common import not_found_logged, require_client_in_scope, resolve_client_filter, update_row


def list_insurers(conn: psycopg.Connection) -> Dict[str, Any]:
    rows = fetch_all(conn, "select id, name from insurers order by (name = 'Other'), name")
    return {"items": rows}


def build_meta(settings: Settings) -> Dict[str, Any]:
    return {
        "api_version": "v1",
        "currency": "ZAR",
        "demo_mode": settings.demo_mode,
        "retention_years": settings.retention_years,
        "claim_statuses": C.CLAIM_STATUSES,
        "hire_car_statuses": C.HIRE_CAR_STATUSES,
        "reminder_types": C.REMINDER_TYPES,
        "request_types": [
            {"type": t["type"], "label": t["label"], "requires_verification": t["requires_verification"]} for t in C.REQUEST_TYPES
        ],
        "policy_categories": C.POLICY_CATEGORIES,
        "policy_statuses": C.POLICY_STATUSES,
        "financial_item_categories": {"asset": C.ASSET_CATEGORIES, "liability": C.LIABILITY_CATEGORIES},
        "goal_categories": C.GOAL_CATEGORIES,
        "document_categories": C.DOCUMENT_CATEGORIES,
        "attachment_rules": {
            "max_bytes": settings.max_upload_bytes,
            "max_per_claim": settings.max_attachments_per_claim,
            "max_per_request": settings.max_attachments_per_request,
            "content_types": {"image": C.IMAGE_TYPES, "document": C.DOCUMENT_TYPES, "audio": C.AUDIO_TYPES},
            "kinds": [{"kind": k, "accepts": fams} for k, fams in C.ATTACHMENT_KINDS.items()],
        },
    }


_POLICY_SELECT = """
select p.*, i.name as insurer_name from policies p join insurers i on i.id = p.insurer_id
"""


def _policy(r: Row) -> Dict[str, Any]:
    return {
        "id": r["id"], "client_id": r["client_id"], "insurer": {"id": r["insurer_id"], "name": r["insurer_name"]},
        "category": r["category"], "product_name": r["product_name"], "policy_number": r["policy_number"],
        "status": r["status"], "asset_description": r["asset_description"],
        "cover_amount_cents": r["cover_amount_cents"], "current_value_cents": r["current_value_cents"],
        "premium_cents": r["premium_cents"], "premium_frequency": r["premium_frequency"],
        "start_date": r["start_date"], "renewal_date": r["renewal_date"],
        "valuation_certificate_date": r["valuation_certificate_date"],
    }


def list_policies_for(conn: psycopg.Connection, client_ids: List[UUID], statuses: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    sql, params = f"{_POLICY_SELECT} where p.client_id = any(%s)", [client_ids]
    if statuses:
        sql += " and p.status = any(%s)"
        params.append(statuses)
    return [_policy(r) for r in fetch_all(conn, sql + " order by p.renewal_date nulls last, p.product_name", params)]


def list_policies(
    conn: psycopg.Connection, p: Principal, paging: Paging, client_id: Optional[UUID], category: Optional[str],
    status: Optional[str], sort: Optional[str],
) -> Dict[str, Any]:
    ids = resolve_client_filter(conn, p, client_id)
    order = order_by(sort, {"renewal_date": "p.renewal_date", "product_name": "p.product_name"}, "renewal_date")
    where, params = "p.client_id = any(%s)", [ids]
    if category:
        where += " and p.category = %s"
        params.append(category)
    if status:
        where += " and p.status = %s"
        params.append(status)
    total = fetch_one(conn, f"select count(*) as n from policies p where {where}", params)["n"]
    rows = fetch_all(conn, f"{_POLICY_SELECT} where {where} order by {order} nulls last, p.id limit %s offset %s", params + [paging.limit, paging.offset])
    return paging.envelope([_policy(r) for r in rows], total)


def get_policy(conn: psycopg.Connection, p: Principal, policy_id: UUID) -> Dict[str, Any]:
    row = fetch_one(conn, f"{_POLICY_SELECT} where p.id = %s and p.client_id = any(%s)", (policy_id, p.client_ids(conn)))
    if row is None:
        raise not_found_logged(conn, p, "policy", policy_id, "Policy")
    return _policy(row)


def _check_insurer(conn: psycopg.Connection, insurer_id: UUID) -> None:
    if fetch_one(conn, "select 1 as x from insurers where id = %s", (insurer_id,)) is None:
        raise validation("insurer_id", "invalid_value", "Unknown insurer.")


def create_policy(conn: psycopg.Connection, p: Principal, body: PolicyCreate) -> Dict[str, Any]:
    require_client_in_scope(conn, p, body.client_id)
    _check_insurer(conn, body.insurer_id)
    cols = body.model_dump()
    names = ", ".join(cols)
    row = fetch_one(conn, f"insert into policies ({names}) values ({', '.join(['%s'] * len(cols))}) returning id", list(cols.values()))
    audit.record(conn, p, "policy.created", "policy", row["id"], client_id=body.client_id,
                 summary=f"Added a {body.category} policy ({body.product_name})", details={"category": body.category})
    return get_policy(conn, p, row["id"])


def patch_policy(conn: psycopg.Connection, p: Principal, policy_id: UUID, body: PolicyPatch) -> Dict[str, Any]:
    get_policy(conn, p, policy_id)  # 404 when out of scope
    fields = body.model_dump(exclude_unset=True)
    for required in ("category", "product_name", "policy_number", "status", "insurer_id"):
        if required in fields and fields[required] is None:
            raise validation(required, "invalid_value", f"{required} cannot be cleared.")
    if "insurer_id" in fields:
        _check_insurer(conn, fields["insurer_id"])
    update_row(conn, "policies", policy_id, fields)
    out = get_policy(conn, p, policy_id)
    audit.record(conn, p, "policy.updated", "policy", policy_id, client_id=out["client_id"],
                 summary=f"Updated the policy '{out['product_name']}'", details={"fields": sorted(fields)})
    return out
