"""Authentication (who is this?) and authorization scoping (what may they see?).

Roles always come from the `profiles` table, never from token claims a user can edit
(docs/ARCHITECT.md section 4).
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple
from uuid import UUID

import jwt
import psycopg
from fastapi import Depends, Request

from app.core import clock
from app.core.db import fetch_all, fetch_one, get_conn
from app.core.errors import ApiError, forbidden

log = logging.getLogger("app.auth")


# ------------------------------------------------------------------------------------ token verification
class TokenVerifier(Protocol):
    def verify(self, token: str) -> str:
        """Return the user id (the `sub` claim) or raise ApiError(401/502)."""


def _unverified_exp(token: str) -> Optional[float]:
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return None
    exp = claims.get("exp")
    return float(exp) if exp is not None else None


class LocalHS256Verifier:
    """Verifies HS256 tokens with a shared secret. Used by the tests and for offline development."""

    def __init__(self, secret: str):
        self._secret = secret

    def verify(self, token: str) -> str:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"require": ["exp", "sub"]},
            )
        except jwt.ExpiredSignatureError:
            raise ApiError(401, "token_expired", "Your session has expired. Please sign in again.")
        except jwt.PyJWTError:
            raise ApiError(401, "token_invalid", "The access token is not valid.")
        return str(claims["sub"])


class SupabaseTokenVerifier:
    """Uses supabase-py `auth.get_claims`.

    Verified in the installed library source (supabase-auth 2.31): tokens signed with an asymmetric key are
    checked locally against the project's JWKS; HS256 tokens are checked by asking Supabase Auth. Which kind
    your project issues depends on its JWT signing settings.
    A short in-memory cache avoids a round trip per request.
    """

    def __init__(self, url: str, key: str, cache_ttl: float = 60.0, cache_max: int = 1000):
        from supabase import create_client

        self._client = create_client(url, key)
        self._ttl = cache_ttl
        self._max = cache_max
        self._cache: Dict[str, Tuple[float, str]] = {}
        self._lock = threading.Lock()

    def verify(self, token: str) -> str:
        key = hashlib.sha256(token.encode()).hexdigest()
        now = time.time()
        exp = _unverified_exp(token)
        if exp is not None and exp < now:
            raise ApiError(401, "token_expired", "Your session has expired. Please sign in again.")
        with self._lock:
            hit = self._cache.get(key)
            if hit and hit[0] > now:
                return hit[1]
        from supabase_auth.errors import AuthApiError, AuthInvalidJwtError

        try:
            res = self._client.auth.get_claims(token)
        except (AuthInvalidJwtError, AuthApiError) as e:
            if isinstance(e, AuthApiError) and getattr(e, "status", 401) >= 500:
                raise ApiError(502, "upstream_error", "Authentication service unavailable.")
            raise ApiError(401, "token_invalid", "The access token is not valid.")
        except Exception:  # network failure, unexpected library error
            log.exception("token verification failed unexpectedly")
            raise ApiError(502, "upstream_error", "Authentication service unavailable.")
        sub = (res or {}).get("claims", {}).get("sub") if res else None
        if not sub:
            raise ApiError(401, "token_invalid", "The access token is not valid.")
        expires = min(now + self._ttl, exp) if exp else now + self._ttl
        with self._lock:
            if len(self._cache) >= self._max:
                self._cache.clear()
            self._cache[key] = (expires, str(sub))
        return str(sub)


# ------------------------------------------------------------------------------------ principal + scoping
@dataclass
class Principal:
    id: UUID
    role: str
    full_name: str
    email: str
    phone: Optional[str] = None
    # Request context, recorded on every audit entry (docs/AUDIT.md build step 1). IP is as reported by the proxy chain.
    ip: Optional[str] = field(default=None, repr=False)
    user_agent: Optional[str] = field(default=None, repr=False)
    request_id: Optional[str] = field(default=None, repr=False)
    _pool: Any = field(default=None, repr=False)     # lets a denied attempt be logged outside the request's transaction
    _client_ids: Optional[List[UUID]] = field(default=None, repr=False)

    @property
    def is_advisor(self) -> bool:
        return self.role == "advisor"

    @property
    def is_client(self) -> bool:
        return self.role == "client"

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"

    @property
    def is_staff(self) -> bool:
        """Adviser or owner: anyone who is not a client."""
        return self.role in ("advisor", "owner")

    def client_ids(self, conn: psycopg.Connection) -> List[UUID]:
        """The one scoping rule (ARCHITECT 4.3): a client sees themselves, an adviser sees assigned clients,
        the owner sees every client."""
        if self._client_ids is None:
            if self.is_client:
                self._client_ids = [self.id]
            elif self.is_owner:
                self._client_ids = [r["id"] for r in fetch_all(conn, "select id from clients")]
            else:
                rows = fetch_all(conn, "select id from clients where adviser_id = %s", (self.id,))
                self._client_ids = [r["id"] for r in rows]
        return self._client_ids


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization")
    if not header:
        raise ApiError(401, "unauthenticated", "Sign in to continue.")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ApiError(401, "unauthenticated", "Send the access token as 'Authorization: Bearer <token>'.")
    return token.strip()


def get_principal(request: Request, conn: psycopg.Connection = Depends(get_conn)) -> Principal:
    token = _bearer(request)
    user_id = request.app.state.verifier.verify(token)
    row = fetch_one(conn, "select id, role, full_name, email, phone from profiles where id = %s", (user_id,))
    if row is None:
        # A valid Supabase user with no profile row: the account has not been provisioned.
        raise forbidden("This account is not set up yet. Contact Royal Square.")
    principal = Principal(**row)
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    principal.ip = (forwarded or (request.client.host if request.client else None) or None)
    principal.user_agent = (request.headers.get("user-agent") or "")[:200] or None
    principal.request_id = getattr(request.state, "request_id", None)
    principal._pool = getattr(request.app.state, "pool", None)
    request.state.user_id = str(principal.id)
    return principal


def require_client(p: Principal = Depends(get_principal)) -> Principal:
    if not p.is_client:
        raise forbidden("This action is only available to clients.")
    return p


def require_advisor(p: Principal = Depends(get_principal)) -> Principal:
    if not p.is_advisor:
        raise forbidden("This action is only available to advisers.")
    return p


def require_staff(p: Principal = Depends(get_principal)) -> Principal:
    if not p.is_staff:
        raise forbidden("This action is only available to Royal Square staff.")
    return p


def require_owner(p: Principal = Depends(get_principal)) -> Principal:
    if not p.is_owner:
        raise forbidden("This action is only available to the firm's owner.")
    return p


def make_test_token(secret: str, user_id: str, expires_in: int = 3600) -> str:
    """Sign an HS256 token the way Supabase does. For tests and local development only."""
    now = int(clock.now().timestamp())
    return jwt.encode(
        {"sub": str(user_id), "aud": "authenticated", "role": "authenticated", "iat": now, "exp": now + expires_in},
        secret,
        algorithm="HS256",
    )
