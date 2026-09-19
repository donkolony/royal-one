"""System endpoints, the error envelope, headers, and token handling."""
import re

import jwt

from app.core.auth import make_test_token
from conftest import ADVISER, CLIENT_1, SECRET


def test_health_needs_no_auth_and_touches_no_database(api):
    r = api.c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok" and r.json()["version"] == "0.1.0"
    assert r.json()["time"].endswith("Z")


def test_meta_is_public_cacheable_and_complete(api):
    r = api.get("/meta")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "public, max-age=3600"
    m = r.json()
    assert [s["value"] for s in m["claim_statuses"]] == ["draft", "submitted", "registered", "assessment", "quotes", "authorised", "in_repair", "completed", "closed"]
    assert m["claim_statuses"][2]["client_label"] == "Registered with your insurer"
    assert m["currency"] == "ZAR" and "motor" in m["policy_categories"]
    assert m["attachment_rules"]["max_bytes"] == 10485760
    assert {t["type"] for t in m["reminder_types"]} >= {"licence_expiry", "claim_police_report", "custom"}


def test_static_reference_endpoints_are_privately_cacheable(api):
    for path in ("/insurers", "/claims/checklist", "/requests/types"):
        r = api.get(path, user=CLIENT_1)
        assert r.status_code == 200 and r.headers["cache-control"] == "private, max-age=3600", path
    assert api.get("/me", user=CLIENT_1).headers["cache-control"] == "no-store"


def test_insurers_are_the_prd_list_plus_other(api):
    names = [i["name"] for i in api.get("/insurers", user=CLIENT_1).json()["items"]]
    assert set(names) == {"Sanlam", "Old Mutual", "Liberty", "Momentum", "Discovery", "Allan Gray", "Santam", "Other"}
    assert names[-1] == "Other"


def test_request_id_is_generated_and_echoed(api):
    r = api.get("/meta")
    assert re.fullmatch(r"[0-9a-f-]{36}", r.headers["x-request-id"])
    r = api.get("/meta", headers={"X-Request-ID": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"
    r = api.get("/meta", headers={"X-Request-ID": "bad id with spaces!"})
    assert r.headers["x-request-id"] != "bad id with spaces!"


def test_error_envelope_shape(api):
    r = api.get("/me")
    assert r.status_code == 401
    e = r.json()["error"]
    assert e["code"] == "unauthenticated" and e["request_id"] == r.headers["x-request-id"]


def test_unknown_route_uses_the_envelope(api):
    r = api.get("/nope", user=CLIENT_1)
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_validation_errors_use_the_envelope_with_field_paths(api):
    r = api.patch("/me", user=CLIENT_1, json={"phone": "x" * 40, "surprise": 1})
    assert r.status_code == 422
    e = r.json()["error"]
    assert e["code"] == "validation_error"
    fields = {d["field"]: d["code"] for d in e["details"]}
    assert fields["phone"] == "too_long" and fields["surprise"] == "extra_forbidden"


def test_malformed_json_is_400(api):
    r = api.patch("/me", user=CLIENT_1, content=b"{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_request"


def test_bad_uuid_and_bad_query_are_validation_errors(api):
    assert api.get("/claims/not-a-uuid", user=CLIENT_1).status_code == 422
    r = api.get("/claims?limit=1000", user=CLIENT_1)
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "limit"


def test_cors_allows_the_configured_origin_only(api):
    ok = api.c.options("/api/v1/me", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET",
                                              "Access-Control-Request-Headers": "authorization"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    bad = api.c.options("/api/v1/me", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_unhandled_exception_is_a_500_envelope_without_internals(make_app, monkeypatch):
    api = make_app()
    from app.services import clients
    monkeypatch.setattr(clients, "get_me", lambda *a, **k: 1 / 0)
    r = api.get("/me", user=CLIENT_1)
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error" and "division" not in r.text
    assert r.headers["x-request-id"]


# ------------------------------------------------------------------------------------------------ tokens
def test_missing_or_malformed_authorization_is_401(api):
    assert api.get("/me").json()["error"]["code"] == "unauthenticated"
    r = api.c.get("/api/v1/me", headers={"Authorization": "Basic abc"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthenticated"


def test_garbage_token_is_token_invalid(api):
    r = api.c.get("/api/v1/me", headers={"Authorization": "Bearer not.a.token"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "token_invalid"


def test_expired_token_is_token_expired(api):
    tok = make_test_token(SECRET, str(CLIENT_1), expires_in=-10)
    r = api.c.get("/api/v1/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "token_expired"


def test_token_signed_with_the_wrong_secret_is_rejected(api):
    tok = make_test_token("some-other-secret-some-other-secret-00", str(CLIENT_1))
    r = api.c.get("/api/v1/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "token_invalid"


def test_unsigned_token_with_alg_none_is_rejected(api):
    tok = jwt.encode({"sub": str(ADVISER), "aud": "authenticated", "exp": 9999999999}, key=None, algorithm="none")
    r = api.c.get("/api/v1/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


def test_valid_user_without_a_profile_is_403(api):
    r = api.get("/me", user="11111111-1111-4111-8111-111111111111")
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"


def test_role_comes_from_the_profile_not_the_token(api):
    """A token claiming to be an adviser (role claims) must not grant adviser rights to a client."""
    tok = jwt.encode({"sub": str(CLIENT_1), "aud": "authenticated", "exp": 9999999999, "role": "advisor",
                      "user_metadata": {"role": "advisor"}, "app_metadata": {"role": "advisor"}}, SECRET, algorithm="HS256")
    r = api.c.get("/api/v1/clients", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403
    assert api.c.get("/api/v1/me", headers={"Authorization": f"Bearer {tok}"}).json()["role"] == "client"
