"""One error envelope for everything (docs/api.md section 1.4)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.http import ApiJSONResponse

log = logging.getLogger("app.errors")


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: Optional[List[Dict[str, str]]] = None,
        retry_after_seconds: Optional[int] = None,
    ):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        self.retry_after_seconds = retry_after_seconds


# Shorthand constructors -----------------------------------------------------------------------------
def not_found(what: str = "Resource") -> ApiError:
    return ApiError(404, "not_found", f"{what} not found.")


def forbidden(message: str = "You do not have permission to do this.") -> ApiError:
    return ApiError(403, "forbidden", message)


def bad_state(message: str) -> ApiError:
    return ApiError(409, "invalid_state_transition", message)


def conflict(message: str) -> ApiError:
    return ApiError(409, "conflict", message)


def validation(field: str, code: str, message: str) -> ApiError:
    return ApiError(422, "validation_error", "One or more fields are invalid.", [field_error(field, code, message)])


def validation_many(details: List[Dict[str, str]]) -> ApiError:
    return ApiError(422, "validation_error", "One or more fields are invalid.", details)


def field_error(field: str, code: str, message: str) -> Dict[str, str]:
    return {"field": field, "code": code, "message": message}


# Rendering ------------------------------------------------------------------------------------------
def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _envelope(request: Request, err: ApiError) -> ApiJSONResponse:
    body: Dict[str, Any] = {
        "error": {
            "code": err.code,
            "message": err.message,
            "request_id": _request_id(request),
        }
    }
    if err.details is not None:
        body["error"]["details"] = err.details
    if err.retry_after_seconds is not None:
        body["error"]["retry_after_seconds"] = err.retry_after_seconds
    headers = {"X-Request-ID": _request_id(request)}
    if err.retry_after_seconds is not None:
        headers["Retry-After"] = str(err.retry_after_seconds)
    return ApiJSONResponse(body, status_code=err.status, headers=headers)


_PYDANTIC_CODES = {
    "missing": "required",
    "extra_forbidden": "extra_forbidden",
    "string_too_short": "too_short",
    "string_too_long": "too_long",
    "too_short": "too_short",
    "too_long": "too_long",
    "greater_than": "too_small",
    "greater_than_equal": "too_small",
    "less_than": "too_large",
    "less_than_equal": "too_large",
    "string_pattern_mismatch": "invalid_format",
    "enum": "invalid_value",
    "literal_error": "invalid_value",
    "uuid_parsing": "invalid_uuid",
    "uuid_type": "invalid_uuid",
    "date_from_datetime_parsing": "invalid_date",
    "date_parsing": "invalid_date",
    "date_type": "invalid_date",
    "datetime_parsing": "invalid_datetime",
    "datetime_type": "invalid_datetime",
    "int_type": "invalid_type",
    "int_parsing": "invalid_type",
    "bool_type": "invalid_type",
    "string_type": "invalid_type",
    "value_error": "invalid_value",
}


def _field_path(loc: tuple) -> str:
    parts = [p for p in loc if p not in ("body", "query", "path", "header", "form")]
    out = ""
    for p in parts:
        if isinstance(p, int):
            out += f"[{p}]"
        else:
            out += ("." if out else "") + str(p)
    return out or "body"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return _envelope(request, exc)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        if any(e.get("type") == "json_invalid" for e in errors):
            return _envelope(request, ApiError(400, "bad_request", "The request body is not valid JSON."))
        details = []
        for e in errors:
            msg = e.get("msg", "Invalid value.")
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, "):]
            details.append(field_error(_field_path(tuple(e.get("loc", ()))), _PYDANTIC_CODES.get(e.get("type", ""), "invalid"), msg))
        return _envelope(request, ApiError(422, "validation_error", "One or more fields are invalid.", details))

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        mapping = {404: "not_found", 405: "bad_request", 413: "payload_too_large", 415: "unsupported_media_type"}
        code = mapping.get(exc.status_code, "bad_request" if exc.status_code < 500 else "internal_error")
        msg = "Route not found." if exc.status_code == 404 else str(exc.detail)
        return _envelope(request, ApiError(exc.status_code, code, msg))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        # Never echo internals to the client; the request id links the response to the log line.
        log.exception("unhandled error request_id=%s", _request_id(request))
        return _envelope(request, ApiError(500, "internal_error", "Something went wrong. Please try again."))
