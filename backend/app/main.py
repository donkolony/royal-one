"""Application factory. Runtime collaborators (database pool, storage, LLM, token verifier) hang off `app.state`
so tests can substitute them."""
from __future__ import annotations

import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import ConnectionPool

from app.api.v1 import advisor_routes, audit_routes, claims_routes, core_routes
from app.core import clock
from app.core.auth import LocalHS256Verifier, SupabaseTokenVerifier, TokenVerifier
from app.core.config import Settings, get_settings, validate_settings
from app.core.db import make_pool
from app.core.errors import install_error_handlers
from app.core.http import ApiJSONResponse, ok
from app.core.logging import configure_logging
from app.core.rate_limit import RateLimiter
from app.llm.base import LLMRouter
from app.llm.providers import build_providers
from app.rag.retrieval import FtsRetriever, Retriever
from app.storage.base import MemoryStorage, Storage, SupabaseStorage

VERSION = "0.1.0"
_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{1,64}$")
access_log = logging.getLogger("app.access")
_PRIVATE_STATIC = {"/api/v1/insurers", "/api/v1/claims/checklist", "/api/v1/requests/types"}


def create_app(
    settings: Optional[Settings] = None,
    *,
    pool: Optional[ConnectionPool] = None,
    storage: Optional[Storage] = None,
    llm: Optional[LLMRouter] = None,
    verifier: Optional[TokenVerifier] = None,
    retriever: Optional[Retriever] = None,
) -> FastAPI:
    settings = validate_settings(settings or get_settings())
    configure_logging(settings.log_level)
    owns_pool = pool is None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pool = pool or make_pool(settings.database_url, settings.db_pool_min, settings.db_pool_max)
        yield
        if owns_pool:
            app.state.pool.close()

    app = FastAPI(
        title="Royal Square Platform API",
        version=VERSION,
        description="Contract: docs/api.md. All data is synthetic demo data.",
        default_response_class=ApiJSONResponse,
        lifespan=lifespan,
    )
    app.state.settings = settings
    if pool is not None:
        app.state.pool = pool  # available even when the lifespan is not run (tests)
    app.state.storage = storage or (
        MemoryStorage() if settings.storage_backend == "memory" else SupabaseStorage(settings.supabase_url, settings.supabase_service_role_key)
    )
    app.state.llm = llm or LLMRouter(build_providers(settings), settings.llm_timeout_seconds)
    app.state.retriever = retriever or FtsRetriever()
    app.state.verifier = verifier or (
        LocalHS256Verifier(settings.supabase_jwt_secret)
        if settings.auth_mode == "local_hs256"
        else SupabaseTokenVerifier(settings.supabase_url, settings.supabase_service_role_key)
    )
    app.state.llm_limiter = RateLimiter(settings.assistant_rate_limit_per_min)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After", "Location"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = request.headers.get("x-request-id", "")
        request.state.request_id = rid if _REQUEST_ID.match(rid) else str(uuid.uuid4())
        started = time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        # Cache policy (api.md 1.7): reference data may be cached for an hour; everything else never.
        path = request.url.path
        if path == "/api/v1/meta":
            policy = "public, max-age=3600"  # no login needed, identical for everyone
        elif path in _PRIVATE_STATIC and response.status_code == 200:
            policy = "private, max-age=3600"  # needs a login, so only the user's own cache may keep it
        else:
            policy = "no-store"
        response.headers.setdefault("Cache-Control", policy)
        access_log.info("request", extra={"fields": {
            "request_id": request.state.request_id, "method": request.method, "path": request.url.path,
            "status": response.status_code, "ms": int((time.monotonic() - started) * 1000),
            "user_id": getattr(request.state, "user_id", None),
        }})
        return response

    install_error_handlers(app)

    @app.get("/health", tags=["system"])
    def health():
        # Deliberately touches nothing else, so it stays fast when dependencies are down.
        return ok({"status": "ok", "version": VERSION, "time": clock.now()})

    for router in (core_routes.router, claims_routes.router, advisor_routes.router, audit_routes.router):
        app.include_router(router, prefix="/api/v1")
    return app


_default_app: Optional[FastAPI] = None


def __getattr__(name: str):
    """`uvicorn app.main:app` works, but the app is only built when uvicorn asks for it.

    Importing this module (as the tests do) therefore has no side effects and needs no environment variables.
    """
    global _default_app
    if name == "app":
        if _default_app is None:
            _default_app = create_app()
        return _default_app
    raise AttributeError(name)
