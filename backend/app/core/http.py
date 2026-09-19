"""Response rendering, pagination and sorting helpers shared by every route."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import Query
from fastapi.responses import JSONResponse


def _default(o: Any) -> Any:
    if isinstance(o, datetime):
        if o.tzinfo is None:
            o = o.replace(tzinfo=timezone.utc)
        return o.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(o, date):
        return o.isoformat()
    if isinstance(o, UUID):
        return str(o)
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


class ApiJSONResponse(JSONResponse):
    """JSON with UTC timestamps ending in Z, as the contract requires (api.md section 1.2)."""

    def render(self, content: Any) -> bytes:
        return json.dumps(content, default=_default, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def ok(data: Any, status_code: int = 200, headers: Optional[Dict[str, str]] = None) -> ApiJSONResponse:
    return ApiJSONResponse(data, status_code=status_code, headers=headers)


def created(data: Any, location: str) -> ApiJSONResponse:
    return ApiJSONResponse(data, status_code=201, headers={"Location": location})


def no_content():
    from fastapi import Response

    return Response(status_code=204)


class Paging:
    """`limit` and `offset` query parameters (api.md section 1.3)."""

    def __init__(self, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0)):
        self.limit = limit
        self.offset = offset

    def envelope(self, items: list, total: int) -> Dict[str, Any]:
        return {"items": items, "total": total, "limit": self.limit, "offset": self.offset}


def order_by(sort: Optional[str], allowed: Dict[str, str], default: str) -> str:
    """Build a safe ORDER BY clause. `allowed` maps public field names to SQL expressions."""
    from app.core.errors import validation

    value = sort or default
    desc = value.startswith("-")
    name = value[1:] if desc else value
    if name not in allowed:
        raise validation("sort", "invalid_value", f"Sort must be one of: {', '.join(sorted(allowed))} (prefix with - for descending).")
    return f"{allowed[name]} {'desc' if desc else 'asc'}"
