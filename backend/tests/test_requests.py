"""Client requests: per-type validation, masking, status rules, attachments."""
from datetime import timedelta

import pytest

from app import seed
from app.core import clock
from conftest import ADVISER, ADVISER_2, CLIENT_1, CLIENT_2, png_bytes

MOTOR = str(seed.uid("policy-c1-motor"))
LIFE = str(seed.uid("policy-c1-life"))
TODAY = clock.today()
GOOD = {
    "address_change": {"address_line_1": "1 Test St", "suburb": "Gardens", "city": "Cape Town", "postal_code": "8001"},
    "bank_details_change": {"account_holder": "Demo", "bank_name": "Demo Bank", "account_type": "cheque", "account_number": "1234567890", "branch_code": "250655"},
    "policy_document": {"policy_id": LIFE, "document_kind": "policy_wording"},
    "border_letter": {"policy_id": MOTOR, "destination_countries": ["Namibia"], "travel_from": str(TODAY + timedelta(days=5)), "travel_to": str(TODAY + timedelta(days=15))},
    "irp5": {"provider_name": "Demo Investments", "tax_year": 2026},
    "consultation": {"preferred_dates": [str(TODAY + timedelta(days=3))], "mode": "phone", "topic": "Retirement"},
    "client_information": {"statement_type": "balance_sheet", "items": [{"label": "Savings", "type": "asset", "amount_cents": 500000}]},
}


def create(api, type_, payload=None, user=CLIENT_1, **kw):
    return api.post("/requests", user=user, json={"type": type_, "payload": GOOD[type_] if payload is None else payload, **kw})


def fields_of(r):
    return {d["field"]: d["code"] for d in r.json()["error"]["details"]}


def test_types_endpoint_describes_every_request_type(api):
    items = api.get("/requests/types", user=CLIENT_1).json()["items"]
    assert [t["type"] for t in items] == ["address_change", "bank_details_change", "policy_document", "border_letter", "irp5", "consultation", "client_information"]
    bank = next(t for t in items if t["type"] == "bank_details_change")
    assert bank["requires_verification"] is True and {f["name"] for f in bank["fields"]} >= {"account_number", "branch_code"}
    assert set(GOOD) == {t["type"] for t in items}


@pytest.mark.parametrize("type_", list(GOOD))
def test_every_type_can_be_submitted(api, type_):
    r = create(api, type_, client_note="Please help.")
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["type"] == type_ and d["status"] == "submitted" and d["client_note"] == "Please help." and d["attachments"] == []
    assert d["client"]["id"] == str(CLIENT_1) and d["adviser_response"] is None and d["submitted_at"].endswith("Z")
    assert r.headers["location"] == f"/api/v1/requests/{d['id']}"


def test_missing_required_fields_are_reported_with_paths(api):
    r = create(api, "address_change", {"suburb": "Gardens"})
    assert r.status_code == 422
    f = fields_of(r)
    assert f["payload.address_line_1"] == "required" and f["payload.city"] == "required" and f["payload.postal_code"] == "required"


@pytest.mark.parametrize("type_,patch,field,code", [
    ("address_change", {"postal_code": "80"}, "payload.postal_code", "invalid_format"),
    ("address_change", {"bogus": 1}, "payload.bogus", "extra_forbidden"),
    ("address_change", {"suburb": "x" * 81}, "payload.suburb", "too_long"),
    ("address_change", {"effective_date": "tomorrow"}, "payload.effective_date", "invalid_date"),
    ("bank_details_change", {"account_number": "12ab"}, "payload.account_number", "invalid_format"),
    ("bank_details_change", {"account_type": "gold"}, "payload.account_type", "invalid_value"),
    ("border_letter", {"travel_to": str(TODAY)}, "payload.travel_to", "too_small"),   # before travel_from
    ("border_letter", {"destination_countries": []}, "payload.destination_countries", "too_short"),
    ("border_letter", {"destination_countries": "Namibia"}, "payload.destination_countries", "invalid_type"),
    ("border_letter", {"policy_id": LIFE}, "payload.policy_id", "invalid_value"),     # not a motor policy
    ("policy_document", {"policy_id": "nope"}, "payload.policy_id", "invalid_uuid"),
    ("irp5", {"tax_year": "2026"}, "payload.tax_year", "invalid_type"),
    ("irp5", {"tax_year": True}, "payload.tax_year", "invalid_type"),
    ("irp5", {"tax_year": 1800}, "payload.tax_year", "too_small"),
    ("consultation", {"preferred_dates": [str(TODAY - timedelta(days=1))]}, "payload.preferred_dates[0]", "too_small"),
    ("consultation", {"preferred_dates": [str(TODAY)] * 4}, "payload.preferred_dates", "too_long"),
    ("consultation", {"mode": "carrier_pigeon"}, "payload.mode", "invalid_value"),
    ("client_information", {"items": []}, "payload.items", "too_short"),
    ("client_information", {"items": [{"label": "x", "type": "gift", "amount_cents": 5}]}, "payload.items[0].type", "invalid_value"),
    ("client_information", {"items": [{"label": "x", "type": "asset", "amount_cents": 0}]}, "payload.items[0].amount_cents", "too_small"),
    ("client_information", {"items": [{"label": "x", "type": "asset", "amount_cents": 5, "extra": 1}]}, "payload.items[0].extra", "extra_forbidden"),
])
def test_payload_validation(api, type_, patch, field, code):
    r = create(api, type_, {**GOOD[type_], **patch})
    assert r.status_code == 422, r.text
    assert fields_of(r).get(field) == code, fields_of(r)


def test_unknown_type_and_bad_body(api):
    assert api.post("/requests", user=CLIENT_1, json={"type": "teleport", "payload": {}}).status_code == 422
    assert api.post("/requests", user=CLIENT_1, json={"type": "irp5"}).status_code == 422
    assert api.post("/requests", user=CLIENT_1, json={"type": "irp5", "payload": GOOD["irp5"], "client_note": "x" * 1001}).status_code == 422


def test_bank_account_number_is_masked_for_clients_only(api):
    rid = create(api, "bank_details_change").json()["id"]
    assert create(api, "bank_details_change").json()["payload"]["account_number"] == "******7890"
    assert api.get(f"/requests/{rid}", user=CLIENT_1).json()["payload"]["account_number"] == "******7890"
    listed = [r for r in api.get("/requests?type=bank_details_change", user=CLIENT_1).json()["items"]]
    assert all(r["payload"]["account_number"].startswith("*") for r in listed)
    assert api.get(f"/requests/{rid}", user=ADVISER).json()["payload"]["account_number"] == "1234567890"
    seeded = api.get(f"/requests/{seed.uid('request-bank')}", user=CLIENT_1).json()
    assert seeded["payload"]["account_number"] == "******7890" and seeded["requires_verification"] is True


def test_list_filters(api):
    assert api.get("/requests", user=ADVISER).json()["total"] == 4
    assert api.get("/requests?open=true", user=ADVISER).json()["total"] == 3
    assert api.get("/requests?status=completed", user=ADVISER).json()["total"] == 1
    assert api.get("/requests?status=completed&status=submitted", user=ADVISER).json()["total"] == 3
    assert api.get("/requests?type=consultation", user=ADVISER).json()["total"] == 1
    assert api.get(f"/requests?client_id={CLIENT_2}", user=ADVISER).json()["total"] == 2
    assert api.get("/requests?type=nope", user=ADVISER).status_code == 422
    items = api.get("/requests", user=ADVISER).json()["items"]
    assert [i["submitted_at"] for i in items] == sorted((i["submitted_at"] for i in items), reverse=True)
    assert "attachments" not in items[0], "list items carry no attachments"
    assert api.get("/requests", user=ADVISER_2).json()["total"] == 0


def test_advisor_status_workflow(api):
    rid = create(api, "address_change").json()["id"]
    r = api.patch(f"/requests/{rid}", user=ADVISER, json={"status": "in_progress"})
    assert r.status_code == 200 and r.json()["status"] == "in_progress" and r.json()["completed_at"] is None
    assert api.patch(f"/requests/{rid}", user=ADVISER, json={"status": "in_progress"}).status_code == 409
    r = api.patch(f"/requests/{rid}", user=ADVISER, json={"status": "completed", "adviser_response": "Updated with all providers."})
    assert r.json()["status"] == "completed" and r.json()["completed_at"].endswith("Z") and r.json()["adviser_response"] == "Updated with all providers."
    again = api.patch(f"/requests/{rid}", user=ADVISER, json={"status": "declined", "adviser_response": "x"})
    assert again.status_code == 409 and again.json()["error"]["code"] == "invalid_state_transition"


def test_submitted_can_go_straight_to_completed_or_declined(api):
    a, b = create(api, "irp5").json()["id"], create(api, "irp5").json()["id"]
    assert api.patch(f"/requests/{a}", user=ADVISER, json={"status": "completed"}).status_code == 200
    assert api.patch(f"/requests/{b}", user=ADVISER, json={"status": "declined"}).status_code == 422, "a decline needs a reason"
    r = api.patch(f"/requests/{b}", user=ADVISER, json={"status": "declined", "adviser_response": "We cannot issue this."})
    assert r.status_code == 200 and r.json()["status"] == "declined"


def test_response_can_be_updated_without_changing_status(api):
    rid = create(api, "irp5").json()["id"]
    r = api.patch(f"/requests/{rid}", user=ADVISER, json={"adviser_response": "Working on it."})
    assert r.status_code == 200 and r.json()["status"] == "submitted" and r.json()["adviser_response"] == "Working on it."
    assert api.patch(f"/requests/{rid}", user=ADVISER, json={"status": "submitted"}).status_code == 422


def test_only_the_assigned_adviser_can_action_a_request(api):
    rid = create(api, "irp5").json()["id"]
    assert api.patch(f"/requests/{rid}", user=ADVISER_2, json={"status": "completed"}).status_code == 404
    assert api.patch(f"/requests/{rid}", user=CLIENT_1, json={"status": "completed"}).status_code == 403


def test_bank_details_change_never_touches_any_record(api, db):
    before = db.execute("select count(*) as n from profiles").fetchone()["n"]
    rid = create(api, "bank_details_change").json()["id"]
    api.patch(f"/requests/{rid}", user=ADVISER, json={"status": "completed"})
    cols = {r["column_name"] for r in db.execute("select column_name from information_schema.columns where table_name in ('profiles','clients')").fetchall()}
    assert not any("bank" in c or "account" in c for c in cols), "no table stores bank details outside a request payload"
    assert db.execute("select count(*) as n from profiles").fetchone()["n"] == before


def test_request_attachments(api):
    rid = create(api, "address_change").json()["id"]
    up = lambda **kw: api.post(f"/requests/{rid}/attachments", user=CLIENT_1, data=kw.get("data", {}),
                               files={"file": ("proof.png", kw.get("bytes", png_bytes()), kw.get("type", "image/png"))})
    r = up()
    assert r.status_code == 201 and r.json()["kind"] == "other"
    assert up(bytes=b"%PDF-1.4 x", type="application/pdf").status_code == 201
    assert up(bytes=b"not an image", type="image/png").status_code == 415
    assert len(api.get(f"/requests/{rid}", user=CLIENT_1).json()["attachments"]) == 2
    assert api.get(f"/requests/{rid}", user=ADVISER).json()["attachments"][0]["url"].startswith("memory://")
    doc = create(api, "irp5").json()["id"]
    r = api.post(f"/requests/{doc}/attachments", user=CLIENT_1, files={"file": ("a.png", png_bytes(), "image/png")})
    assert r.status_code == 422, "this request type accepts no attachments"
    api.patch(f"/requests/{rid}", user=ADVISER, json={"status": "completed"})
    assert up().status_code == 409, "closed requests take no more files"
    assert api.post(f"/requests/{rid}/attachments", user=CLIENT_2, files={"file": ("a.png", png_bytes(), "image/png")}).status_code == 404
