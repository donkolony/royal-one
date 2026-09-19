"""Groq and Gemini adapters against mocked HTTP. NOT verified against the live services (see providers.py)."""
import json

import httpx
import pytest

from app.core.config import Settings
from app.llm.base import LLMError, LLMRouter, Message
from app.llm.providers import GEMINI_URL, GROQ_URL, GeminiProvider, GroqProvider, build_providers
from conftest import FakeProvider

MSGS = [Message("system", "be brief"), Message("user", "hi"), Message("assistant", "hello"), Message("user", "again")]


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


# --------------------------------------------------------------------------------------------- groq
def test_groq_request_and_response_shape():
    seen = {}

    def handler(req: httpx.Request):
        seen.update(url=str(req.url), auth=req.headers["authorization"], body=json.loads(req.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok":true}'}}]})

    p = GroqProvider("KEY", "some-model", client(handler))
    assert p.generate(MSGS, json_mode=True, timeout_s=5) == '{"ok":true}'
    assert seen["url"] == GROQ_URL and seen["auth"] == "Bearer KEY"
    b = seen["body"]
    assert b["model"] == "some-model" and b["response_format"] == {"type": "json_object"} and b["temperature"] <= 0.2
    assert [m["role"] for m in b["messages"]] == ["system", "user", "assistant", "user"]


def test_groq_without_json_mode_omits_response_format():
    seen = {}
    p = GroqProvider("K", "m", client(lambda r: (seen.update(b=json.loads(r.content)), httpx.Response(200, json={"choices": [{"message": {"content": "x"}}]}))[1]))
    p.generate(MSGS, json_mode=False, timeout_s=5)
    assert "response_format" not in seen["b"]


@pytest.mark.parametrize("status,headers,kind,retry", [
    (429, {"retry-after": "7"}, "rate_limited", 7), (429, {}, "rate_limited", None), (500, {}, "unavailable", None),
    (503, {}, "unavailable", None), (401, {}, "unavailable", None), (404, {}, "unavailable", None),
])
def test_groq_error_mapping(status, headers, kind, retry):
    p = GroqProvider("K", "m", client(lambda r: httpx.Response(status, headers=headers, json={"error": "secret detail"})))
    with pytest.raises(LLMError) as e:
        p.generate(MSGS, json_mode=True, timeout_s=5)
    assert e.value.kind == kind and e.value.retry_after == retry and "secret detail" not in str(e.value)


@pytest.mark.parametrize("payload", [{}, {"choices": []}, {"choices": [{"message": {}}]}, [1, 2]])
def test_groq_bad_shapes_are_bad_response(payload):
    p = GroqProvider("K", "m", client(lambda r: httpx.Response(200, json=payload)))
    with pytest.raises(LLMError) as e:
        p.generate(MSGS, json_mode=True, timeout_s=5)
    assert e.value.kind == "bad_response"


def test_groq_network_failure_is_unavailable():
    def boom(req):
        raise httpx.ConnectTimeout("slow")
    with pytest.raises(LLMError) as e:
        GroqProvider("K", "m", client(boom)).generate(MSGS, json_mode=True, timeout_s=1)
    assert e.value.kind == "unavailable"


# ------------------------------------------------------------------------------------------- gemini
def test_gemini_request_and_response_shape():
    seen = {}

    def handler(req: httpx.Request):
        seen.update(url=str(req.url), key=req.headers["x-goog-api-key"], body=json.loads(req.content))
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"a":'}, {"text": "1}"}]}}]})

    p = GeminiProvider("KEY", "gem-model", client(handler))
    assert p.generate(MSGS, json_mode=True, timeout_s=5) == '{"a":1}'
    assert seen["url"] == GEMINI_URL.format(model="gem-model") and seen["key"] == "KEY" and "KEY" not in seen["url"]
    b = seen["body"]
    assert b["systemInstruction"] == {"parts": [{"text": "be brief"}]}
    assert [c["role"] for c in b["contents"]] == ["user", "model", "user"]
    assert b["generationConfig"]["responseMimeType"] == "application/json"


@pytest.mark.parametrize("status,kind", [(429, "rate_limited"), (500, "unavailable"), (403, "unavailable")])
def test_gemini_error_mapping(status, kind):
    p = GeminiProvider("K", "m", client(lambda r: httpx.Response(status, json={})))
    with pytest.raises(LLMError) as e:
        p.generate(MSGS, json_mode=True, timeout_s=5)
    assert e.value.kind == kind


def test_gemini_bad_shape():
    p = GeminiProvider("K", "m", client(lambda r: httpx.Response(200, json={"candidates": []})))
    with pytest.raises(LLMError) as e:
        p.generate(MSGS, json_mode=False, timeout_s=5)
    assert e.value.kind == "bad_response"


# ----------------------------------------------------------------------------------- router + config
def test_router_falls_back_and_reports_who_answered():
    r = LLMRouter([FakeProvider("groq", "a", [LLMError("unavailable")]), FakeProvider("gemini", "b", ["ok"])])
    res = r.generate(MSGS)
    assert (res.text, res.provider, res.model) == ("ok", "gemini", "b")


def test_router_with_no_providers_is_unconfigured():
    assert LLMRouter([]).configured is False


def _s(**kw):
    return Settings(_env_file=None, database_url="postgresql://x", auth_mode="local_hs256", supabase_jwt_secret="s" * 40,
                    storage_backend="memory", **kw)


def test_build_providers_order_dedupe_and_missing_keys():
    both = build_providers(_s(llm_provider="groq", llm_fallback_provider="gemini", groq_api_key="g", groq_model="gm", gemini_api_key="k", gemini_model="km"))
    assert [p.name for p in both] == ["groq", "gemini"]
    same = build_providers(_s(llm_provider="groq", llm_fallback_provider="groq", groq_api_key="g", groq_model="gm"))
    assert [p.name for p in same] == ["groq"]
    assert build_providers(_s(llm_provider="groq", groq_api_key="", groq_model="m")) == []
    assert build_providers(_s()) == []


def test_missing_required_names_every_variable():
    s = Settings(_env_file=None)
    assert s.missing_required() == ["DATABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_URL"]
    s = _s(llm_provider="groq", llm_fallback_provider="gemini")
    assert s.missing_required() == ["GEMINI_API_KEY", "GEMINI_MODEL", "GROQ_API_KEY", "GROQ_MODEL"]
    assert _s().missing_required() == []


def test_the_app_refuses_to_start_without_required_settings():
    from app.main import create_app
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_app(Settings(_env_file=None, auth_mode="local_hs256", supabase_jwt_secret="s" * 40, storage_backend="memory"))


def test_gmail_is_refused():
    with pytest.raises(ValueError, match="gmail"):
        Settings(_env_file=None, email_provider="gmail")


# ------------------------------------------------------------------------------------ transient retries
def _router(*providers):
    delays = []
    return LLMRouter(list(providers), retry_delay_s=0.5, sleep=delays.append), delays


def test_transient_errors_are_retried_once_on_the_same_provider():
    p = FakeProvider("gemini", "m", [LLMError("unavailable", transient=True), "recovered"])
    router, delays = _router(p)
    assert router.generate(MSGS).text == "recovered"
    assert len(p.calls) == 2 and delays == [0.5]


def test_a_persistent_transient_error_falls_back_after_one_retry():
    a = FakeProvider("groq", "a", [LLMError("unavailable", transient=True)])
    b = FakeProvider("gemini", "b", ["from backup"])
    router, delays = _router(a, b)
    res = router.generate(MSGS)
    assert res.provider == "gemini" and len(a.calls) == 2 and len(b.calls) == 1 and delays == [0.5]


def test_configuration_errors_and_rate_limits_are_not_retried():
    for err in (LLMError("unavailable"), LLMError("rate_limited", retry_after=3), LLMError("bad_response")):
        a = FakeProvider("groq", "a", [err])
        router, delays = _router(a, FakeProvider("gemini", "b", ["ok"]))
        assert router.generate(MSGS).provider == "gemini"
        assert len(a.calls) == 1 and delays == [], err.kind


def test_providers_mark_only_server_and_network_failures_as_transient():
    def raises(status):
        p = GroqProvider("K", "m", client(lambda r: httpx.Response(status, json={})))
        with pytest.raises(LLMError) as e:
            p.generate(MSGS, json_mode=True, timeout_s=5)
        return e.value.transient
    assert raises(503) is True and raises(500) is True
    assert raises(401) is False and raises(404) is False and raises(429) is False

    def boom(req):
        raise httpx.ReadTimeout("slow")
    with pytest.raises(LLMError) as e:
        GeminiProvider("K", "m", client(boom)).generate(MSGS, json_mode=True, timeout_s=1)
    assert e.value.transient is True


# ---------------------------------------------------------------------------------- obviously-wrong values
def test_config_problems_catch_the_common_mistakes():
    from app.core.config import validate_settings
    bad = Settings(_env_file=None, database_url="https://abc.supabase.co/rest/v1/", auth_mode="local_hs256", supabase_jwt_secret="s" * 40,
                   storage_backend="supabase", supabase_url="https://abc.supabase.co", supabase_service_role_key="sb_publishable_abc",
                   llm_provider="groq", groq_api_key="xai-123", groq_model="m")
    probs = bad.config_problems()
    assert len(probs) == 3
    assert "REST API address" in probs[0] and "publishable" in probs[1] and "xAI" in probs[2]
    with pytest.raises(RuntimeError) as e:
        validate_settings(bad)
    assert "DATABASE_URL" in str(e.value) and "publishable" in str(e.value)
    assert "sb_publishable_abc" not in str(e.value), "the message must never echo a key"


def test_config_problems_are_quiet_for_valid_values():
    ok = Settings(_env_file=None, database_url="postgresql://u:p@host:6543/postgres", auth_mode="supabase", supabase_url="https://a.supabase.co",
                  supabase_service_role_key="sb_secret_abc", llm_provider="gemini", gemini_api_key="k", gemini_model="m",
                  groq_api_key="xai-not-used-because-groq-is-not-selected")
    assert ok.config_problems() == []
    legacy = Settings(_env_file=None, database_url="postgres://u:p@h/db", auth_mode="supabase", supabase_url="https://a.supabase.co",
                      supabase_service_role_key="eyJhbGciOi.legacy.jwt")
    assert legacy.config_problems() == []
