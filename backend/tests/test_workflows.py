"""The workflow engine, notifications, and the simulated insurer (brief section C)."""
import copy

import pytest

from app.core.config import Settings
from app.domain import constants as C
from app.domain import workflows as W
from app.services import workflow
from conftest import ADVISER, ADVISER_2, CLIENT_1, CLIENT_2, CLIENT_3, OWNER, Api, audit_rows, claim_id


# ================================================================================== the definitions are data
def test_workflows_lists_the_claim_and_every_request_with_steps_and_documents(api):
    items = api.get("/workflows", user=CLIENT_1).json()["items"]
    keys = {i["key"] for i in items}
    assert {"motor_claim", "address_change", "policy_document", "irp5", "border_letter"} <= keys
    claim = next(i for i in items if i["key"] == "motor_claim")
    assert [s["key"] for s in claim["steps"]][0] == "checklist" and {d["kind"] for d in claim["documents"]} == {"photo", "drivers_licence"}
    assert next(d for d in claim["documents"] if d["kind"] == "drivers_licence")["reuse_from_vault"] == "drivers_licence"
    addr = next(i for i in items if i["key"] == "address_change")
    assert addr["fields"] and addr["steps"] and addr["documents"][0]["reuse_from_vault"] == "proof_of_address"
    assert api.get("/workflows").status_code == 401


def test_the_request_types_endpoint_keeps_its_old_keys_and_gains_the_new_ones(api):
    t = api.get("/requests/types", user=CLIENT_1).json()["items"][0]
    assert {"type", "label", "requires_verification", "max_attachments", "fields"} <= set(t)
    assert {"description", "steps", "documents", "requires_identity", "insurer_forward", "sla_days"} <= set(t)


def test_the_old_constants_are_derived_from_the_single_config():
    assert C.CLAIM_STATUSES is W.CLAIM_STATUSES and C.REQUEST_TYPES == W.request_types()
    assert C.STATUS_ORDER == [s["value"] for s in W.CLAIM_STATUSES]


# ============================================== the engine reproduces the old hard-coded claim state machine exactly
def _reference_transitions(status, role):
    """The pre-engine logic, kept here as an independent oracle (services/claims.py before build step 4)."""
    order = C.STATUS_ORDER
    idx = order.index(status)
    if role == "client":
        if status == "draft":
            return [("submitted", "forward")]
        return [("closed", "forward")] if status == "completed" else []
    out = []
    if 1 <= idx <= 7:
        out.append((order[idx + 1], "forward"))
    if 2 <= idx <= 7:
        out.append((order[idx - 1], "back"))
    return out


@pytest.mark.parametrize("role", ["client", "advisor"])
@pytest.mark.parametrize("status", C.STATUS_ORDER)
def test_the_config_offers_exactly_what_the_old_code_offered(status, role):
    got = [(t["to_status"], t["direction"]) for t in workflow.transitions(status, role, {"missing_fields": [], "insurer_details.claim_number": "X"})]
    assert got == _reference_transitions(status, role)


def test_a_transition_reports_what_is_still_missing():
    (t,) = workflow.transitions("submitted", "advisor", {"insurer_details.claim_number": None})[:1]
    assert t["to_status"] == "registered" and t["requires"] == ["insurer_details.claim_number"]
    (d,) = workflow.transitions("draft", "client", {"missing_fields": ["incident.description", "vehicle_use"]})
    assert d["requires"] == ["incident.description", "vehicle_use"]


def test_back_labels_are_generated_from_the_status_names():
    back = [t for t in workflow.transitions("in_repair", "advisor", {}) if t["direction"] == "back"][0]
    assert back["label"] == "Move back to authorised"


# ===================================== adding a request type is a config entry: no new endpoint, page or migration
@pytest.fixture
def new_type(monkeypatch):
    definition = {
        "type": "pet_cover_quote", "label": "Request a pet cover quote", "requires_verification": False, "max_attachments": 0,
        "description": "A quote for a pet.", "requires_identity": False, "insurer_forward": True, "sla_days": 2,
        "steps": [{"key": "details", "label": "Your pet"}], "documents": [],
        "fields": [{"name": "pet_name", "label": "Pet name", "type": "string", "required": True, "max_length": 40},
                   {"name": "species", "label": "Species", "type": "enum", "required": True, "options": ["dog", "cat"]}],
    }
    types = list(C.REQUEST_TYPES) + [definition]
    monkeypatch.setattr(C, "REQUEST_TYPES", types)
    monkeypatch.setattr(C, "REQUEST_TYPE_BY_NAME", {t["type"]: t for t in types})
    return definition


def test_a_new_request_type_added_only_to_the_config_works_end_to_end(api, new_type):
    assert "pet_cover_quote" in [t["type"] for t in api.get("/requests/types", user=CLIENT_1).json()["items"]]
    bad = api.post("/requests", user=CLIENT_1, json={"type": "pet_cover_quote", "payload": {"pet_name": "Rex", "species": "lizard"}})
    assert bad.status_code == 422 and bad.json()["error"]["details"][0]["field"] == "payload.species"
    r = api.post("/requests", user=CLIENT_1, json={"type": "pet_cover_quote", "payload": {"pet_name": "Rex", "species": "dog"}})
    assert r.status_code == 201, r.text
    d = api.get(f"/requests/{r.json()['id']}", user=ADVISER).json()
    assert d["type_label"] == "Request a pet cover quote" and [e["type"] for e in d["timeline"]] == ["created", "forwarded"]
    assert api.post("/requests", user=CLIENT_1, json={"type": "not_a_type", "payload": {}}).status_code == 422


# ======================================================================================== request lifecycle
def _new_request(api, user=CLIENT_1):
    r = api.post("/requests", user=user, json={"type": "irp5", "payload": {"provider_name": "Old Mutual", "tax_year": 2026}})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_submitting_a_request_writes_a_timeline_and_tells_the_adviser(api, db):
    rid = _new_request(api)
    d = api.get(f"/requests/{rid}", user=CLIENT_1).json()
    assert [e["type"] for e in d["timeline"]] == ["created", "forwarded"] and d["insurer_forward"] is True
    n = api.get("/notifications?unread=true", user=ADVISER).json()
    assert any(i["kind"] == "new_request" and "IRP5" in i["title"] and i["link"] == {"resource": "request", "id": rid} for i in n["items"])


def test_the_adviser_moving_a_request_updates_the_clients_timeline_and_notifies_them(api):
    rid = _new_request(api)
    before = api.get("/notifications", user=CLIENT_1).json()["unread_count"]
    r = api.patch(f"/requests/{rid}", user=ADVISER, json={"status": "in_progress"})
    assert r.status_code == 200
    api.patch(f"/requests/{rid}", user=ADVISER, json={"status": "completed", "adviser_response": "Sent to your email."})
    tl = api.get(f"/requests/{rid}", user=CLIENT_1).json()["timeline"]
    assert [e["to_status"] for e in tl if e["type"] == "status_changed"] == ["in_progress", "completed"]
    assert tl[-1]["message"] == "Sent to your email." and tl[-1]["actor"]["role"] == "advisor"
    after = api.get("/notifications", user=CLIENT_1).json()
    assert after["unread_count"] == before + 2 and after["items"][0]["title"] == "Your request is complete"


def test_an_invalid_request_move_is_refused(api):
    rid = _new_request(api)
    api.patch(f"/requests/{rid}", user=ADVISER, json={"status": "completed"})
    assert api.patch(f"/requests/{rid}", user=ADVISER, json={"status": "in_progress"}).status_code == 409


def test_an_adviser_reply_without_a_status_change_is_a_note_and_notifies(api):
    rid = _new_request(api)
    api.patch(f"/requests/{rid}", user=ADVISER, json={"adviser_response": "We need your tax number."})
    d = api.get(f"/requests/{rid}", user=CLIENT_1).json()
    assert d["timeline"][-1]["type"] == "note" and d["status"] == "submitted"
    assert api.get("/notifications", user=CLIENT_1).json()["items"][0]["title"] == "Your adviser replied"


# ============================================================================================= notifications
def test_a_claim_submission_tells_the_adviser_and_an_advisers_move_tells_the_client(api):
    from test_claims import complete_draft  # the suite's helper for a fully filled draft
    cid = complete_draft(api, CLIENT_1)
    assert api.post(f"/claims/{cid}/submit", user=CLIENT_1).status_code == 200
    got = api.get("/notifications?unread=true", user=ADVISER).json()["items"]
    assert any(i["kind"] == "new_claim" and i["link"]["resource"] == "claim" for i in got)
    api.patch(f"/claims/{cid}/insurer-details", user=ADVISER, json={"claim_number": "SC-1"})
    assert api.post(f"/claims/{cid}/transitions", user=ADVISER, json={"to_status": "registered"}).status_code == 200
    mine = api.get("/notifications", user=CLIENT_1).json()["items"]
    assert mine[0]["title"] == "Registered with your insurer" and mine[0]["link"]["id"] == cid


def test_a_hidden_transition_does_not_notify_the_client(api):
    before = api.get("/notifications", user=CLIENT_2).json()["unread_count"]
    api.post(f"/claims/{claim_id('assessment')}/transitions", user=ADVISER, json={"to_status": "quotes", "visible_to_client": False})
    assert api.get("/notifications", user=CLIENT_2).json()["unread_count"] == before


def test_notifications_belong_to_their_recipient_and_can_be_read(api):
    api.post(f"/claims/{claim_id('assessment')}/transitions", user=ADVISER, json={"to_status": "quotes"})
    n = api.get("/notifications", user=CLIENT_2).json()
    assert n["unread_count"] == 1
    nid = n["items"][0]["id"]
    assert api.post(f"/notifications/{nid}/read", user=CLIENT_1).status_code == 404, "someone else's notification"
    assert api.post(f"/notifications/{nid}/read", user=CLIENT_2).status_code == 200
    assert api.get("/notifications?unread=true", user=CLIENT_2).json()["items"] == []
    api.post(f"/claims/{claim_id('assessment')}/transitions", user=ADVISER, json={"to_status": "assessment", "note": "back"})
    api.post(f"/claims/{claim_id('assessment')}/transitions", user=ADVISER, json={"to_status": "quotes"})
    assert api.post("/notifications/read-all", user=CLIENT_2).json()["marked"] >= 1
    assert api.get("/notifications", user=CLIENT_1).json()["unread_count"] == 0


# ===================================================================================== the simulated insurer
@pytest.fixture
def demo(settings, fresh_db, storage):
    from fastapi.testclient import TestClient
    from app.llm.base import LLMRouter
    from app.main import create_app
    s = settings.model_copy(update={"demo_mode": True})
    return Api(TestClient(create_app(s, pool=fresh_db, storage=storage, llm=LLMRouter([])), raise_server_exceptions=False))


def test_the_demo_routes_do_not_exist_unless_demo_mode_is_on(api):
    assert api.post("/demo/insurer-step", user=ADVISER, json={"claim_id": claim_id("submitted")}).status_code == 404
    assert api.post("/demo/reset", user=OWNER).status_code == 404
    assert api.get("/meta").json()["demo_mode"] is False


def test_demo_mode_is_refused_in_production():
    with pytest.raises(ValueError):
        Settings(_env_file=None, environment="production", demo_mode=True, database_url="postgresql://x", auth_mode="local_hs256", supabase_jwt_secret="s" * 40, storage_backend="memory")


def test_the_simulated_insurer_walks_a_claim_from_submitted_to_completed(demo, db):
    cid = claim_id("submitted")
    assert demo.get("/meta").json()["demo_mode"] is True
    seen = []
    for expected in ("registered", "assessment", "quotes", "authorised", "in_repair", "completed"):
        r = demo.post("/demo/insurer-step", user=ADVISER, json={"claim_id": cid})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == expected
        seen.append(r.json()["timeline"][-1])
    assert all(e["actor"] is None and "(simulated)" in e["message"] for e in seen), "the simulator says what it is and has no actor"
    d = demo.get(f"/claims/{cid}", user=CLIENT_1).json()
    assert d["insurer_details"]["claim_number"].startswith("SIM-") and d["repair"]["completed_at"] and d["repair"]["authorised_amount_cents"] == 1_850_000
    assert demo.post("/demo/insurer-step", user=ADVISER, json={"claim_id": cid}).status_code == 409, "it waits for the client's sign-off"
    n = db.execute("select count(*) as n from audit_log where action = 'claim.status_changed' and actor_id is null and details->>'simulated' = 'true'").fetchone()["n"]
    assert n == 6, "each simulated step is on the audit trail, as the system"


def test_each_simulated_step_reaches_both_screens_without_anyone_chasing(demo):
    cid = claim_id("submitted")
    c0, a0 = demo.get("/notifications", user=CLIENT_1).json()["unread_count"], demo.get("/notifications", user=ADVISER).json()["unread_count"]
    demo.post("/demo/insurer-step", user=ADVISER, json={"claim_id": cid})
    assert demo.get("/notifications", user=CLIENT_1).json()["unread_count"] == c0 + 1
    adv = demo.get("/notifications", user=ADVISER).json()
    assert adv["unread_count"] == a0 + 1 and adv["items"][0]["title"].startswith("Insurer (simulated)")
    client_view = demo.get(f"/claims/{cid}", user=CLIENT_1).json()["timeline"][-1]
    adviser_view = demo.get(f"/claims/{cid}", user=ADVISER).json()["timeline"][-1]
    assert client_view["id"] == adviser_view["id"] and client_view["to_status"] == "registered", "one shared timeline"


def test_the_simulator_respects_scope(demo):
    assert demo.post("/demo/insurer-step", user=ADVISER_2, json={"claim_id": claim_id("submitted")}).status_code == 404
    assert demo.post("/demo/insurer-step", user=CLIENT_1, json={"claim_id": claim_id("submitted")}).status_code == 403
    assert demo.post("/demo/insurer-step", user=OWNER, json={"claim_id": claim_id("submitted")}).status_code == 200
    assert demo.post("/demo/insurer-step", user=ADVISER, json={}).status_code == 422
    assert demo.post("/demo/insurer-step", user=ADVISER, json={"claim_id": claim_id("assessment"), "request_id": claim_id("assessment")}).status_code == 422


def test_the_simulated_provider_answers_a_request(demo):
    rid = _new_request(demo)
    a = demo.post("/demo/insurer-step", user=ADVISER, json={"request_id": rid}).json()
    assert a["status"] == "in_progress" and a["timeline"][-1]["type"] == "insurer_update" and "(simulated)" in a["timeline"][-1]["title"]
    b = demo.post("/demo/insurer-step", user=ADVISER, json={"request_id": rid}).json()
    assert b["status"] == "completed" and "simulated provider" in b["adviser_response"]
    assert demo.post("/demo/insurer-step", user=ADVISER, json={"request_id": rid}).status_code == 409
    assert demo.get("/notifications", user=CLIENT_1).json()["items"][0]["title"] == "Provider responded (simulated)"


def test_a_request_the_adviser_handles_is_not_forwarded_to_a_provider(demo):
    r = demo.post("/requests", user=CLIENT_1, json={"type": "consultation", "payload": {"preferred_dates": ["2099-01-01"], "mode": "video", "topic": "Review"}})
    assert r.status_code == 201
    assert "forwarded" not in [e["type"] for e in r.json()["timeline"]]
    assert demo.post("/demo/insurer-step", user=ADVISER, json={"request_id": r.json()["id"]}).status_code == 409


def test_reset_puts_the_demo_back_and_keeps_the_document_library(demo, db):
    db.execute("insert into documents (title, category, content_hash, status) values ('Keep me', 'policy_wording', 'h-keep', 'indexed')")
    db.commit()
    demo.post("/demo/insurer-step", user=ADVISER, json={"claim_id": claim_id("submitted")})
    assert demo.post("/demo/reset", user=ADVISER).status_code == 403
    assert demo.post("/demo/reset", user=OWNER).status_code == 200
    assert demo.get(f"/claims/{claim_id('submitted')}", user=ADVISER).json()["status"] == "submitted"
    assert db.execute("select count(*) as n from documents").fetchone()["n"] == 1
    assert len(audit_rows(db, action="demo.reset")) == 1
    assert demo.get("/audit/verify", user=OWNER).json()["ok"] is True
