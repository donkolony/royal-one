"""Net worth and the adviser-maintained balance sheet (docs/api.md section 5.7).

net_worth = sum(assets) - sum(liabilities), where assets/liabilities are `financial_items`, plus the current
value of the client's ACTIVE investment and retirement policies (reported with source "policy").
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

import psycopg

from app.core import clock
from app.core.auth import Principal
from app.core.db import Row, execute, fetch_all, fetch_one
from app.core.errors import not_found, validation
from app.core.http import Paging
from app.domain import constants as C
from app.schemas.models import FinancialItemCreate, FinancialItemPatch
from app.services.common import require_client_in_scope, resolve_client_filter, update_row

_POLICY_TO_ITEM_CATEGORY = {"investment": "investments", "retirement": "retirement"}


def compute_net_worth(conn: psycopg.Connection, client_ids: List[UUID]) -> Dict[str, Any]:
    items = fetch_all(
        conn,
        "select kind, category, sum(amount_cents)::bigint as total from financial_items where client_id = any(%s) group by kind, category",
        (client_ids,),
    )
    pols = fetch_all(
        conn,
        "select category, sum(current_value_cents)::bigint as total from policies "
        "where client_id = any(%s) and status = 'active' and category in ('investment', 'retirement') "
        "and current_value_cents is not null group by category",
        (client_ids,),
    )
    breakdown: List[Dict[str, Any]] = [
        {"kind": r["kind"], "category": r["category"], "source": "balance_sheet", "total_cents": int(r["total"])} for r in items
    ]
    breakdown += [
        {"kind": "asset", "category": _POLICY_TO_ITEM_CATEGORY[r["category"]], "source": "policy", "total_cents": int(r["total"])}
        for r in pols
    ]
    assets = sum(b["total_cents"] for b in breakdown if b["kind"] == "asset")
    liabilities = sum(b["total_cents"] for b in breakdown if b["kind"] == "liability")
    breakdown.sort(key=lambda b: (b["kind"], -b["total_cents"]))
    return {
        "currency": "ZAR",
        "total_assets_cents": assets,
        "total_liabilities_cents": liabilities,
        "net_worth_cents": assets - liabilities,
        "as_of": clock.today(),
        "breakdown": breakdown,
    }


def net_worth(conn: psycopg.Connection, p: Principal, client_id: Optional[UUID]) -> Dict[str, Any]:
    return compute_net_worth(conn, resolve_client_filter(conn, p, client_id, required_for_advisor=True))


def _item(r: Row) -> Dict[str, Any]:
    return {k: r[k] for k in ("id", "client_id", "kind", "category", "label", "amount_cents", "as_of_date", "updated_at")}


def list_items(conn: psycopg.Connection, p: Principal, paging: Paging, client_id: Optional[UUID], kind: Optional[str]) -> Dict[str, Any]:
    ids = resolve_client_filter(conn, p, client_id, required_for_advisor=True)
    where, params = "client_id = any(%s)", [ids]
    if kind:
        where += " and kind = %s"
        params.append(kind)
    total = fetch_one(conn, f"select count(*) as n from financial_items where {where}", params)["n"]
    rows = fetch_all(conn, f"select * from financial_items where {where} order by kind, amount_cents desc, id limit %s offset %s", params + [paging.limit, paging.offset])
    return paging.envelope([_item(r) for r in rows], total)


def _check_category(kind: str, category: str) -> None:
    valid = C.ASSET_CATEGORIES if kind == "asset" else C.LIABILITY_CATEGORIES
    if category not in valid:
        raise validation("category", "invalid_value", f"For {kind}s the category must be one of: {', '.join(valid)}.")


def create_item(conn: psycopg.Connection, p: Principal, body: FinancialItemCreate) -> Dict[str, Any]:
    require_client_in_scope(conn, p, body.client_id)
    _check_category(body.kind, body.category)
    row = fetch_one(
        conn,
        "insert into financial_items (client_id, kind, category, label, amount_cents, as_of_date) values (%s,%s,%s,%s,%s,%s) returning *",
        (body.client_id, body.kind, body.category, body.label, body.amount_cents, body.as_of_date),
    )
    return _item(row)


def _load_item(conn: psycopg.Connection, p: Principal, item_id: UUID) -> Row:
    row = fetch_one(conn, "select * from financial_items where id = %s and client_id = any(%s)", (item_id, p.client_ids(conn)))
    if row is None:
        raise not_found("Financial item")
    return row


def patch_item(conn: psycopg.Connection, p: Principal, item_id: UUID, body: FinancialItemPatch) -> Dict[str, Any]:
    row = _load_item(conn, p, item_id)
    fields = body.model_dump(exclude_unset=True)
    for k in ("category", "label", "amount_cents", "as_of_date"):
        if k in fields and fields[k] is None:
            raise validation(k, "invalid_value", f"{k} cannot be cleared.")
    if "category" in fields:
        _check_category(row["kind"], fields["category"])
    update_row(conn, "financial_items", item_id, fields)
    return _item(fetch_one(conn, "select * from financial_items where id = %s", (item_id,)))


def delete_item(conn: psycopg.Connection, p: Principal, item_id: UUID) -> None:
    _load_item(conn, p, item_id)
    execute(conn, "delete from financial_items where id = %s", (item_id,))
