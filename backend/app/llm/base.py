"""LLM providers behind one interface (docs/ARCHITECT.md section 8.6)."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Protocol

from app.core.errors import ApiError

log = logging.getLogger("app.llm")


@dataclass
class Message:
    role: str  # system | user | assistant
    content: str


class LLMError(Exception):
    """kind: 'rate_limited' | 'unavailable' | 'bad_response'."""

    def __init__(self, kind: str, message: str = "", retry_after: Optional[int] = None, transient: bool = False):
        super().__init__(message or kind)
        self.kind = kind
        self.retry_after = retry_after
        self.transient = transient  # a 5xx or network failure: worth one quick retry (a bad key or model name is not)


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
    """Try the primary provider, then the fallback; raise the contract's 503 if all fail.

    A transient failure (5xx, network) is retried once on the same provider after a short pause, because providers
    do return brief "high demand" errors. Rate limits and configuration errors are not retried: they go to the fallback.
    """

    def __init__(self, providers: List[LLMProvider], timeout_s: float = 20.0, retry_delay_s: float = 1.0,
                 sleep: Callable[[float], None] = time.sleep):
        self.providers = providers
        self.timeout_s = timeout_s
        self.retry_delay_s = retry_delay_s
        self._sleep = sleep

    @property
    def configured(self) -> bool:
        return bool(self.providers)

    def generate(self, messages: List[Message], *, json_mode: bool = True) -> LLMResult:
        retry_hint: Optional[int] = None
        for prov in self.providers:
            for attempt in (1, 2):
                try:
                    text = prov.generate(messages, json_mode=json_mode, timeout_s=self.timeout_s)
                    return LLMResult(text=text, provider=prov.name, model=prov.model)
                except LLMError as e:
                    log.warning("llm provider %s failed: %s (attempt %d)", prov.name, e.kind, attempt)
                    if e.retry_after:
                        retry_hint = max(retry_hint or 0, e.retry_after)
                    if e.transient and attempt == 1:
                        self._sleep(self.retry_delay_s)
                        continue
                    break
        raise ApiError(503, "llm_unavailable", "The assistant is temporarily unavailable. Please try again shortly.", retry_after_seconds=retry_hint or 30)
