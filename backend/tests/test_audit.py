"""The audit trail: what is recorded, who can read it, and whether tampering shows (docs/AUDIT.md build step 1)."""
import csv
import io

import psycopg
import pytest

from app.services import audit
from tests.conftest import ADVISER, ADVISER_2, CLIENT_1, CLIENT_2, CLIENT_3, OWNER, audit_rows, claim_id


def _register(api, cid="submitted"):
    api.patch(f"/claims/{claim_id(cid)}/insurer-details", user=ADVISER, json={"claim_number": "SC-900001"})
    return api.post(f"/claims/{claim_id(cid)}/transitions", user=ADVISER, json={"to_status": "registered"})


# ---------------------------------------------------------------------------------------------- what is recorded
def test_a_claim_transition_is_recorded_with_actor_role_client_and_context(api, db):
    assert _register(api).status_code == 200
    (row,) = audit_rows(db, action="claim.status_changed")
    assert row["actor_id"] == ADVISER and row["actor_role"] == "advisor" and row["client_id"] == CLIENT_1
    assert row["entity_type"] == "claim" and row["details"]["from"] == "submitted" and row["details"]["to"] == "registered"
    assert row["request_id"] and row["ip"] and row["hash"] and row["occurred_at"] is not None


def test_client_actions_are_recorded_against_the_client(api, db):
    r = api.post("/claims", user=CLIENT_1, json={})
    assert r.status_code == 201
    (row,) = audit_rows(db, action="claim.created")
    assert row["actor_role"] == "client" and row["client_id"] == CLIENT_1


def test_no_entry_holds_document_text_or_bank_numbers(api, db):
    api.get(f"/requests?client_id={CLIENT_1}", user=ADVISER)
    for r in audit_rows(db):
        assert "1234567890" not in r["summary"] and "1234567890" not in str(r["details"])


def test_an_upload_is_recorded_without_its_content(api, db):
    from tests.conftest import png_bytes
    d = api.post("/claims", user=CLIENT_1, json={}).json()
    r = api.post(f"/claims/{d['id']}/attachments", user=CLIENT_1, data={"kind": "vehicle_photo"},
                 files={"file": ("bumper.png", png_bytes(), "image/png")})
    assert r.status_code == 201
    (row,) = audit_rows(db, action="document.uploaded")
    assert row["details"]["kind"] == "vehicle_photo" and row["details"]["size_bytes"] == len(png_bytes())


def test_the_assistant_query_is_logged_without_the_question_text(api, db):
    r = api.post("/assistant/query", user=ADVISER, json={"question": "What is the notification period for a motor claim?"})
    assert r.status_code == 200
    (row,) = audit_rows(db, action="assistant.query")
    assert row["actor_id"] == ADVISER and "question_chars" in row["details"] and "notification period" not in str(row["details"])
    assert "sources" in row["details"]


def test_staff_views_are_logged_once_per_window_not_on_every_poll(api, db):
    for _ in range(3):
        assert api.get(f"/claims/{claim_id('submitted')}", user=ADVISER).status_code == 200
    assert len(audit_rows(db, action="claim.viewed")) == 1
    api.get(f"/claims/{claim_id('assessment')}", user=ADVISER)
    assert len(audit_rows(db, action="claim.viewed")) == 2


def test_a_client_opening_their_own_claim_is_not_logged(api, db):
    api.get(f"/claims/{claim_id('submitted')}", user=CLIENT_1)
    assert audit_rows(db, action="claim.viewed") == []


# --------------------------------------------------------------------------------------------- denied attempts
def test_opening_another_advisers_client_by_id_is_refused_and_logged(api, db):
    r = api.get(f"/clients/{CLIENT_1}", user=ADVISER_2)
    assert r.status_code == 404
    (row,) = audit_rows(db, action="access.denied")
    assert row["actor_id"] == ADVISER_2 and row["client_id"] == CLIENT_1 and row["entity_type"] == "client"


def test_opening_another_advisers_claim_is_refused_and_logged(api, db):
    assert api.get(f"/claims/{claim_id('submitted')}", user=ADVISER_2).status_code == 404
    (row,) = audit_rows(db, action="access.denied")
    assert row["entity_type"] == "claim" and row["client_id"] == CLIENT_1


def test_a_guessed_id_that_does_not_exist_is_a_plain_404_with_no_entry(api, db):
    assert api.get("/clients/00000000-0000-4000-8000-000000000000", user=ADVISER).status_code == 404
    assert audit_rows(db, action="access.denied") == []


def test_the_denied_entry_survives_although_the_request_rolled_back(api, db):
    api.get(f"/clients/{CLIENT_2}", user=ADVISER_2)
    assert len(audit_rows(db, action="access.denied")) == 1


# ------------------------------------------------------------------------------------------------ append-only
def test_the_log_refuses_update_delete_and_truncate(api, db):
    _register(api)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute("update audit_log set summary = 'edited'")
    db.rollback()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute("delete from audit_log")
    db.rollback()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute("truncate audit_log")
    db.rollback()


# -------------------------------------------------------------------------------------------------- hash chain
def test_the_chain_verifies_after_normal_use(api):
    _register(api)
    api.get(f"/clients/{CLIENT_1}", user=ADVISER)
    v = api.get("/audit/verify", user=OWNER).json()
    assert v["ok"] is True and v["checked"] >= 3 and v["first_bad_id"] is None


def test_an_edited_row_is_detected_even_if_the_triggers_are_bypassed(api, db):
    _register(api)
    api.get(f"/clients/{CLIENT_1}", user=ADVISER)
    target = audit_rows(db, action="claim.status_changed")[0]["id"]
    db.execute("alter table audit_log disable trigger audit_log_no_change")
    try:
        db.execute("update audit_log set summary = 'quietly rewritten' where id = %s", (target,))
        db.commit()
        v = api.get("/audit/verify", user=OWNER).json()
        assert v["ok"] is False and v["first_bad_id"] == target
    finally:
        db.execute("alter table audit_log enable trigger audit_log_no_change")
        db.commit()


def test_a_removed_row_breaks_the_chain(api, db):
    _register(api)
    api.get(f"/clients/{CLIENT_1}", user=ADVISER)
    rows = audit_rows(db)
    db.execute("alter table audit_log disable trigger audit_log_no_change")
    try:
        db.execute("delete from audit_log where id = %s", (rows[1]["id"],))
        db.commit()
        assert api.get("/audit/verify", user=OWNER).json()["ok"] is False
    finally:
        db.execute("alter table audit_log enable trigger audit_log_no_change")
        db.commit()


def test_hashes_are_deterministic_and_depend_on_the_previous_hash():
    from datetime import datetime, timezone
    e = dict(occurred_at=datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc), actor_id=None, actor_role="system", action="x.y",
             entity_type="x", entity_id=None, client_id=None, summary="s", details={"a": 1}, ip=None, user_agent=None, request_id=None)
    assert audit.compute_hash("", e) == audit.compute_hash("", dict(e))
    assert audit.compute_hash("", e) != audit.compute_hash("abc", e)
    assert audit.compute_hash("", e) != audit.compute_hash("", {**e, "summary": "t"})


def test_only_the_owner_can_verify(api):
    assert api.get("/audit/verify", user=ADVISER).status_code == 403
    assert api.get("/audit/verify", user=CLIENT_1).status_code == 403
    assert api.get("/audit/verify").status_code == 401


# ---------------------------------------------------------------------------------------- reading and filtering
def test_a_client_cannot_read_the_trail(api):
    assert api.get("/audit", user=CLIENT_1).status_code == 403
    assert api.get("/audit/export", user=CLIENT_1).status_code == 403


def test_an_adviser_sees_their_clients_and_own_actions_only(api):
    api.get(f"/clients/{CLIENT_1}", user=ADVISER)
    api.get(f"/clients/{CLIENT_1}", user=ADVISER_2)   # refused, logged against client 1, actor adviser 2
    mine = api.get("/audit?limit=100", user=ADVISER).json()["items"]
    assigned = {str(c) for c in (CLIENT_1, CLIENT_2, CLIENT_3)}
    assert mine and all((i["client"] and i["client"]["id"] in assigned) or i["actor"]["id"] == str(ADVISER) for i in mine)
    actors = {i["actor"]["id"] for i in mine}
    assert str(ADVISER_2) in actors, "a refused attempt against my client is visible to me"
    theirs = api.get("/audit?limit=100", user=ADVISER_2).json()["items"]
    assert all(i["actor"]["id"] == str(ADVISER_2) for i in theirs), "adviser 2 sees only what they did themselves"


def test_the_owner_sees_everything_and_can_filter(api):
    _register(api)
    api.get(f"/clients/{CLIENT_1}", user=ADVISER)
    everything = api.get("/audit?limit=100", user=OWNER).json()
    assert everything["total"] >= 3
    by_prefix = api.get("/audit?action=claim", user=OWNER).json()["items"]
    assert by_prefix and all(i["action"].startswith("claim.") for i in by_prefix)
    exact = api.get("/audit?action=claim.status_changed", user=OWNER).json()["items"]
    assert len(exact) == 1 and exact[0]["client"]["id"] == str(CLIENT_1)
    assert api.get(f"/audit?client_id={CLIENT_2}", user=OWNER).json()["total"] == 0
    assert api.get(f"/audit?actor_id={ADVISER}&entity_type=claim", user=OWNER).json()["total"] >= 1
    assert api.get("/audit?q=Moved+claim", user=OWNER).json()["total"] == 1
    assert api.get("/audit?date_from=2000-01-01&date_to=2000-01-02", user=OWNER).json()["total"] == 0
    assert api.get("/audit?date_from=nonsense", user=OWNER).status_code == 422


# ----------------------------------------------------------------------------------------------------- export
def test_the_csv_export_has_the_columns_and_is_itself_logged(api, db):
    _register(api)
    r = api.get("/audit/export?action=claim", user=OWNER)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0] == audit.CSV_COLUMNS and len(rows) >= 2
    assert len(audit_rows(db, action="audit.exported")) == 1


def test_the_csv_neutralises_spreadsheet_formulas(api, db):
    audit.record(db, None, "test.formula", "test", summary="=HYPERLINK(\"http://evil\")")
    db.commit()
    text = api.get("/audit/export?action=test.formula", user=OWNER).text
    assert "'=HYPERLINK" in text and "\n=HYPERLINK" not in text and ",=HYPERLINK" not in text
