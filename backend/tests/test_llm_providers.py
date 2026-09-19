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
