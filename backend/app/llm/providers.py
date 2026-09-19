"""Groq and Gemini over plain HTTPS (httpx).

UNVERIFIED AGAINST THE LIVE SERVICES: these request/response formats are written from knowledge of the providers' public
APIs and have only been exercised against mocked HTTP in the tests. Before relying on them, run one real request per
provider and confirm the model names you set in GROQ_MODEL / GEMINI_MODEL are currently available.
  * Groq is called through its OpenAI-compatible chat completions endpoint.
  * Gemini is called through the generateContent REST method.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.llm.base import LLMError, LLMProvider, Message

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _retry_after(resp: httpx.Response) -> Optional[int]:
    v = resp.headers.get("retry-after")
    try:
        return max(1, int(float(v))) if v else None
    except ValueError:
        return None


def _raise_for(resp: httpx.Response) -> None:
    if resp.status_code == 429:
        raise LLMError("rate_limited", "provider rate limit", _retry_after(resp))
    if resp.status_code >= 400:
        # 4xx other than 429 usually means a bad key or model name: treat as unavailable, do not echo the body.
        raise LLMError("unavailable", f"provider returned HTTP {resp.status_code}")


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str, client: Optional[httpx.Client] = None):
        self.model = model
        self._key = api_key
        self._client = client or httpx.Client()

    def generate(self, messages: List[Message], *, json_mode: bool, timeout_s: float) -> str:
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": 0.1,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            resp = self._client.post(GROQ_URL, json=body, headers={"Authorization": f"Bearer {self._key}"}, timeout=timeout_s)
        except httpx.HTTPError as e:
            raise LLMError("unavailable", type(e).__name__)
        _raise_for(resp)
        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError, TypeError):
            raise LLMError("bad_response", "unexpected response shape")


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, client: Optional[httpx.Client] = None):
        self.model = model
        self._key = api_key
        self._client = client or httpx.Client()

    def generate(self, messages: List[Message], *, json_mode: bool, timeout_s: float) -> str:
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        contents = [
            {"role": "model" if m.role == "assistant" else "user", "parts": [{"text": m.content}]}
            for m in messages if m.role != "system"
        ]
        body: Dict[str, Any] = {"contents": contents, "generationConfig": {"temperature": 0.1}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        try:
            resp = self._client.post(
                GEMINI_URL.format(model=self.model), json=body, headers={"x-goog-api-key": self._key}, timeout=timeout_s
            )
        except httpx.HTTPError as e:
            raise LLMError("unavailable", type(e).__name__)
        _raise_for(resp)
        try:
            return "".join(part["text"] for part in resp.json()["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError, ValueError, TypeError):
            raise LLMError("bad_response", "unexpected response shape")


def build_providers(settings) -> List[LLMProvider]:
    """Primary first, then the fallback. Missing keys are caught earlier by validate_settings."""
    out: List[LLMProvider] = []
    for name in (settings.llm_provider, settings.llm_fallback_provider):
        if name == "groq" and settings.groq_api_key:
            out.append(GroqProvider(settings.groq_api_key, settings.groq_model))
        elif name == "gemini" and settings.gemini_api_key:
            out.append(GeminiProvider(settings.gemini_api_key, settings.gemini_model))
    # Drop a duplicate if primary == fallback.
    seen, unique = set(), []
    for p in out:
        if p.name not in seen:
            seen.add(p.name)
            unique.append(p)
    return unique
