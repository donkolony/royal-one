"""Small pure pieces: file sniffing, filenames, rate limiter, http helpers, migrations, Supabase verifier."""
import jwt
import pytest

from app.core.auth import LocalHS256Verifier, SupabaseTokenVerifier, make_test_token
from app.core.errors import ApiError
from app.core.http import _default
from app.core.migrate import apply_migrations
from app.core.rate_limit import RateLimiter
from app.storage.base import MemoryStorage, safe_filename
from app.storage.sniff import sniff_content_type
from app.services.requests import mask_account
from conftest import SECRET


@pytest.mark.parametrize("data,expected", [
    (b"\xff\xd8\xff\xe0" + b"0" * 12, "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n" + b"0" * 8, "image/png"),
    (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "image/webp"),
    (b"RIFF\x00\x00\x00\x00WAVEfmt ", "audio/wav"),
    (b"%PDF-1.7\n", "application/pdf"),
    (b"\x1a\x45\xdf\xa3" + b"0" * 12, "audio/webm"),
    (b"OggS\x00\x02" + b"0" * 10, "audio/ogg"),
    (b"\x00\x00\x00\x18ftypM4A " + b"0" * 8, "audio/mp4"),
    (b"ID3\x03\x00" + b"0" * 11, "audio/mpeg"),
    (b"\xff\xfb\x90\x00" + b"0" * 12, "audio/mpeg"),
    (b"MZ\x90\x00", None), (b"<html>", None), (b"GIF89a", None), (b"", None), (b"PK\x03\x04", None),
])
def test_sniff(data, expected):
    assert sniff_content_type(data) == expected


@pytest.mark.parametrize("name,expected", [
    ("photo.jpg", "photo.jpg"), ("../../etc/passwd", "passwd"), ("C:\\Users\\me\\a b.png", "a_b.png"),
    ("   ", "file"), ("....", "file"), ("a" * 300 + ".png", "a" * 100), ("naïve-file (1).png", "na_ve-file_1_.png".replace("_.png", ".png")),
])
def test_safe_filename(name, expected):
    got = safe_filename(name)
    assert "/" not in got and "\\" not in got and ".." not in got and len(got) <= 100
    if name in ("photo.jpg", "../../etc/passwd", "   ", "...."):
        assert got == expected


def test_mask_account():
    assert mask_account("1234567890") == "******7890" and mask_account("123") == "123" and mask_account("") == ""


def test_datetimes_render_in_utc_with_z():
    from datetime import date, datetime, timedelta, timezone
    from uuid import UUID
    from decimal import Decimal
    assert _default(datetime(2026, 9, 19, 14, 30, tzinfo=timezone(timedelta(hours=2)))) == "2026-09-19T12:30:00Z"
    assert _default(datetime(2026, 9, 19, 14, 30)) == "2026-09-19T14:30:00Z"
    assert _default(date(2026, 9, 19)) == "2026-09-19" and _default(Decimal("5")) == 5 and _default(Decimal("5.5")) == 5.5
    assert _default(UUID(int=1)) == "00000000-0000-0000-0000-000000000001"
    with pytest.raises(TypeError):
        _default(object())


def test_rate_limiter_window_and_keys():
    now = [0.0]
    rl = RateLimiter(2, 60.0, clock=lambda: now[0])
    rl.check("a"), rl.check("a")
    with pytest.raises(ApiError) as e:
        rl.check("a")
    assert e.value.status == 429 and e.value.retry_after_seconds == 60
    rl.check("b")  # other users are unaffected
    now[0] = 30
    with pytest.raises(ApiError) as e:
        rl.check("a")
    assert e.value.retry_after_seconds == 30
    now[0] = 61
    rl.check("a")


def test_memory_storage_round_trip():
    s = MemoryStorage()
    s.put("b", "p/x.png", b"data", "image/png")
    assert s.files[("b", "p/x.png")] == (b"data", "image/png")
    assert s.signed_urls("b", ["p/x.png"], 60)["p/x.png"].startswith("memory://b/p/x.png?expires=")
    s.delete("b", ["p/x.png"])
    assert not s.files


def test_migrations_are_idempotent_and_ordered(pg_uri):
    assert apply_migrations(pg_uri) == []


def test_every_table_has_the_expected_constraints(db):
    checks = {r["conname"] for r in db.execute("select conname from pg_constraint where contype = 'c'").fetchall()}
    assert "attachments_one_parent" in checks
    import psycopg
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("insert into attachments (kind, storage_path, filename, content_type, size_bytes, uploaded_by) "
                   "select 'other','p','f','image/png',1,id from profiles limit 1")
    db.rollback()


def test_claim_reference_sequence_and_unique_dedupe_key(db):
    import psycopg
    with pytest.raises(psycopg.errors.UniqueViolation):
        for _ in range(2):
            db.execute("insert into reminders (client_id, type, title, due_date, audience, source, dedupe_key) "
                       "select id, 'x', 't', now()::date, 'both', 'rule', 'dup-key' from clients limit 1")
    db.rollback()


# ---------------------------------------------------------------------------------- token verifiers
def test_hs256_verifier():
    v = LocalHS256Verifier(SECRET)
    assert v.verify(make_test_token(SECRET, "user-1")) == "user-1"
    with pytest.raises(ApiError) as e:
        v.verify(make_test_token(SECRET, "user-1", expires_in=-5))
    assert e.value.code == "token_expired"
    with pytest.raises(ApiError) as e:
        v.verify(jwt.encode({"sub": "u", "aud": "someone-else", "exp": 9999999999}, SECRET, algorithm="HS256"))
    assert e.value.code == "token_invalid"
    with pytest.raises(ApiError):
        v.verify(jwt.encode({"aud": "authenticated", "exp": 9999999999}, SECRET, algorithm="HS256"))  # no sub


class FakeAuth:
    def __init__(self, result=None, exc=None):
        self.result, self.exc, self.calls = result, exc, 0

    def get_claims(self, token):
        self.calls += 1
        if self.exc:
            raise self.exc
        return self.result


def supabase_verifier(monkeypatch, auth):
    import supabase
    monkeypatch.setattr(supabase, "create_client", lambda url, key: type("C", (), {"auth": auth})())
    return SupabaseTokenVerifier("https://x.supabase.example", "key")


def test_supabase_verifier_success_and_caching(monkeypatch):
    auth = FakeAuth({"claims": {"sub": "user-9"}})
    v = supabase_verifier(monkeypatch, auth)
    tok = make_test_token(SECRET, "user-9")
    assert v.verify(tok) == "user-9" and v.verify(tok) == "user-9"
    assert auth.calls == 1, "second call is served from the cache"


def test_supabase_verifier_maps_errors(monkeypatch):
    from supabase_auth.errors import AuthApiError, AuthInvalidJwtError
    tok = make_test_token(SECRET, "u")
    cases = [
        (AuthInvalidJwtError("bad"), 401, "token_invalid"),
        (AuthApiError("nope", 401, None), 401, "token_invalid"),
        (AuthApiError("down", 503, None), 502, "upstream_error"),
        (RuntimeError("network"), 502, "upstream_error"),
    ]
    for exc, status, code in cases:
        v = supabase_verifier(monkeypatch, FakeAuth(exc=exc))
        with pytest.raises(ApiError) as e:
            v.verify(tok)
        assert (e.value.status, e.value.code) == (status, code)
    with pytest.raises(ApiError) as e:
        supabase_verifier(monkeypatch, FakeAuth(result={"claims": {}})).verify(tok)
    assert e.value.code == "token_invalid"


def test_supabase_verifier_rejects_expired_without_calling_supabase(monkeypatch):
    auth = FakeAuth({"claims": {"sub": "u"}})
    with pytest.raises(ApiError) as e:
        supabase_verifier(monkeypatch, auth).verify(make_test_token(SECRET, "u", expires_in=-5))
    assert e.value.code == "token_expired" and auth.calls == 0


def test_importing_app_main_has_no_side_effects_and_uvicorn_can_find_app(monkeypatch):
    """`uvicorn app.main:app` must work, but merely importing the module must not build the app or need env vars."""
    import app.main as main
    monkeypatch.setattr(main, "_default_app", None)
    sentinel = object()
    monkeypatch.setattr(main, "create_app", lambda: sentinel)
    assert main.app is sentinel and main.app is sentinel  # built once, then reused
    with pytest.raises(AttributeError):
        main.nope
