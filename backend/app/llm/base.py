"""LLM providers behind one interface (docs/ARCHITECT.md section 8.6)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Protocol

from app.core.errors import ApiError

log = logging.getLogger("app.llm")


@dataclass
class Message:
    role: str  # system | user | assistant
    content: str


class LLMError(Exception):
    """kind: 'rate_limited' | 'unavailable' | 'bad_response'."""

    def __init__(self, kind: str, message: str = "", retry_after: Optional[int] = None):
        super().__init__(message or kind)
        self.kind = kind
        self.retry_after = retry_after


class LLMProvider(Protocol):
    name: str
    model: str

    def generate(self, messages: List[Message], *, json_mode: bool, timeout_s: float) -> str: ...


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str


class LLMRouter:
    """Try the primary provider, then the fallback; raise the contract's 503 if all fail."""

    def __init__(self, providers: List[LLMProvider], timeout_s: float = 20.0):
        self.providers = providers
        self.timeout_s = timeout_s

    @property
    def configured(self) -> bool:
        return bool(self.providers)

    def generate(self, messages: List[Message], *, json_mode: bool = True) -> LLMResult:
        retry_hint: Optional[int] = None
        for prov in self.providers:
            try:
                text = prov.generate(messages, json_mode=json_mode, timeout_s=self.timeout_s)
                return LLMResult(text=text, provider=prov.name, model=prov.model)
            except LLMError as e:
                log.warning("llm provider %s failed: %s", prov.name, e.kind)
                if e.retry_after:
                    retry_hint = max(retry_hint or 0, e.retry_after)
        raise ApiError(503, "llm_unavailable", "The assistant is temporarily unavailable. Please try again shortly.", retry_after_seconds=retry_hint or 30)
