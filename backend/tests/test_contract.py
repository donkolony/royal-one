"""The implementation and docs/api.md must describe the same API. Drift in either direction fails here."""
import re

import pytest

from app.core.config import REPO_DIR

API_MD = (REPO_DIR / "docs" / "api.md").read_text(encoding="utf-8")


def documented():
    rows = re.findall(r"^\| (\d+) \| (GET|POST|PATCH|PUT|DELETE) \| `([^`]+)` \| ([^|]+) \| ([^|]+) \|$", API_MD, re.M)
    return {(m, "/health" if p == "/health" else "/api/v1" + p): (a.strip(), pr.strip()) for _, m, p, a, pr in rows}


def implemented(app):
    """Enumerate through the OpenAPI schema: this FastAPI version nests included routers, so app.routes is not flat."""
    out = set()
    for path, ops in app.openapi()["paths"].items():
        if path.startswith("/api/v1") or path == "/health":
            for method in ops:
                out.add((method.upper(), path))
    return out


def norm(path):
    return re.sub(r"\{[^}]+\}", "{}", path)


@pytest.fixture
def app(api):
    return api.c.app


def test_the_index_has_no_duplicate_rows():
    rows = re.findall(r"^\| (\d+) \| (?:GET|POST|PATCH|PUT|DELETE) \|", API_MD, re.M)
    assert len(rows) == len(set(rows)) == len(documented()) and len(rows) >= 68


def test_every_documented_endpoint_is_implemented(app):
    have = {(m, norm(p)) for m, p in implemented(app)}
    missing = [(m, p) for (m, p) in documented() if (m, norm(p)) not in have]
    assert missing == [], f"documented but not implemented: {missing}"


def test_every_implemented_endpoint_is_documented(app):
    docs = {(m, norm(p)) for m, p in documented()}
    extra = [(m, p) for (m, p) in implemented(app) if (m, norm(p)) not in docs]
    assert extra == [], f"implemented but not in docs/api.md: {extra}"


def test_documented_auth_matches_behaviour(api):
    """Anonymous callers get 401 on everything except /health and /meta."""
    public = {"/health", "/api/v1/meta"}
    sample = {"{client_id}": "00000000-0000-4000-8000-000000000000"}
    for (method, path), (auth, _prio) in documented().items():
        url = re.sub(r"\{[^}]+\}", sample["{client_id}"], path)
        r = api.c.request(method, url, json={} if method in ("POST", "PATCH", "PUT") else None)
        if path in public:
            assert r.status_code != 401, path
        else:
            assert r.status_code == 401, (method, path, r.status_code)
            assert auth != "none", (method, path)


def test_openapi_document_builds(app):
    spec = app.openapi()
    assert spec["info"]["title"] == "Royal Square Platform API" and "/api/v1/claims/{claim_id}/submit" in spec["paths"]


def test_static_routes_are_registered_before_parameterised_siblings(app):
    order = list(app.openapi()["paths"])
    assert order.index("/api/v1/claims/checklist") < order.index("/api/v1/claims/{claim_id}")
    assert order.index("/api/v1/claims/pipeline") < order.index("/api/v1/claims/{claim_id}")
    assert order.index("/api/v1/requests/types") < order.index("/api/v1/requests/{request_id}")


def test_the_openapi_route_count_matches_the_index(app):
    assert len(implemented(app)) == len(documented())
