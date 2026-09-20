"""Small helpers shared by services."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

import psycopg

from app.core.auth import Principal
from app.core.db import Row, execute, fetch_one
from app.core.errors import not_found, validation
from app.services import audit


def person_ref(row: Row, prefix: str = "") -> Dict[str, Any]:
    return {
        "id": row[f"{prefix}id"],
        "full_name": row[f"{prefix}full_name"],
        "email": row[f"{prefix}email"],
        "phone": row[f"{prefix}phone"],
    }


def client_ref(row: Row, id_key: str = "client_id", name_key: str = "client_name") -> Dict[str, Any]:
    return {"id": row[id_key], "full_name": row[name_key]}


def progress_percent(current: int, target: int) -> float:
    if target <= 0:
        return 0.0
    return min(100.0, round(current * 100.0 / target, 1))


# Which client owns each kind of record, so a refused attempt can be logged against the data subject.
_OWNERS = {
    "client": "select id as cid from clients where id = %s",
    "claim": "select client_id as cid from claims where id = %s",
    "request": "select client_id as cid from requests where id = %s",
    "policy": "select client_id as cid from policies where id = %s",
    "goal": "select client_id as cid from goal_participants where goal_id = %s limit 1",
    "reminder": "select client_id as cid from reminders where id = %s",
}


def not_found_logged(conn: psycopg.Connection, principal: Principal, entity_type: str, entity_id: UUID, label: str):
    """A 404 for something outside the caller's scope. The answer is identical whether or not the record exists (so ids
    cannot be probed), but when it DOES exist the refused attempt is written to the audit trail."""
    row = fetch_one(conn, _OWNERS[entity_type], (entity_id,))
    if row is not None:
        audit.record_denied(principal, entity_type, entity_id, client_id=row["cid"])
    return not_found(label)


def require_client_in_scope(conn: psycopg.Connection, principal: Principal, client_id: UUID) -> UUID:
    """404 (not 403) for a client outside the caller's scope, so ids cannot be probed."""
    if client_id not in principal.client_ids(conn):
        raise not_found_logged(conn, principal, "client", client_id, "Client")
    return client_id


def resolve_client_filter(conn: psycopg.Connection, principal: Principal, client_id: Optional[UUID], required_for_advisor: bool = False) -> List[UUID]:
    """Turn the optional `client_id` query parameter into the list of client ids a query may touch."""
    ids = principal.client_ids(conn)
    if client_id is None:
        if required_for_advisor and principal.is_advisor:
            raise validation("client_id", "required", "client_id is required.")
        return ids
    if client_id not in ids:
        raise not_found_logged(conn, principal, "client", client_id, "Client")
    return [client_id]


def update_row(conn: psycopg.Connection, table: str, row_id: UUID, fields: Dict[str, Any], jsonb: Iterable[str] = ()) -> None:
    """UPDATE the given columns (names come from code, values are always parameters) and bump updated_at."""
    if not fields:
        return
    from psycopg.types.json import Jsonb

    sets, params = [], []
    for col, val in fields.items():
        sets.append(f"{col} = %s")
        params.append(Jsonb(val) if col in set(jsonb) else val)
    params.append(row_id)
    execute(conn, f"update {table} set {', '.join(sets)}, updated_at = now() where id = %s", params)


def insurer_ref(row: Row, id_key: str = "insurer_id", name_key: str = "insurer_name") -> Optional[Dict[str, Any]]:
    if row.get(id_key) is None:
        return None
    return {"id": row[id_key], "name": row[name_key]}


def exists(conn: psycopg.Connection, table: str, row_id: UUID) -> bool:
    return fetch_one(conn, f"select 1 as x from {table} where id = %s", (row_id,)) is not None
