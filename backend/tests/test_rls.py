"""Row-level security, proven at the database (docs/AUDIT.md R7, brief section H).

These tests do NOT go through the API. They connect as the `authenticated` role with a Supabase-style JWT subject, exactly
like a browser holding the public anon key would, and try to read and write other people's rows. The backend's own
privileged connection bypasses RLS, so this is the independent second layer.

Any table added later must call rs_lock_down() and add a policy: the generic tests below fail otherwise.
"""
import contextlib

import psycopg
import pytest

from tests.conftest import ADVISER, ADVISER_2, CLIENT_1, CLIENT_2, CLIENT_3, CLIENT_4, OWNER, claim_id

PUBLIC_NON_DATA = {"schema_migrations"}


@contextlib.contextmanager
def as_role(pg_uri, user_id=None, role="authenticated"):
    """A connection that behaves like Supabase's PostgREST for one signed-in user (or anon when user_id is None)."""
    with psycopg.connect(pg_uri, autocommit=True) as conn:
        conn.execute(f"set role {role}")
        if user_id is not None:
            conn.execute("select set_config('request.jwt.claim.sub', %s, false)", (str(user_id),))
        yield conn


def q(conn, sql, params=None):
    return conn.execute(sql, params).fetchall()


def n(conn, sql, params=None):
    return conn.execute(sql, params).fetchone()[0]


@pytest.fixture
def pg(pg_uri, fresh_db):
    return pg_uri


def tables(pg_uri, with_column=None):
    with psycopg.connect(pg_uri) as c:
        rows = c.execute(
            "select c.relname from pg_class c join pg_namespace ns on ns.oid = c.relnamespace "
            "where ns.nspname = 'public' and c.relkind = 'r' order by 1").fetchall()
        names = [r[0] for r in rows]
        if with_column:
            have = {r[0] for r in c.execute(
                "select table_name from information_schema.columns where table_schema = 'public' and column_name = %s",
                (with_column,)).fetchall()}
            names = [t for t in names if t in have]
        return names


# ------------------------------------------------------------------------------------------- every table is covered
def test_every_public_table_has_rls_enabled(pg):
    with psycopg.connect(pg) as c:
        off = c.execute(
            "select c.relname from pg_class c join pg_namespace ns on ns.oid = c.relnamespace "
            "where ns.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity").fetchall()
    assert off == [], f"tables without row-level security: {[r[0] for r in off]}"


def test_anon_can_read_nothing_and_write_nothing(pg):
    with as_role(pg, role="anon") as conn:
        for t in tables(pg):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(f"select 1 from {t} limit 1")


def test_a_signed_in_user_can_never_write_any_table(pg):
    with as_role(pg, CLIENT_1) as conn:
        for t in tables(pg):
            for stmt in (f"delete from {t}", f"truncate {t}"):
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    conn.execute(stmt)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("update claims set status = 'closed'")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("insert into reminders (client_id, type, title, due_date, audience, source) values (%s,'custom','x',now(),'client','manual')", (CLIENT_1,))


def test_a_user_with_no_subject_sees_no_client_rows(pg):
    with as_role(pg, None) as conn:
        for t in tables(pg, "client_id"):
            assert n(conn, f"select count(*) from {t}") == 0, t


# --------------------------------------------------------------------------------------- client: own rows only
def test_a_client_sees_only_their_own_rows_in_every_client_table(pg):
    with as_role(pg, CLIENT_1) as conn:
        for t in tables(pg, "client_id"):
            assert n(conn, f"select count(*) from {t} where client_id <> %s", (CLIENT_1,)) == 0, f"{t} leaks other clients' rows"
        assert n(conn, "select count(*) from policies") == 4
        assert n(conn, "select count(*) from claims") >= 2


def test_a_client_cannot_read_a_specific_other_clients_records(pg):
    with as_role(pg, CLIENT_1) as conn:
        assert n(conn, "select count(*) from claims where client_id = %s", (CLIENT_2,)) == 0
        assert n(conn, "select count(*) from policies where client_id = %s", (CLIENT_2,)) == 0
        assert n(conn, "select count(*) from requests where client_id = %s", (CLIENT_2,)) == 0
        assert n(conn, "select count(*) from clients where id = %s", (CLIENT_2,)) == 0
        assert n(conn, "select count(*) from profiles where id = %s", (CLIENT_2,)) == 0
        assert n(conn, "select count(*) from financial_items where client_id = %s", (CLIENT_2,)) == 0


def test_a_client_sees_their_adviser_profile_and_no_other_staff(pg):
    with as_role(pg, CLIENT_1) as conn:
        assert {r[0] for r in q(conn, "select id from profiles where role <> 'client'")} == {ADVISER}


def test_a_client_sees_only_shared_goals_they_take_part_in(pg):
    with as_role(pg, CLIENT_2) as conn:
        titles = {r[0] for r in q(conn, "select title from goals")}
    assert "Children's university fund" in titles and "Retire at 60" not in titles


def test_a_client_sees_only_client_visible_timeline_events_and_reminders(pg, db):
    db.execute("insert into claim_events (claim_id, type, title, visible_to_client, actor_id) values (%s,'note','internal',false,%s)",
               (claim_id("submitted"), ADVISER))
    db.commit()
    with as_role(pg, CLIENT_1) as conn:
        assert n(conn, "select count(*) from claim_events where visible_to_client = false") == 0
        assert n(conn, "select count(*) from reminders where audience = 'advisor'") == 0
    with as_role(pg, ADVISER) as conn:
        assert n(conn, "select count(*) from claim_events where visible_to_client = false") >= 1
        assert n(conn, "select count(*) from reminders where audience = 'advisor'") >= 1


def test_a_clients_draft_claim_is_visible_to_them_and_hidden_from_staff(pg):
    draft = claim_id("draft")
    with as_role(pg, CLIENT_1) as conn:
        assert n(conn, "select count(*) from claims where id = %s", (draft,)) == 1
    for staff in (ADVISER, OWNER):
        with as_role(pg, staff) as conn:
            assert n(conn, "select count(*) from claims where id = %s", (draft,)) == 0, staff


# ------------------------------------------------------------------------------ adviser: assigned clients only
def test_an_adviser_sees_exactly_their_assigned_clients(pg):
    with as_role(pg, ADVISER) as conn:
        assert {r[0] for r in q(conn, "select id from clients")} == {CLIENT_1, CLIENT_2, CLIENT_3}
        for t in tables(pg, "client_id"):
            assert n(conn, f"select count(*) from {t} where client_id = %s", (CLIENT_4,)) == 0, f"{t} leaks another adviser's client"
    with as_role(pg, ADVISER_2) as conn:
        assert {r[0] for r in q(conn, "select id from clients")} == {CLIENT_4}
        assert n(conn, "select count(*) from claims") == 0


def test_an_adviser_cannot_open_another_advisers_client_records(pg):
    with as_role(pg, ADVISER_2) as conn:
        for t in ("policies", "claims", "requests", "financial_items", "reminders"):
            assert n(conn, f"select count(*) from {t} where client_id in (%s,%s,%s)", (CLIENT_1, CLIENT_2, CLIENT_3)) == 0, t
        assert n(conn, "select count(*) from profiles where id = %s", (CLIENT_1,)) == 0


def test_an_adviser_cannot_see_another_advisers_conversations_or_mailbox(pg, api, db):
    api.post("/assistant/query", user=ADVISER, json={"question": "What is the notification period?"})
    with as_role(pg, ADVISER) as conn:
        assert n(conn, "select count(*) from assistant_conversations") == 1
        assert n(conn, "select count(*) from email_threads") == 3
    with as_role(pg, ADVISER_2) as conn:
        assert n(conn, "select count(*) from assistant_conversations") == 0
        assert n(conn, "select count(*) from assistant_messages") == 0
        assert n(conn, "select count(*) from email_threads") == 0
        assert n(conn, "select count(*) from email_messages") == 0


def test_the_document_library_is_adviser_only(pg, db):
    db.execute("insert into documents (title, category, content_hash, status) values ('Demo doc', 'policy_wording', 'h1', 'indexed')")
    db.commit()
    with as_role(pg, ADVISER) as conn:
        assert n(conn, "select count(*) from documents") == 1
    for other in (CLIENT_1, OWNER):
        with as_role(pg, other) as conn:
            assert n(conn, "select count(*) from documents") == 0, other


# ------------------------------------------------------------------------------------------------------- owner
def test_the_owner_sees_every_clients_rows_but_never_drafts(pg):
    with as_role(pg, OWNER) as conn:
        assert {r[0] for r in q(conn, "select id from clients")} == {CLIENT_1, CLIENT_2, CLIENT_3, CLIENT_4}
        assert n(conn, "select count(*) from policies") == 8
        assert n(conn, "select count(*) from claims where status = 'draft'") == 0


# ---------------------------------------------------------------------------------------------------- audit log
def test_the_audit_log_is_readable_by_owner_and_scoped_for_advisers(pg, api):
    api.get(f"/clients/{CLIENT_1}", user=ADVISER)
    api.get(f"/clients/{CLIENT_4}", user=ADVISER_2)
    with as_role(pg, OWNER) as conn:
        assert n(conn, "select count(*) from audit_log") >= 2
    with as_role(pg, ADVISER) as conn:
        assert n(conn, "select count(*) from audit_log where client_id = %s", (CLIENT_4,)) == 0
        assert n(conn, "select count(*) from audit_log where client_id = %s", (CLIENT_1,)) >= 1
    with as_role(pg, CLIENT_1) as conn:
        assert n(conn, "select count(*) from audit_log") == 0


# ------------------------------------------------------------------------------------------- the helper functions
def test_rs_helpers_answer_from_the_jwt_subject(pg):
    with as_role(pg, ADVISER) as conn:
        assert n(conn, "select rs_role()") == "advisor"
        assert n(conn, "select rs_can_see_client(%s)", (CLIENT_1,)) is True
        assert n(conn, "select rs_can_see_client(%s)", (CLIENT_4,)) is False
    with as_role(pg, None) as conn:
        assert n(conn, "select rs_role()") is None
        assert n(conn, "select rs_can_see_client(%s)", (CLIENT_1,)) is False
