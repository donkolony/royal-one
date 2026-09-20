"""Advice records (AI drafts, the human commits), consents, the compliance pack, timelines and retention (brief section E)."""
import hashlib
import io
import json
import time
from datetime import date

import pytest
from pypdf import PdfReader

from app.llm.base import LLMRouter
from conftest import (ADVISER, ADVISER_2, CLIENT_1, CLIENT_2, CLIENT_3, CLIENT_5, CLIENT_8, CLIENT_9, OWNER, FakeProvider, audit_rows, claim_id)

NOTES = {"interaction_type": "review", "needs_goals": ["Protect the family", "Retire at 60"], "recommendation": "Raise life cover after the income review.",
         "products_considered": [{"product": "Life cover top-up", "category": "life", "provider": "Sanlam"}]}


def body(client, **over):
    return {"client_id": str(client), **NOTES, **over}


def commit(api, client=CLIENT_8, user=ADVISER, **over):
    d = api.post("/advice-records/draft", user=user, json=body(client)).json()["draft"]
    return api.post("/advice-records", user=user, json=body(client, final_summary=d["summary"], ai_draft=d["summary"], draft_source=d["source"], approved=True, **over))


# ============================================================================ advice: AI drafts, the human commits
def test_a_draft_stores_nothing_and_says_it_needs_review(fapi, fdb):
    before = fdb.execute("select count(*) as n from advice_records").fetchone()["n"]
    r = fapi.post("/advice-records/draft", user=ADVISER, json=body(CLIENT_8))
    assert r.status_code == 200 and r.json()["requires_human_review"] is True and r.json()["draft"]["source"] == "template"
    s = r.json()["draft"]["summary"]
    assert "Sarah van der Merwe" in s and "Zanele Mthembu" in s and "Protect the family" in s and "Life cover top-up" in s and "Raise life cover" in s
    assert fdb.execute("select count(*) as n from advice_records").fetchone()["n"] == before
    assert len(audit_rows(fdb, action="ai.advice_draft")) == 1


def test_an_ai_polished_draft_is_used_only_when_it_adds_no_figures(make_full_app):
    good = json.dumps({"summary": "Sarah met Zanele to review her needs. She wants to protect her family and retire at 60. Life cover was discussed and the recommendation is to raise it."})
    api = make_full_app(LLMRouter([FakeProvider(script=[good])]))
    assert api.post("/advice-records/draft", user=ADVISER, json=body(CLIENT_8)).json()["draft"]["source"] == "ai"
    bad = json.dumps({"summary": "Zanele was offered R5 000 000 of cover at R450 a month."})
    api2 = make_full_app(LLMRouter([FakeProvider(script=[bad])]))
    d = api2.post("/advice-records/draft", user=ADVISER, json=body(CLIENT_8)).json()
    assert d["draft"]["source"] == "template" and any("discarded" in w for w in d["warnings"])


def test_nothing_is_saved_without_the_advisers_explicit_approval(fapi, fdb):
    d = fapi.post("/advice-records/draft", user=ADVISER, json=body(CLIENT_8)).json()["draft"]
    unapproved = fapi.post("/advice-records", user=ADVISER, json=body(CLIENT_8, final_summary=d["summary"], ai_draft=d["summary"], draft_source="template"))
    assert unapproved.status_code == 422 and unapproved.json()["error"]["details"][0]["field"] == "approved"
    assert fapi.post("/advice-records", user=ADVISER, json=body(CLIENT_8, final_summary=d["summary"], approved=False)).status_code == 422
    assert fapi.post("/advice-records", user=ADVISER, json=body(CLIENT_8, final_summary="too short", approved=True)).status_code == 422
    assert fdb.execute("select count(*) as n from advice_records where client_id = %s", (CLIENT_8,)).fetchone()["n"] == 0


def test_the_committed_record_keeps_the_draft_the_final_text_and_whether_it_was_edited(fapi):
    r = commit(fapi)
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["edited_from_draft"] is False and a["draft_source"] == "template" and a["approved_by"] == str(ADVISER) and a["approved_at"] and a["client_acknowledged"] is False
    d = fapi.post("/advice-records/draft", user=ADVISER, json=body(CLIENT_8)).json()["draft"]["summary"]
    edited = fapi.post("/advice-records", user=ADVISER, json=body(CLIENT_8, final_summary=d + " Client asked for a call in March.", ai_draft=d, draft_source="template", approved=True)).json()
    assert edited["edited_from_draft"] is True and edited["ai_draft"] == d and "March" in edited["final_summary"]


def test_a_review_updates_the_review_date_and_logs_the_reuse_of_the_verified_id(fapi, fdb):
    assert commit(fapi, CLIENT_1).status_code == 201
    assert fapi.get(f"/clients/{CLIENT_1}", user=ADVISER).json()["last_annual_review_date"] == date.today().isoformat()
    assert fapi.get("/identity", user=CLIENT_1).json()["reuse_log"][0]["used_for"] == "review"
    assert audit_rows(fdb, action="advice.recorded", client_id=CLIENT_1)[-1]["details"]["interaction_type"] == "review"


def test_an_unacknowledged_record_asks_the_client_and_they_can_acknowledge_it(fapi):
    a = commit(fapi).json()
    assert fapi.get("/notifications", user=CLIENT_8).json()["items"][0]["title"] == "Please confirm your adviser's meeting summary"
    assert fapi.post(f"/advice-records/{a['id']}/acknowledge", user=CLIENT_2, json={}).status_code == 404
    r = fapi.post(f"/advice-records/{a['id']}/acknowledge", user=CLIENT_8, json={})
    assert r.status_code == 200 and r.json()["client_acknowledged"] is True and r.json()["acknowledgement_method"] == "in_app"
    assert fapi.post(f"/advice-records/{a['id']}/acknowledge", user=CLIENT_8, json={}).status_code == 409


def test_acknowledgement_rules(fapi):
    a = commit(fapi).json()
    assert fapi.post(f"/advice-records/{a['id']}/acknowledge", user=OWNER, json={}).status_code == 403
    assert fapi.post(f"/advice-records/{a['id']}/acknowledge", user=ADVISER_2, json={}).status_code == 404
    assert fapi.post(f"/advice-records/{a['id']}/acknowledge", user=ADVISER, json={"method": "verbal"}).json()["acknowledgement_method"] == "verbal"
    assert commit(fapi, CLIENT_8, client_acknowledged=True).status_code == 422, "an acknowledgement needs a method"
    assert commit(fapi, CLIENT_8, client_acknowledged=True, acknowledgement_method="in_meeting").json()["client_acknowledged"] is True


def test_advice_is_adviser_only_and_scoped(fapi):
    assert fapi.post("/advice-records/draft", user=OWNER, json=body(CLIENT_8)).status_code == 403
    assert fapi.post("/advice-records/draft", user=CLIENT_8, json=body(CLIENT_8)).status_code == 403
    assert fapi.post("/advice-records/draft", user=ADVISER_2, json=body(CLIENT_8)).status_code == 404
    commit(fapi)
    assert len(fapi.get(f"/advice-records?client_id={CLIENT_8}", user=ADVISER).json()["items"]) == 1
    assert len(fapi.get("/advice-records", user=CLIENT_8).json()["items"]) == 1
    assert fapi.get(f"/advice-records?client_id={CLIENT_8}", user=ADVISER_2).status_code == 404


# ================================================================================================== consents
def test_a_client_grants_and_withdraws_their_own_consent(fapi):
    c = fapi.get("/consents", user=CLIENT_8).json()
    assert c["notice_is_draft"] is True and c["current"]["data_processing"] is None
    r = fapi.post("/consents", user=CLIENT_8, json={"purpose": "data_processing", "status": "granted", "method": "in_app"})
    assert r.status_code == 200 and r.json()["current"]["data_processing"]["status"] == "granted" and r.json()["current"]["data_processing"]["notice_version"] == "v1-demo-draft"
    fapi.post("/consents", user=CLIENT_8, json={"purpose": "data_processing", "status": "withdrawn", "method": "in_app"})
    assert fapi.get("/consents", user=CLIENT_8).json()["current"]["data_processing"]["status"] == "withdrawn"
    assert len(fapi.get("/consents", user=CLIENT_8).json()["history"]) == 2, "append-only history"
    assert any("withdrew a consent" in i["title"] for i in fapi.get("/notifications", user=ADVISER).json()["items"])


def test_consent_method_must_match_who_is_recording_it(fapi):
    ok = {"purpose": "marketing", "status": "granted"}
    assert fapi.post("/consents", user=CLIENT_8, json={**ok, "method": "in_person"}).status_code == 422
    assert fapi.post("/consents", user=ADVISER, json={**ok, "method": "in_app", "client_id": str(CLIENT_8)}).status_code == 422
    assert fapi.post("/consents", user=ADVISER, json={**ok, "method": "in_person"}).status_code == 422, "client_id needed"
    assert fapi.post("/consents", user=ADVISER, json={**ok, "method": "in_person", "client_id": str(CLIENT_8)}).status_code == 200
    assert fapi.post("/consents", user=ADVISER_2, json={**ok, "method": "written", "client_id": str(CLIENT_8)}).status_code == 404
    assert fapi.post("/consents", user=OWNER, json={**ok, "method": "written", "client_id": str(CLIENT_8)}).status_code == 403


def test_recording_the_three_records_closes_the_compliance_gaps(fapi):
    def gaps():
        return {g["kind"] for g in fapi.get("/owner/drilldown?metric=compliance.gaps&limit=100", user=OWNER).json()["items"] if g["client"]["id"] == str(CLIENT_8)}
    assert gaps() == {"identity", "advice", "consent"}
    d = fapi.post("/identity", user=CLIENT_8, data={"doc_type": "id_document", "expiry_date": "2040-01-01"}, files={"file": ("id.png", __import__("conftest").png_bytes(), "image/png")}).json()
    fapi.post(f"/identity/{d['id']}/verify", user=ADVISER, json={})
    fapi.post("/consents", user=CLIENT_8, json={"purpose": "data_processing", "status": "granted", "method": "in_app"})
    assert commit(fapi, CLIENT_8, client_acknowledged=True, acknowledgement_method="in_meeting").status_code == 201
    assert gaps() == set()


# ================================================================================================ the pack
def pack(api, client, user=ADVISER):
    r = api.get(f"/clients/{client}/compliance", user=user)
    assert r.status_code == 200, r.text
    return r.json()


def test_the_pack_covers_identity_advice_consent_claims_and_access_history_in_seconds(fapi):
    started = time.monotonic()
    p = pack(fapi, CLIENT_1, OWNER)
    assert time.monotonic() - started < 10 and p["generation_ms"] < 10_000
    assert p["client"]["full_name"] == "Thabo Mokoena" and p["reference"].startswith("PACK-") and p["generated_by"]["role"] == "owner"
    assert p["compliance_status"]["identity"]["state"] == "valid" and p["compliance_status"]["consent"]["state"] == "current"
    assert {d["doc_type"] for d in p["identity"]["documents"]} == {"id_document", "drivers_licence"}
    assert p["advice_records"] and p["consents"]["history"] and p["policies"] and p["claims"] and p["requests"]
    assert any(c["events"] for c in p["claims"]) and all("timestamp" not in e for c in p["claims"] for e in c["events"])
    assert p["access_history"] and all({"occurred_at", "actor", "action", "summary"} <= set(e) for e in p["access_history"])
    assert p["integrity"]["audit_chain_ok"] is True and p["integrity"]["audit_entries_checked"] > 0
    assert set(p["sections"]) >= {"identity", "consents", "advice_records", "claims", "access_history"}


def test_the_pack_is_timestamped_and_carries_a_hash_of_its_content(fapi):
    p = pack(fapi, CLIENT_1)
    body = {k: p[k] for k in ("client", "compliance_status", "identity", "consents", "advice_records", "policies", "documents", "claims", "requests")}
    assert p["content_sha256"] == hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert p["reference"].endswith(p["content_sha256"][:8].upper()) and p["generated_at"].endswith("Z")
    assert pack(fapi, CLIENT_1)["content_sha256"] == p["content_sha256"], "same data, same hash"


def test_the_pack_leaves_out_what_a_regulator_does_not_need(fapi):
    fapi.post("/requests", user=CLIENT_1, json={"type": "bank_details_change", "payload": {"account_holder": "T Mokoena", "bank_name": "Demo Bank", "account_type": "savings",
                                                                                       "account_number": "1234567890", "branch_code": "123456"}})
    text = fapi.get(f"/clients/{CLIENT_1}/compliance", user=ADVISER).text
    for secret in ("1234567890", '"annual_income_cents"', '"dependants":', "storage_path", "identity/", "signed", "https://", "memory://"):
        assert secret not in text, secret
    assert "excluded_for_data_minimisation" in text


def test_the_pdf_is_a_real_pdf_with_the_content_in_it(fapi, fdb):
    r = fapi.get(f"/clients/{CLIENT_1}/compliance/pack.pdf", user=ADVISER)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF")
    assert "PACK-" in r.headers["content-disposition"] and len(r.content) > 3000
    text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(r.content)).pages)
    for needle in ("Compliance pack", "Thabo Mokoena", "Identity documents", "Advice records", "Access history", "Content SHA-256", "verification is simulated"):
        assert needle in text, needle
    assert audit_rows(fdb, action="compliance.pack_exported")[-1]["details"]["format"] == "pdf"


def test_every_pack_is_audited_with_its_reference_and_hash(fapi, fdb):
    p = pack(fapi, CLIENT_5, OWNER)
    (row,) = audit_rows(fdb, action="compliance.pack_exported", client_id=CLIENT_5)
    assert row["details"]["reference"] == p["reference"] and row["details"]["content_sha256"] == p["content_sha256"] and row["actor_role"] == "owner"


def test_the_pack_says_when_the_audit_trail_has_been_tampered_with(fapi, fdb):
    target = audit_rows(fdb)[3]["id"]
    fdb.execute("alter table audit_log disable trigger audit_log_no_change")
    try:
        fdb.execute("update audit_log set summary = 'rewritten' where id = %s", (target,))
        fdb.commit()
        assert pack(fapi, CLIENT_1)["integrity"]["audit_chain_ok"] is False
    finally:
        fdb.execute("alter table audit_log enable trigger audit_log_no_change")
        fdb.commit()


def test_the_pack_respects_scope_and_role(fapi, fdb):
    assert fapi.get(f"/clients/{CLIENT_1}/compliance", user=ADVISER_2).status_code == 404
    assert fapi.get(f"/clients/{CLIENT_1}/compliance/pack.pdf", user=ADVISER_2).status_code == 404
    assert fapi.get(f"/clients/{CLIENT_1}/compliance", user=CLIENT_1).status_code == 403
    assert fapi.get(f"/clients/{CLIENT_1}/compliance").status_code == 401
    assert audit_rows(fdb, action="access.denied", actor_id=ADVISER_2)


# ============================================================================================== timelines
def test_the_staff_timeline_shows_the_history_without_who_looked_noise(fapi):
    fapi.get(f"/clients/{CLIENT_1}", user=ADVISER)
    t = fapi.get(f"/clients/{CLIENT_1}/timeline", user=ADVISER).json()["items"]
    actions = {i["action"] for i in t}
    assert {"claim.submitted", "advice.recorded", "identity.verified", "consent.changed"} <= actions
    assert not any(a.endswith(".viewed") or a.startswith(("opportunity.", "ai.")) or a == "access.denied" for a in actions)
    ids = [i["id"] for i in t]
    assert ids == sorted(ids, reverse=True)


def test_a_clients_own_timeline_is_client_safe(fapi):
    fapi.patch(f"/claims/{claim_id('submitted')}/insurer-details", user=ADVISER, json={"claim_number": "SC-1"})
    fapi.post(f"/claims/{claim_id('submitted')}/updates", user=ADVISER, json={"type": "note", "message": "Internal note", "visible_to_client": False})
    fapi.get(f"/opportunities?client_id={CLIENT_1}", user=ADVISER)
    t = fapi.get("/me/timeline", user=CLIENT_1).json()["items"]
    actions = {i["action"] for i in t}
    assert actions and all(a.startswith(("claim.", "request.", "document.", "identity.", "consent.", "advice.", "goal.", "reminder.completed", "life_event.")) for a in actions)
    assert "claim.note_added" not in actions and not any("Internal note" in i["summary"] for i in t)
    assert fapi.get("/me/timeline", user=ADVISER).status_code == 403
    assert fapi.get(f"/clients/{CLIENT_1}/timeline", user=ADVISER_2).status_code == 404


# ======================================================================== overview and the retention review
def test_the_overview_lists_only_the_callers_clients(fapi):
    mine = fapi.get("/compliance/overview", user=ADVISER).json()
    assert len(mine["clients"]) == 9 and mine["summary"]["clients"] == 9 and mine["summary"]["gaps"]
    assert {c["adviser"] for c in mine["clients"]} == {"Sarah van der Merwe"}
    allc = fapi.get("/compliance/overview", user=OWNER).json()
    assert len(allc["clients"]) == 12 and allc["summary"]["score_percent"] == round((8 + 6 + 9) * 100 / 36, 1)
    assert fapi.get("/compliance/overview", user=CLIENT_1).status_code == 403


def test_retention_flags_old_records_and_deletes_nothing(fapi, fdb):
    r = fapi.get("/compliance/retention", user=OWNER).json()
    assert r["retention_years"] == 5 and r["action"] == "flag_only" and r["total"] == 2
    assert {i["kind"] for i in r["items"]} == {"closed_request", "identity_document"} and all(i["client"]["full_name"] == "Johan Smit" for i in r["items"])
    assert "placeholder" in r["note"].lower() and "Nothing is deleted" in r["note"]
    assert fdb.execute("select count(*) as n from requests where client_id = %s and status = 'completed'", (CLIENT_3,)).fetchone()["n"] >= 1
    assert fapi.get("/compliance/retention", user=ADVISER).status_code == 403


def test_the_retention_period_is_configuration_not_code(settings, full_db, storage):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from conftest import Api
    api = Api(TestClient(create_app(settings.model_copy(update={"retention_years": 10}), pool=full_db, storage=storage, llm=LLMRouter([])), raise_server_exceptions=False))
    assert api.get("/compliance/retention", user=OWNER).json()["total"] == 0
    assert api.get("/meta").json()["retention_years"] == 10
