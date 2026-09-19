"""The tests that matter most: nobody sees or changes anyone else's data (ARCHITECT section 12)."""
import pytest

from app import seed
from conftest import ADVISER, ADVISER_2, CLIENT_1, CLIENT_2, CLIENT_4, claim_id

C1_MOTOR = str(seed.uid("policy-c1-motor"))
C2_MOTOR = str(seed.uid("policy-c2-motor"))
C4_MOTOR = str(seed.uid("policy-c4-motor"))

ADVISER_ONLY_GETS = [
    "/advisor/dashboard", "/clients", f"/clients/{CLIENT_1}", f"/clients/{CLIENT_1}/dashboard", "/claims/pipeline",
    "/documents", "/assistant/conversations", "/email/status", "/email/threads",
]


@pytest.mark.parametrize("path", ADVISER_ONLY_GETS)
def test_clients_get_403_on_adviser_routes(api, path):
    r = api.get(path, user=CLIENT_1)
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize("path", ADVISER_ONLY_GETS)
def test_anonymous_gets_401_everywhere(api, path):
    assert api.get(path).status_code == 401


def test_advisers_cannot_use_client_only_routes(api):
    assert api.get("/me/dashboard", user=ADVISER).status_code == 403
    assert api.post("/claims", user=ADVISER, json={}).status_code == 403
    assert api.post("/requests", user=ADVISER, json={"type": "irp5", "payload": {}}).status_code == 403


def test_clients_cannot_call_adviser_write_routes(api):
    assert api.post("/goals", user=CLIENT_1, json={"client_ids": [str(CLIENT_1)], "title": "x", "category": "other", "target_amount_cents": 10}).status_code == 403
    assert api.post("/reminders", user=CLIENT_1, json={"client_id": str(CLIENT_1), "title": "x", "due_date": "2030-01-01", "audience": "client"}).status_code == 403
    assert api.post("/financial-items", user=CLIENT_1, json={}).status_code == 403
    assert api.patch(f"/clients/{CLIENT_1}", user=CLIENT_1, json={"phone": "1"}).status_code == 403
    assert api.post(f"/claims/{claim_id('assessment')}/transitions", user=CLIENT_2, json={"to_status": "quotes"}).status_code == 403
    assert api.post("/assistant/query", user=CLIENT_1, json={"question": "hello there"}).status_code == 403
    assert api.post("/email/drafts/generate", user=CLIENT_1, json={"claim_id": claim_id("assessment"), "purpose": "follow_up"}).status_code == 403


# ---------------------------------------------------------------------- client A cannot reach client B
def test_client_cannot_read_another_clients_data(api):
    other_claim = claim_id("assessment")  # belongs to client 2
    assert api.get(f"/claims/{other_claim}", user=CLIENT_1).status_code == 404
    assert api.get(f"/policies/{C2_MOTOR}", user=CLIENT_1).status_code == 404
    other_req = str(seed.uid("request-consult"))
    assert api.get(f"/requests/{other_req}", user=CLIENT_1).status_code == 404
    assert api.get(f"/goals/{seed.uid('goal-travel')}", user=CLIENT_1).status_code == 404


def test_client_lists_never_contain_other_clients_rows(api):
    assert {c["client"]["id"] for c in api.get("/claims", user=CLIENT_1).json()["items"]} == {str(CLIENT_1)}
    assert {p["client_id"] for p in api.get("/policies", user=CLIENT_1).json()["items"]} == {str(CLIENT_1)}
    assert {r["client"]["id"] for r in api.get("/requests", user=CLIENT_1).json()["items"]} == {str(CLIENT_1)}
    assert all(str(CLIENT_1) in [p["client_id"] for p in g["participants"]] for g in api.get("/goals", user=CLIENT_1).json()["items"])


def test_client_id_filter_cannot_widen_a_clients_scope(api):
    assert api.get(f"/claims?client_id={CLIENT_2}", user=CLIENT_1).status_code == 404
    assert api.get(f"/policies?client_id={CLIENT_2}", user=CLIENT_1).status_code == 404
    assert api.get(f"/reminders?client_id={CLIENT_2}", user=CLIENT_1).status_code == 404
    assert api.get(f"/net-worth?client_id={CLIENT_2}", user=CLIENT_1).status_code == 404
    assert api.get(f"/claims?client_id={CLIENT_1}", user=CLIENT_1).status_code == 200


def test_client_cannot_modify_another_clients_claim_or_request(api):
    cid = claim_id("draft")  # client 1's own draft
    assert api.patch(f"/claims/{cid}", user=CLIENT_2, json={"vehicle_use": "personal"}).status_code == 404
    assert api.post(f"/claims/{cid}/submit", user=CLIENT_2).status_code == 404
    assert api.post(f"/claims/{cid}/attachments", user=CLIENT_2, data={"kind": "vehicle_photo"},
                    files={"file": ("a.png", b"\x89PNG\r\n\x1a\n" + b"0" * 20, "image/png")}).status_code == 404
    assert api.post(f"/claims/{claim_id('assessment')}/repair-date", user=CLIENT_1, json={"drop_off_date": "2099-01-01"}).status_code == 404


def test_client_cannot_use_another_clients_policy(api):
    r = api.post("/claims", user=CLIENT_1, json={"policy_id": C2_MOTOR})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "policy_id"
    r = api.post("/requests", user=CLIENT_1, json={"type": "policy_document", "payload": {"policy_id": C2_MOTOR, "document_kind": "policy_schedule"}})
    assert r.status_code == 422


def test_client_cannot_complete_an_advisor_only_reminder(api, db):
    api.post("/reminders/run-check", user=ADVISER)
    rows = api.get("/reminders?audience=advisor", user=ADVISER).json()["items"]
    assert rows, "seed should produce adviser-audience reminders"
    assert api.post(f"/reminders/{rows[0]['id']}/complete", user=CLIENT_1).status_code == 404
    assert api.post(f"/reminders/{rows[0]['id']}/complete", user=CLIENT_2).status_code == 404


# ------------------------------------------------------------------------------- adviser X vs adviser Y
def test_adviser_only_sees_assigned_clients(api):
    a = api.get("/clients", user=ADVISER).json()
    assert a["total"] == 3 and str(CLIENT_4) not in [c["id"] for c in a["items"]]
    b = api.get("/clients", user=ADVISER_2).json()
    assert [c["id"] for c in b["items"]] == [str(CLIENT_4)]


def test_adviser_cannot_reach_unassigned_clients_data(api):
    assert api.get(f"/clients/{CLIENT_4}", user=ADVISER).status_code == 404
    assert api.get(f"/clients/{CLIENT_4}/dashboard", user=ADVISER).status_code == 404
    assert api.patch(f"/clients/{CLIENT_4}", user=ADVISER, json={"phone": "1"}).status_code == 404
    assert api.get(f"/policies/{C4_MOTOR}", user=ADVISER).status_code == 404
    assert api.get(f"/claims?client_id={CLIENT_4}", user=ADVISER).status_code == 404
    assert api.get(f"/net-worth?client_id={CLIENT_4}", user=ADVISER).status_code == 404
    assert api.post("/goals", user=ADVISER, json={"client_ids": [str(CLIENT_4)], "title": "x", "category": "other", "target_amount_cents": 10}).status_code == 422
    assert api.post("/reminders", user=ADVISER, json={"client_id": str(CLIENT_4), "title": "x", "due_date": "2030-01-01", "audience": "advisor"}).status_code == 404
    assert api.post("/financial-items", user=ADVISER, json={"client_id": str(CLIENT_4), "kind": "asset", "category": "cash", "label": "x", "amount_cents": 5, "as_of_date": "2026-01-01"}).status_code == 404


def test_other_advisers_cannot_act_on_a_claim(api):
    cid = claim_id("assessment")
    assert api.get(f"/claims/{cid}", user=ADVISER_2).status_code == 404
    assert api.post(f"/claims/{cid}/transitions", user=ADVISER_2, json={"to_status": "quotes"}).status_code == 404
    assert api.patch(f"/claims/{cid}/insurer-details", user=ADVISER_2, json={"claim_number": "X"}).status_code == 404
    assert api.post(f"/claims/{cid}/updates", user=ADVISER_2, json={"message": "hi"}).status_code == 404
    assert api.get("/claims/pipeline", user=ADVISER_2).json()["columns"][0]["count"] == 0


def test_advisers_never_see_draft_claims(api):
    draft = claim_id("draft")
    assert api.get(f"/claims/{draft}", user=ADVISER).status_code == 404
    assert draft not in [c["id"] for c in api.get("/claims", user=ADVISER).json()["items"]]
    assert draft not in [c["id"] for col in api.get("/claims/pipeline?include_closed=true", user=ADVISER).json()["columns"] for c in col["claims"]]
    assert draft not in [c["id"] for c in api.get(f"/clients/{CLIENT_1}/dashboard", user=ADVISER).json()["open_claims"]["items"]]
    assert api.get(f"/claims/{draft}", user=CLIENT_1).status_code == 200  # the owner still can
    assert api.post("/email/drafts/generate", user=ADVISER, json={"claim_id": draft, "purpose": "follow_up"}).status_code == 404


def test_advisers_mailbox_is_private(api, db):
    from app import seed as s
    with db.cursor() as cur:
        cur.execute("insert into email_threads (advisor_id, subject) values (%s, 'Adviser 2 private') returning id", (s.ADVISER_2,))
        tid = cur.fetchone()["id"]
        cur.execute("insert into email_messages (thread_id, from_email, sent_at, body_text) values (%s,'x@y.example',now(),'secret')", (tid,))
    db.commit()
    assert api.get(f"/email/threads/{tid}", user=ADVISER).status_code == 404
    assert str(tid) not in [t["id"] for t in api.get("/email/threads", user=ADVISER).json()["items"]]
    assert api.get(f"/email/threads/{tid}", user=ADVISER_2).status_code == 200


def test_conversations_are_private_to_their_adviser(make_app):
    from conftest import FakeProvider
    from app.llm.base import LLMRouter
    api = make_app(LLMRouter([FakeProvider(script=['{"answer":"x","used_sources":[],"sufficient":false}'])]))
    conv = api.post("/assistant/query", user=ADVISER, json={"question": "what is the weather like"}).json()["conversation_id"]
    assert api.get(f"/assistant/conversations/{conv}", user=ADVISER_2).status_code == 404
    assert api.post("/assistant/query", user=ADVISER_2, json={"question": "follow up please", "conversation_id": conv}).status_code == 404
    assert api.delete(f"/assistant/conversations/{conv}", user=ADVISER_2).status_code == 404


def test_row_level_security_is_enabled_on_every_table(db):
    with db.cursor() as cur:
        cur.execute("select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace "
                    "where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity and c.relname <> 'schema_migrations'")
        assert [r["relname"] for r in cur.fetchall()] == [], "every table must have RLS enabled (default deny)"
