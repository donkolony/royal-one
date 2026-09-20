"""The identity vault: capture once, verify (simulated), reuse instead of asking again, expire loudly (brief section D)."""
from datetime import date, timedelta

import pytest

from app import seed
from conftest import (ADVISER, ADVISER_2, CLIENT_1, CLIENT_2, CLIENT_3, CLIENT_5, CLIENT_8, CLIENT_11, CLIENT_12, OWNER, audit_rows, png_bytes)


def upload(api, user, doc_type="id_document", expiry=None, client_id=None, data=None, ctype="image/png"):
    form = {"doc_type": doc_type, **({"expiry_date": expiry} if expiry else {}), **({"client_id": str(client_id)} if client_id else {})}
    return api.post("/identity", user=user, data=form, files={"file": ("doc.png", data if data is not None else png_bytes(), ctype)})


def vault(api, user, client_id=None):
    return api.get("/identity" + (f"?client_id={client_id}" if client_id else ""), user=user).json()


def summary(api, client, user=None):
    return vault(api, user or client, client if user else None)["summary"]


# ============================================================================================= capture once
def test_a_client_uploads_a_document_and_it_waits_for_verification(fapi, fdb):
    r = upload(fapi, CLIENT_8, "id_document", "2035-01-01")
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["status"] == "pending" and d["verification_source"] == "uploaded" and d["verified_by"] is None and d["is_simulated_verification"] is False
    assert summary(fapi, CLIENT_8)["id_document"]["state"] == "pending"
    assert any(i["kind"] == "identity" and "added a ID document" in i["title"] for i in fapi.get("/notifications", user=ADVISER).json()["items"])
    (row,) = audit_rows(fdb, action="identity.uploaded", client_id=CLIENT_8)
    assert row["details"]["doc_type"] == "id_document" and "doc.png" not in str(row["details"])


def test_the_adviser_verifies_it_and_the_metadata_says_it_was_simulated(fapi, fdb):
    d = upload(fapi, CLIENT_8, "id_document", "2035-01-01").json()
    r = fapi.post(f"/identity/{d['id']}/verify", user=ADVISER, json={"issued_date": "2025-01-01"})
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["status"] == "verified" and v["verification_source"] == "simulated_verification" and v["verifier"] == "demo_simulated"
    assert v["verified_by"]["full_name"] == "Sarah van der Merwe" and v["verified_at"] and v["expiry_date"] == "2035-01-01" and v["issued_date"] == "2025-01-01"
    assert summary(fapi, CLIENT_8)["id_document"]["state"] == "valid"
    assert fapi.get("/notifications", user=CLIENT_8).json()["items"][0]["title"] == "Your ID document was verified"
    assert audit_rows(fdb, action="identity.verified", client_id=CLIENT_8)[0]["details"]["simulated"] is True
    assert fapi.post(f"/identity/{d['id']}/verify", user=ADVISER, json={}).status_code == 409


def test_the_vault_says_plainly_that_verification_is_a_demo(fapi):
    v = vault(fapi, CLIENT_1)
    assert v["verifier"]["is_simulated"] is True and "Demo" in v["verifier"]["note"] and "KYC" not in v["verifier"]["note"].replace("real", "")


def test_the_demo_verifier_refuses_a_document_whose_expiry_has_passed(fapi):
    d = upload(fapi, CLIENT_8, "id_document", (date.today() - timedelta(days=1)).isoformat()).json()
    r = fapi.post(f"/identity/{d['id']}/verify", user=ADVISER, json={})
    assert r.status_code == 200 and r.json()["status"] == "rejected" and "expiry" in r.json()["rejected_reason"]


def test_a_newer_verified_document_supersedes_the_old_one(fapi):
    old = [d for d in vault(fapi, CLIENT_1)["documents"] if d["doc_type"] == "id_document"][0]
    new = upload(fapi, CLIENT_1, "id_document", "2040-06-01").json()
    fapi.post(f"/identity/{new['id']}/verify", user=ADVISER, json={})
    docs = {d["id"]: d["status"] for d in vault(fapi, CLIENT_1)["documents"]}
    assert docs[old["id"]] == "superseded" and docs[new["id"]] == "verified"


def test_verifying_a_licence_keeps_the_single_licence_date_in_step(fapi):
    d = upload(fapi, CLIENT_8, "drivers_licence", "2031-05-05").json()
    fapi.post(f"/identity/{d['id']}/verify", user=ADVISER, json={})
    assert fapi.get(f"/clients/{CLIENT_8}", user=ADVISER).json()["drivers_licence_expiry"] == "2031-05-05"


def test_only_the_advisers_verify_and_reject(fapi):
    d = upload(fapi, CLIENT_8, "id_document").json()
    assert fapi.post(f"/identity/{d['id']}/verify", user=CLIENT_8, json={}).status_code == 403
    assert fapi.post(f"/identity/{d['id']}/verify", user=OWNER, json={}).status_code == 403
    assert fapi.post(f"/identity/{d['id']}/verify", user=ADVISER_2, json={}).status_code == 404
    assert fapi.post(f"/identity/{d['id']}/reject", user=ADVISER, json={"reason": "x"}).status_code == 422
    r = fapi.post(f"/identity/{d['id']}/reject", user=ADVISER, json={"reason": "The photo is blurred"})
    assert r.json()["status"] == "rejected" and r.json()["rejected_reason"] == "The photo is blurred"


def test_uploads_are_validated_by_content_not_by_name(fapi):
    assert upload(fapi, CLIENT_8, "id_document", data=b"not an image at all", ctype="image/png").status_code == 415
    assert upload(fapi, CLIENT_8, "id_document", data=png_bytes(), ctype="application/pdf").status_code == 415
    assert upload(fapi, CLIENT_8, "passport").status_code == 422
    assert upload(fapi, CLIENT_8, "id_document", data=b"").status_code == 422


def test_an_adviser_can_add_a_document_for_their_own_client_only(fapi):
    assert upload(fapi, ADVISER, "id_document", client_id=CLIENT_8).status_code == 201
    assert upload(fapi, ADVISER, "id_document").status_code == 422
    assert upload(fapi, ADVISER_2, "id_document", client_id=CLIENT_8).status_code == 404
    assert upload(fapi, OWNER, "id_document", client_id=CLIENT_8).status_code == 403


# ======================================================================================= reuse: not asked again
def test_a_verified_client_starts_a_claim_and_is_not_asked_for_a_licence_again(fapi, fdb, storage):
    r = fapi.post("/claims", user=CLIENT_1, json={})
    assert r.status_code == 201
    c = r.json()
    assert "attachments.drivers_licence" not in c["missing_fields"], "the licence is already on file"
    lic = [a for a in c["attachments"] if a["kind"] == "drivers_licence"]
    assert len(lic) == 1 and "identity vault" in lic[0]["label"]
    assert c["identity"]["drivers_licence"]["reused"] is True and c["identity"]["drivers_licence"]["state"] == "valid"
    assert c["timeline"][-1]["title"] == "Driver's licence taken from your verified documents"
    log = vault(fapi, CLIENT_1)["reuse_log"]
    assert log[0]["used_for"] == "claim" and log[0]["used_for_id"] == c["id"] and log[0]["label"] == "driver's licence"
    (row,) = audit_rows(fdb, action="identity.reused", client_id=CLIENT_1)
    assert row["details"]["used_for"] == "claim" and "reused the verified driver's licence" in row["summary"].lower()
    assert [d for d in vault(fapi, CLIENT_1)["documents"] if d["doc_type"] == "drivers_licence"][0]["reuse_count"] == 1


def test_the_reused_licence_is_the_same_private_object_and_survives_removing_it_from_the_draft(fapi, storage):
    c = fapi.post("/claims", user=CLIENT_1, json={}).json()
    att = [a for a in c["attachments"] if a["kind"] == "drivers_licence"][0]
    doc = [d for d in vault(fapi, CLIENT_1)["documents"] if d["doc_type"] == "drivers_licence"][0]
    path = f"identity/{CLIENT_1}/{seed.uid(f'idoc-{CLIENT_1}-drivers_licence')}-drivers_licence.png"
    assert ("attachments", path) in storage.files
    assert fapi.delete(f"/claims/{c['id']}/attachments/{att['id']}", user=CLIENT_1).status_code == 204
    assert ("attachments", path) in storage.files, "deleting a claim attachment must never delete the vault file"
    assert doc["status"] == "verified"


def test_a_claim_can_be_completed_and_submitted_without_ever_uploading_a_licence(fapi):
    from test_claims import COMPLETE_PATCH, upload as claim_upload
    c = fapi.post("/claims", user=CLIENT_1, json={}).json()
    iid = fapi.get("/insurers", user=CLIENT_1).json()["items"][0]["id"]
    assert fapi.patch(f"/claims/{c['id']}", user=CLIENT_1, json={**COMPLETE_PATCH, "insurer_id": iid}).status_code == 200
    assert claim_upload(fapi, CLIENT_1, c["id"], "vehicle_photo").status_code == 201
    r = fapi.post(f"/claims/{c['id']}/submit", user=CLIENT_1)
    assert r.status_code == 200 and r.json()["status"] == "submitted"


def test_an_expired_licence_is_not_reused_and_the_client_is_asked_again(fapi):
    c = fapi.post("/claims", user=CLIENT_3, json={}).json()
    assert "attachments.drivers_licence" in c["missing_fields"]
    assert c["identity"]["drivers_licence"] == {"reused": False, "state": "expired", **{k: c["identity"]["drivers_licence"][k] for k in ("document_id", "expiry_date", "verified_at")}}


def test_a_client_with_nothing_on_file_is_asked_as_before(fapi):
    c = fapi.post("/claims", user=CLIENT_8, json={}).json()
    assert "attachments.drivers_licence" in c["missing_fields"] and c["identity"]["drivers_licence"]["state"] == "missing"


def test_a_request_that_needs_identity_reuses_the_verified_id(fapi):
    r = fapi.post("/requests", user=CLIENT_1, json={"type": "bank_details_change", "payload": {
        "account_holder": "Thabo Mokoena", "bank_name": "Demo Bank", "account_type": "savings", "account_number": "1234567890", "branch_code": "123456"}})
    assert r.status_code == 201
    ev = [e["type"] for e in r.json()["timeline"]]
    assert "identity_reused" in ev and "identity_needed" not in ev
    assert vault(fapi, CLIENT_1)["reuse_log"][0]["used_for"] == "request"


def test_a_request_without_a_valid_id_says_one_is_needed_instead_of_silently_proceeding(fapi):
    r = fapi.post("/requests", user=CLIENT_11, json={"type": "bank_details_change", "payload": {
        "account_holder": "Ruan Pretorius", "bank_name": "Demo Bank", "account_type": "cheque", "account_number": "9876543210", "branch_code": "654321"}})
    assert r.status_code == 201
    assert "identity_needed" in [e["type"] for e in r.json()["timeline"]]
    assert any(i["kind"] == "identity" and "verified ID" in i["title"] for i in fapi.get("/notifications", user=CLIENT_11).json()["items"])


def test_a_fresh_proof_of_address_is_reused_for_an_address_change_and_a_stale_one_is_not(fapi, fdb):
    payload = {"address_line_1": "1 Test Street", "suburb": "Gardens", "city": "Cape Town", "postal_code": "8001"}
    d = upload(fapi, CLIENT_2, "proof_of_address").json()
    fapi.post(f"/identity/{d['id']}/verify", user=ADVISER, json={})
    fresh = fapi.post("/requests", user=CLIENT_2, json={"type": "address_change", "payload": payload}).json()
    assert "identity_reused" in [e["type"] for e in fresh["timeline"]]
    fdb.execute("update identity_documents set verified_at = now() - interval '100 days' where id = %s", (d["id"],))
    fdb.commit()
    assert summary(fapi, CLIENT_2)["proof_of_address"]["state"] == "stale"
    stale = fapi.post("/requests", user=CLIENT_2, json={"type": "address_change", "payload": payload}).json()
    assert "identity_reused" not in [e["type"] for e in stale["timeline"]]


# ================================================================================== expiry is loud, not silent
def test_an_id_expiring_in_thirty_days_makes_a_reminder_a_compliance_flag_and_a_touchpoint(fapi):
    rem = fapi.get(f"/reminders?client_id={CLIENT_5}&type=identity_expiry", user=ADVISER).json()["items"]
    assert len(rem) == 1 and rem[0]["audience"] == "both" and "ID document expires" in rem[0]["title"] and rem[0]["urgency"] == "upcoming"
    assert any(r["type"] == "identity_expiry" for r in fapi.get("/reminders?limit=100", user=CLIENT_5).json()["items"]), "the client sees it too"
    assert summary(fapi, CLIENT_5)["id_document"]["state"] == "expiring"
    gaps = fapi.get("/owner/drilldown?metric=compliance.gaps&limit=100", user=OWNER).json()["items"]
    assert any(g["client"]["id"] == str(CLIENT_5) and g["kind"] == "identity" and g["severity"] == "medium" for g in gaps)
    touch = fapi.get(f"/opportunities?client_id={CLIENT_5}&signal=expiring_document&limit=10", user=ADVISER).json()["items"]
    assert touch and touch[0]["is_touchpoint"] and touch[0]["evidence"]["document"] == "id_document" and touch[0]["evidence"]["days_left"] == 20


def test_an_expired_id_is_a_high_severity_gap_and_verifying_a_new_one_closes_it(fapi):
    def gap():
        return [g for g in fapi.get("/owner/drilldown?metric=compliance.gaps&limit=100", user=OWNER).json()["items"]
                if g["client"]["id"] == str(CLIENT_12) and g["kind"] == "identity"]
    before = fapi.get("/owner/business-health", user=OWNER).json()["compliance"]["score_percent"]
    assert gap() and gap()[0]["severity"] == "high"
    new = upload(fapi, CLIENT_12, "id_document", "2040-01-01").json()
    assert gap(), "an unverified upload does not close the gap"
    fapi.post(f"/identity/{new['id']}/verify", user=ADVISER_2, json={})
    assert not gap()
    assert fapi.get("/owner/business-health", user=OWNER).json()["compliance"]["score_percent"] > before


# ======================================================================================== access and privacy
def test_clients_cannot_reach_each_others_documents(fapi):
    mine = vault(fapi, CLIENT_1)["documents"][0]["id"]
    assert fapi.get(f"/identity/{mine}/url", user=CLIENT_2).status_code == 404
    other = fapi.get(f"/identity?client_id={CLIENT_2}", user=CLIENT_1).json()
    assert other["client_id"] == str(CLIENT_1), "a client's client_id parameter is ignored: they only ever see their own vault"
    assert fapi.get(f"/identity?client_id={CLIENT_1}", user=ADVISER_2).status_code == 404
    assert fapi.get("/identity", user=ADVISER).status_code == 422
    assert fapi.get("/identity").status_code == 401


def test_opening_a_document_gives_a_short_lived_signed_url_and_is_audited(fapi, fdb):
    doc = [d for d in vault(fapi, CLIENT_1)["documents"] if d["doc_type"] == "id_document"][0]
    r = fapi.get(f"/identity/{doc['id']}/url", user=ADVISER)
    assert r.status_code == 200 and "expires" in r.json()["url"] and r.json()["expires_at"]
    (row,) = audit_rows(fdb, action="identity.viewed", actor_id=ADVISER)
    assert row["client_id"] == CLIENT_1 and row["details"]["doc_type"] == "id_document"


def test_the_vault_never_exposes_the_storage_path(fapi):
    body = fapi.get("/identity", user=CLIENT_1).text
    assert "identity/" not in body and "storage_path" not in body
