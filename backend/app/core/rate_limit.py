"""In-process sliding-window limiter, per user (api.md section 1.8).

Per process: correct for a single Render instance. Replace with a shared store if the service is scaled out.
"""
from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict

from fastapi import Depends, Request

from app.core.auth import Principal, require_advisor
from app.core.errors import ApiError


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0, clock: Callable[[], float] = time.monotonic):
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = self._clock()
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - self.window:
                q.popleft()
            if len(q) >= self.limit:
                retry = max(1, math.ceil(q[0] + self.window - now))
                raise ApiError(429, "rate_limited", "Too many requests. Please wait a moment and try again.", retry_after_seconds=retry)
            q.append(now)


def llm_rate_limit(request: Request, p: Principal = Depends(require_advisor)) -> Principal:
    """Dependency for the LLM-backed endpoints (adviser-only; assistant and email drafts share one budget per user).
    The role check runs first, so a client is refused with 403 without consuming any budget."""
    request.app.state.llm_limiter.check(str(p.id))
    return p
