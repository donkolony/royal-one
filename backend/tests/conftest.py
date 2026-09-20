"""Test harness: a real PostgreSQL (bundled by `pgserver`), the real migrations, the real demo seed, fake LLM and storage."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pgserver
import pytest
from fastapi.testclient import TestClient

from app import seed
from app.core.auth import make_test_token
from app.core.config import Settings
from app.core.db import make_pool
from app.core.migrate import apply_migrations
from app.llm.base import LLMRouter
from app.main import create_app
from app.storage.base import MemoryStorage

SECRET = "test-secret-test-secret-test-secret-0000"
ADVISER, ADVISER_2, OWNER = seed.ADVISER, seed.ADVISER_2, seed.OWNER
CLIENT_1, CLIENT_2, CLIENT_3, CLIENT_4 = seed.CLIENT_1, seed.CLIENT_2, seed.CLIENT_3, seed.CLIENT_4


@pytest.fixture(scope="session")
def pg_uri(tmp_path_factory):
    server = pgserver.get_server(tmp_path_factory.mktemp("pgdata"), cleanup_mode="delete")
    uri = server.get_uri()
    apply_migrations(uri)
    yield uri
    server.cleanup()


@pytest.fixture(scope="session")
def settings(pg_uri) -> Settings:
    # _env_file=None: tests must never pick up a developer's real backend/.env.
    return Settings(
        _env_file=None, database_url=pg_uri, auth_mode="local_hs256", supabase_jwt_secret=SECRET, storage_backend="memory",
        llm_provider="none", llm_fallback_provider="none", allowed_origins="http://localhost:5173", assistant_rate_limit_per_min=5,
    )


@pytest.fixture(scope="session")
def pool(pg_uri):
    p = make_pool(pg_uri, 1, 4)
    yield p
    p.close()


class FakeProvider:
    """Programmable LLM. `script` is a list of str (returned) or Exception (raised), consumed in order; the last repeats."""

    def __init__(self, name: str = "groq", model: str = "fake-model", script: Optional[List[Any]] = None):
        self.name, self.model = name, model
        self.script = list(script or [])
        self.calls: List[Dict[str, Any]] = []

    def generate(self, messages, *, json_mode: bool, timeout_s: float) -> str:
        self.calls.append({"messages": messages, "json_mode": json_mode})
        item = self.script.pop(0) if len(self.script) > 1 else (self.script[0] if self.script else "{}")
        if isinstance(item, Exception):
            raise item
        return item(messages) if callable(item) else item


@pytest.fixture
def storage() -> MemoryStorage:
    return MemoryStorage()


@pytest.fixture
def fresh_db(pool, settings, storage):
    """Empty and reseed the demo data before each test."""
    with pool.connection() as conn:
        seed.reset_data(conn)
        seed.seed_demo(conn, settings, storage)
    return pool


class Api:
    def __init__(self, client: TestClient):
        self.c = client

    def _h(self, user, headers):
        h = dict(headers or {})
        if user is not None:
            h["Authorization"] = f"Bearer {make_test_token(SECRET, str(user))}"
        return h

    def request(self, method: str, path: str, user=None, headers=None, **kw):
        return self.c.request(method, f"/api/v1{path}", headers=self._h(user, headers), **kw)

    def get(self, path, user=None, **kw): return self.request("GET", path, user, **kw)
    def post(self, path, user=None, **kw): return self.request("POST", path, user, **kw)
    def patch(self, path, user=None, **kw): return self.request("PATCH", path, user, **kw)
    def put(self, path, user=None, **kw): return self.request("PUT", path, user, **kw)
    def delete(self, path, user=None, **kw): return self.request("DELETE", path, user, **kw)


@pytest.fixture
def make_app(settings, fresh_db, storage):
    def _make(llm: Optional[LLMRouter] = None, **kw) -> Api:
        app = create_app(settings, pool=fresh_db, storage=storage, llm=llm or LLMRouter([]), **kw)
        return Api(TestClient(app, raise_server_exceptions=False))
    return _make


@pytest.fixture
def api(make_app) -> Api:
    return make_app()


@pytest.fixture
def db(fresh_db):
    """A connection for asserting on / arranging database state directly."""
    with fresh_db.connection() as conn:
        yield conn


def png_bytes() -> bytes:
    return seed.PNG_1X1


def ids_of(resp) -> List[str]:
    return [i["id"] for i in resp.json()["items"]]


def claim_id(name: str) -> str:
    return str(seed.uid(f"claim-{name}"))


def audit_rows(db, **where):
    """Audit entries matching column=value pairs, oldest first (arranging and asserting on the trail directly)."""
    clause = " and ".join(f"{k} = %s" for k in where) or "true"
    return db.execute(f"select * from audit_log where {clause} order by id", list(where.values())).fetchall()
