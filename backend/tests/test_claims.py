"""Motor claims: checklist, draft, uploads, submit, the state machine, adviser actions, review."""
import pytest

from conftest import ADVISER, CLIENT_1, CLIENT_2, claim_id, png_bytes

POLICE = {"reported": True, "case_number": "CAS 1/09/2026", "station": "Cape Town Central"}
COMPLETE_PATCH = {
    "incident": {"occurred_at": "2026-09-18T17:45:00Z", "location_text": "Corner of A St and B St, Cape Town",
                 "description": "Rear-ended at a red light by a white hatchback."},
    "police": POLICE,
    "driver": {"is_policyholder": True, "full_name": "Thabo Mokoena"},
    "vehicle_use": "personal",
}


def upload(api, user, cid, kind="vehicle_photo", data=None, ctype="image/png", name="a.png", **form):
    return api.post(f"/claims/{cid}/attachments", user=user, data={"kind": kind, **form},
                    files={"file": (name, data if data is not None else png_bytes(), ctype)})


def new_draft(api, user=CLIENT_1, **body):
    r = api.post("/claims", user=user, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def complete_draft(api, user=CLIENT_1, insurer=True):
    d = new_draft(api, user)
    iid = api.get("/insurers", user=user).json()["items"][0]["id"]
    patch = {**COMPLETE_PATCH, **({"insurer_id": iid} if insurer else {})}
    assert api.patch(f"/claims/{d['id']}", user=user, json=patch).status_code == 200
    assert upload(api, user, d["id"], "vehicle_photo").status_code == 201
    assert upload(api, user, d["id"], "drivers_licence").status_code == 201
    return d["id"]


# --------------------------------------------------------------------------------------------- checklist
def test_checklist_has_the_eight_prd_items(api):
    items = api.get("/claims/checklist", user=CLIENT_1).json()["items"]
    assert [i["order"] for i in items] == list(range(1, 9))
    assert items[0]["upload_kind"] == "road_photo" and "48 hours" in items[7]["description"]
    assert api.get("/claims/checklist").status_code == 401


# ------------------------------------------------------------------------------------------------ draft
def test_create_draft_with_empty_body(api):
    d = new_draft(api)
    assert d["status"] == "draft" and d["reference"] is None and d["status_label"] == "Not sent yet"
    assert d["timeline"][0]["type"] == "created" and d["attachments"] == []
    assert "insurer_id" in d["missing_fields"] and "attachments.drivers_licence" in d["missing_fields"]
    assert d["allowed_transitions"] == [{"to_status": "submitted", "direction": "forward", "label": "Send to Royal Square",
                                         "requires": d["missing_fields"], "actor": "client"}]


def test_create_draft_from_motor_policy_defaults_insurer(api, db):
    pol = api.get("/policies?category=motor", user=CLIENT_1).json()["items"][0]
    d = new_draft(api, policy_id=pol["id"])
    assert d["insurer"]["name"] == "Santam" and d["policy_id"] == pol["id"]


def test_draft_rejects_a_non_motor_policy(api):
    pol = api.get("/policies?category=life", user=CLIENT_1).json()["items"][0]
    r = api.post("/claims", user=CLIENT_1, json={"policy_id": pol["id"]})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "policy_id"


def test_create_returns_location_header(api):
    r = api.post("/claims", user=CLIENT_1, json={})
    assert r.headers["location"] == f"/api/v1/claims/{r.json()['id']}"


def test_patch_merges_objects_one_level_and_replaces_arrays(api):
    d = new_draft(api)
    api.patch(f"/claims/{d['id']}", user=CLIENT_1, json={"incident": {"location_text": "Somewhere in town"},
                                                       "witnesses": [{"name": "A"}, {"name": "B"}]})
    r = api.patch(f"/claims/{d['id']}", user=CLIENT_1, json={"incident": {"description": "Long enough description here."},
                                                            "witnesses": [{"name": "C", "phone": "+27 82 111 1111"}]}).json()
    assert r["incident"]["location_text"] == "Somewhere in town", "sibling field must survive a nested patch"
    assert r["incident"]["description"] == "Long enough description here."
    assert [w["name"] for w in r["witnesses"]] == ["C"], "arrays are replaced whole"
    cleared = api.patch(f"/claims/{d['id']}", user=CLIENT_1, json={"incident": {"location_text": None}}).json()
    assert cleared["incident"]["location_text"] is None


@pytest.mark.parametrize("body,field", [
    ({"incident": {"occurred_at": "2999-01-01T00:00:00Z"}}, "incident.occurred_at"),
    ({"incident": {"description": "short"}}, "incident.description"),
    ({"incident": {"location_lat": 91}}, "incident.location_lat"),
    ({"incident": {"occurred_at": "2026-09-18T17:45:00"}}, "incident.occurred_at"),  # naive datetime
    ({"police": {"reported": "yes"}}, "police.reported"),
    ({"vehicle_use": "pleasure"}, "vehicle_use"),
    ({"witnesses": [{"name": ""}]}, "witnesses[0].name"),
    ({"witnesses": [{"name": "A", "email": "not-an-email"}]}, "witnesses[0].email"),
    ({"third_parties": [{"name": "A"}] * 11}, "third_parties"),
    ({"insurer_id": "00000000-0000-4000-8000-000000000000"}, "insurer_id"),
    ({"bogus": 1}, "bogus"),
])
def test_patch_validation(api, body, field):
    d = new_draft(api)
    r = api.patch(f"/claims/{d['id']}", user=CLIENT_1, json=body)
    assert r.status_code == 422, r.text
    assert field in [x["field"] for x in r.json()["error"]["details"]]


def test_submitted_claims_cannot_be_edited_by_the_client(api):
    r = api.patch(f"/claims/{claim_id('submitted')}", user=CLIENT_1, json={"vehicle_use": "business"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_state_transition"


# ------------------------------------------------------------------------------------------- attachments
def test_upload_accepts_valid_image_and_returns_signed_url(api, storage):
    d = new_draft(api)
    r = upload(api, CLIENT_1, d["id"], label="Rear bumper")
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["kind"] == "vehicle_photo" and a["label"] == "Rear bumper" and a["content_type"] == "image/png"
    assert a["url"].startswith("memory://attachments/claims/") and a["url_expires_at"].endswith("Z")
    assert len(storage.files) >= 1
    assert api.get(f"/claims/{d['id']}", user=CLIENT_1).json()["attachments"][0]["id"] == a["id"]


@pytest.mark.parametrize("data,ctype,kind,code", [
    (b"MZ\x90\x00 not an image at all", "image/png", "vehicle_photo", 415),        # exe renamed to png
    (png_bytes(), "image/jpeg", "vehicle_photo", 415),                              # declared type lies
    (png_bytes(), "image/png", "witness_voice_note", 415),                          # image is not audio
    (b"%PDF-1.4\n%fake", "application/pdf", "vehicle_photo", 415),                  # pdf not accepted for a photo
    (b"<html><script>alert(1)</script></html>", "text/html", "other", 415),
    (b"", "image/png", "vehicle_photo", 422),                                       # empty
])
def test_upload_rejections(api, data, ctype, kind, code):
    d = new_draft(api)
    assert upload(api, CLIENT_1, d["id"], kind, data=data, ctype=ctype).status_code == code


def test_upload_rejects_unknown_kind_and_long_label(api):
    d = new_draft(api)
    assert upload(api, CLIENT_1, d["id"], "selfie").status_code == 422
    assert upload(api, CLIENT_1, d["id"], label="x" * 121).status_code == 422
    assert api.post(f"/claims/{d['id']}/attachments", user=CLIENT_1, data={"kind": "vehicle_photo"}).status_code == 422  # no file


def test_upload_size_limit(make_app, settings, fresh_db, storage):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.llm.base import LLMRouter
    from conftest import Api
    small = settings.model_copy(update={"max_upload_bytes": 100})
    api = Api(TestClient(create_app(small, pool=fresh_db, storage=storage, llm=LLMRouter([]))))
    d = new_draft(api)
    r = upload(api, CLIENT_1, d["id"], data=png_bytes() + b"0" * 200)
    assert r.status_code == 413 and r.json()["error"]["code"] == "payload_too_large"


def test_attachment_count_limit(settings, fresh_db, storage):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.llm.base import LLMRouter
    from conftest import Api
    api = Api(TestClient(create_app(settings.model_copy(update={"max_attachments_per_claim": 2}), pool=fresh_db, storage=storage, llm=LLMRouter([]))))
    d = new_draft(api)
    assert upload(api, CLIENT_1, d["id"]).status_code == 201
    assert upload(api, CLIENT_1, d["id"]).status_code == 201
    r = upload(api, CLIENT_1, d["id"])
    assert r.status_code == 422 and r.json()["error"]["details"][0]["code"] == "too_many"


def test_uploaded_filename_is_sanitised_and_never_a_path(api, storage):
    d = new_draft(api)
    a = upload(api, CLIENT_1, d["id"], name="../../etc/passwd.png").json()
    assert "/" not in a["filename"] and ".." not in a["filename"].replace("passwd", "")
    assert all(".." not in path for (_b, path) in storage.files)


def test_delete_attachment_only_while_draft(api, storage):
    d = new_draft(api)
    a = upload(api, CLIENT_1, d["id"]).json()
    n = len(storage.files)
    assert api.delete(f"/claims/{d['id']}/attachments/{a['id']}", user=CLIENT_1).status_code == 204
    assert len(storage.files) == n - 1
    assert api.delete(f"/claims/{d['id']}/attachments/{a['id']}", user=CLIENT_1).status_code == 404
    att = api.get(f"/claims/{claim_id('submitted')}", user=CLIENT_1).json()["attachments"][0]
    r = api.delete(f"/claims/{claim_id('submitted')}/attachments/{att['id']}", user=CLIENT_1)
    assert r.status_code == 409


def test_client_can_add_a_document_after_submission_and_it_shows_in_the_timeline(api):
    cid = claim_id("submitted")
    assert upload(api, CLIENT_1, cid, "id_document", label="Other driver ID").status_code == 201
    tl = api.get(f"/claims/{cid}", user=ADVISER).json()["timeline"]
    assert tl[-1]["type"] == "attachment_added" and tl[-1]["visible_to_client"] is True


# --------------------------------------------------------------------------------------------- submit
def test_submit_reports_every_missing_field(api):
    d = new_draft(api)
    r = api.post(f"/claims/{d['id']}/submit", user=CLIENT_1)
    assert r.status_code == 422
    fields = {x["field"] for x in r.json()["error"]["details"]}
    assert fields == set(d["missing_fields"]) and "attachments.photo" in fields and "police.reported" in fields
    assert api.get(f"/claims/{d['id']}", user=CLIENT_1).json()["status"] == "draft"


def test_police_case_number_required_only_when_reported(api):
    d = new_draft(api)
    api.patch(f"/claims/{d['id']}", user=CLIENT_1, json={"police": {"reported": True}})
    assert "police.case_number" in api.get(f"/claims/{d['id']}", user=CLIENT_1).json()["missing_fields"]
    api.patch(f"/claims/{d['id']}", user=CLIENT_1, json={"police": {"reported": False}})
    assert "police.case_number" not in api.get(f"/claims/{d['id']}", user=CLIENT_1).json()["missing_fields"]


def test_relationship_required_when_driver_is_not_the_policyholder(api):
    d = new_draft(api)
    api.patch(f"/claims/{d['id']}", user=CLIENT_1, json={"driver": {"is_policyholder": False, "full_name": "Sam"}})
    assert "driver.relationship_to_policyholder" in api.get(f"/claims/{d['id']}", user=CLIENT_1).json()["missing_fields"]


def test_a_licence_photo_alone_is_not_a_scene_photo(api):
    d = new_draft(api)
    upload(api, CLIENT_1, d["id"], "drivers_licence")
    m = api.get(f"/claims/{d['id']}", user=CLIENT_1).json()["missing_fields"]
    assert "attachments.photo" in m and "attachments.drivers_licence" not in m


def test_submit_success(api):
    cid = complete_draft(api)
    assert api.get(f"/claims/{cid}", user=CLIENT_1).json()["missing_fields"] == []
    r = api.post(f"/claims/{cid}/submit", user=CLIENT_1)
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["status"] == "submitted" and c["submitted_at"].endswith("Z")
    assert c["reference"].startswith("CLM-") and c["reference"].split("-")[2].isdigit()
    assert [e["type"] for e in c["timeline"]] == ["created", "submitted"]
    assert c["status_label"] == "Sent to Royal Square"
    assert api.get(f"/claims/{cid}", user=ADVISER).json()["status_label"] == "Submitted"  # adviser tone


def test_references_are_unique_and_increasing(api):
    a = api.post(f"/claims/{complete_draft(api)}/submit", user=CLIENT_1).json()["reference"]
    b = api.post(f"/claims/{complete_draft(api, CLIENT_2)}/submit", user=CLIENT_2).json()["reference"]
    assert a != b and int(b.split("-")[2]) == int(a.split("-")[2]) + 1


def test_submit_twice_is_a_state_conflict(api):
    cid = complete_draft(api)
    api.post(f"/claims/{cid}/submit", user=CLIENT_1)
    r = api.post(f"/claims/{cid}/submit", user=CLIENT_1)
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_state_transition"


def test_submitting_makes_the_claim_visible_to_the_adviser(api):
    cid = complete_draft(api)
    assert api.get(f"/claims/{cid}", user=ADVISER).status_code == 404
    api.post(f"/claims/{cid}/submit", user=CLIENT_1)
    assert api.get(f"/claims/{cid}", user=ADVISER).status_code == 200


# ---------------------------------------------------------------------------------------------- lists
def test_list_and_filters(api):
    items = api.get("/claims", user=ADVISER).json()
    assert items["total"] == 3 and {c["status"] for c in items["items"]} == {"submitted", "assessment", "in_repair"}
    assert api.get("/claims?status=assessment&status=in_repair", user=ADVISER).json()["total"] == 2
    assert api.get("/claims?search=SC-778201", user=ADVISER).json()["total"] == 1
    assert api.get("/claims?search=Johan", user=ADVISER).json()["total"] == 1
    assert api.get(f"/claims?client_id={CLIENT_2}", user=ADVISER).json()["total"] == 1
    assert api.get("/claims?status=bogus", user=ADVISER).status_code == 422
    assert api.get("/claims?sort=colour", user=ADVISER).status_code == 422
    mine = api.get("/claims?open=true", user=CLIENT_1).json()
    assert mine["total"] == 2  # submitted + own draft
    assert api.get("/claims?limit=1&offset=1", user=ADVISER).json()["items"].__len__() == 1


def test_summary_shape_and_days_in_status(api):
    c = next(x for x in api.get("/claims", user=ADVISER).json()["items"] if x["status"] == "in_repair")
    assert set(c) == {"id", "reference", "client", "insurer", "status", "status_label", "claim_number", "incident_occurred_at",
                      "incident_location_text", "hire_car_status", "days_in_status", "submitted_at", "updated_at"}
    assert c["days_in_status"] >= 9 and c["hire_car_status"] == "delivered" and c["claim_number"] == "LB-55012"


def test_pipeline_columns_and_order(api):
    cols = api.get("/claims/pipeline", user=ADVISER).json()["columns"]
    assert [c["status"] for c in cols] == ["submitted", "registered", "assessment", "quotes", "authorised", "in_repair", "completed"]
    assert [c["count"] for c in cols] == [1, 0, 1, 0, 0, 1, 0]
    assert cols[0]["claims"][0]["status_label"] == "Submitted" and cols[1]["label"] == "Registered (claim no. issued)"
    with_closed = api.get("/claims/pipeline?include_closed=true", user=ADVISER).json()["columns"]
    assert with_closed[-1]["status"] == "closed"


# ---------------------------------------------------------------------------------------- state machine
def test_detail_shape(api):
    c = api.get(f"/claims/{claim_id('assessment')}", user=ADVISER).json()
    for key in ("incident", "police", "driver", "vehicle_use", "witnesses", "third_parties", "insurer_details", "repair", "hire_car",
                "review", "missing_fields", "allowed_transitions", "attachments", "timeline", "created_at", "closed_at", "policy_id"):
        assert key in c, key
    assert c["insurer_details"]["claim_number"] == "SC-778201"
    assert [t["to_status"] for t in c["allowed_transitions"]] == ["quotes", "registered"]
    assert c["allowed_transitions"][1]["direction"] == "back"
    assert c["police"]["deadline_status"] == "met"


def test_client_timeline_hides_internal_notes(api):
    cid = claim_id("assessment")
    adviser = {e["type"] for e in api.get(f"/claims/{cid}", user=ADVISER).json()["timeline"]}
    client = api.get(f"/claims/{cid}", user=CLIENT_2).json()["timeline"]
    assert "note" in adviser and "note" not in {e["type"] for e in client}
    assert all(e["visible_to_client"] for e in client)


def test_walk_the_whole_pipeline_forward(api):
    cid = claim_id("submitted")
    api.patch(f"/claims/{cid}/insurer-details", user=ADVISER, json={"claim_number": "SC-1", "handler_name": "H", "handler_email": "h@ins.example"})
    for target in ["registered", "assessment", "quotes", "authorised", "in_repair", "completed", "closed"]:
        r = api.post(f"/claims/{cid}/transitions", user=ADVISER, json={"to_status": target, "note": f"to {target}"})
        assert r.status_code == 200, (target, r.text)
        assert r.json()["status"] == target
    c = api.get(f"/claims/{cid}", user=ADVISER).json()
    assert c["closed_at"] and c["allowed_transitions"] == []
    assert [e["to_status"] for e in c["timeline"] if e["type"] == "status_changed"] == ["registered", "assessment", "quotes", "authorised", "in_repair", "completed", "closed"]


def test_registered_requires_the_insurers_claim_number(api):
    cid = claim_id("submitted")
    tr = api.get(f"/claims/{cid}", user=ADVISER).json()["allowed_transitions"][0]
    assert tr["to_status"] == "registered" and tr["requires"] == ["insurer_details.claim_number"]
    r = api.post(f"/claims/{cid}/transitions", user=ADVISER, json={"to_status": "registered"})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "insurer_details.claim_number"
    api.patch(f"/claims/{cid}/insurer-details", user=ADVISER, json={"claim_number": "SC-9"})
    assert api.post(f"/claims/{cid}/transitions", user=ADVISER, json={"to_status": "registered"}).status_code == 200


@pytest.mark.parametrize("to", ["closed", "in_repair", "submitted", "draft", "assessment"])
def test_illegal_transitions_are_conflicts(api, to):
    r = api.post(f"/claims/{claim_id('submitted')}/transitions", user=ADVISER, json={"to_status": to})
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_state_transition"


def test_adviser_can_step_back_one_but_not_out_of_submitted_or_closed(api):
    cid = claim_id("assessment")
    r = api.post(f"/claims/{cid}/transitions", user=ADVISER, json={"to_status": "registered", "note": "Moved by mistake"})
    assert r.status_code == 200 and r.json()["status"] == "registered"
    assert r.json()["timeline"][-1]["title"].startswith("Status corrected")
    r = api.post(f"/claims/{cid}/transitions", user=ADVISER, json={"to_status": "submitted"})
    assert r.status_code == 200
    assert api.post(f"/claims/{cid}/transitions", user=ADVISER, json={"to_status": "draft"}).status_code == 409


def test_transition_can_be_hidden_from_the_client(api):
    cid = claim_id("assessment")
    api.post(f"/claims/{cid}/transitions", user=ADVISER, json={"to_status": "quotes", "visible_to_client": False})
    assert api.get(f"/claims/{cid}", user=CLIENT_2).json()["timeline"][-1]["to_status"] != "quotes"
    assert api.get(f"/claims/{cid}", user=ADVISER).json()["timeline"][-1]["to_status"] == "quotes"


def test_client_sees_client_labels(api):
    c = api.get(f"/claims/{claim_id('assessment')}", user=CLIENT_2).json()
    assert c["status_label"] == "Vehicle assessment" and c["allowed_transitions"] == []


def test_insurer_details_event_only_when_something_changed(api):
    cid = claim_id("assessment")
    before = len(api.get(f"/claims/{cid}", user=ADVISER).json()["timeline"])
    api.patch(f"/claims/{cid}/insurer-details", user=ADVISER, json={"claim_number": "SC-778201"})  # unchanged
    assert len(api.get(f"/claims/{cid}", user=ADVISER).json()["timeline"]) == before
    r = api.patch(f"/claims/{cid}/insurer-details", user=ADVISER, json={"handler_phone": "+27 21 000 0000"})
    assert r.json()["insurer_details"]["handler_phone"] == "+27 21 000 0000" and len(r.json()["timeline"]) == before + 1
    assert api.patch(f"/claims/{cid}/insurer-details", user=ADVISER, json={"handler_email": "nope"}).status_code == 422


def test_repair_details_and_hire_car(api):
    cid = claim_id("in-repair")
    r = api.patch(f"/claims/{cid}/repair-details", user=ADVISER, json={"repairer_name": "New Repairer", "quote_amount_cents": 2000000,
                                                                      "estimated_completion_date": "2026-10-10"})
    assert r.status_code == 200 and r.json()["repair"]["repairer_name"] == "New Repairer" and r.json()["repair"]["quote_amount_cents"] == 2000000
    r = api.patch(f"/claims/{cid}/hire-car", user=ADVISER, json={"status": "return_arranged", "return_date": "2026-10-11"})
    assert r.json()["hire_car"]["status"] == "return_arranged"
    assert r.json()["timeline"][-1]["type"] == "hire_car_updated" and r.json()["timeline"][-1]["title"] == "Hire car return arranged"
    assert api.patch(f"/claims/{cid}/hire-car", user=ADVISER, json={"status": "flying"}).status_code == 422
    assert api.patch(f"/claims/{cid}/hire-car", user=ADVISER, json={"status": None}).status_code == 422


def test_updates_default_visibility(api):
    cid = claim_id("in-repair")
    r = api.post(f"/claims/{cid}/updates", user=ADVISER, json={"type": "repair_update", "message": "Paint drying."})
    assert r.status_code == 201 and r.json()["visible_to_client"] is True and r.json()["title"] == "Repair update"
    assert r.json()["actor"]["role"] == "advisor"
    r = api.post(f"/claims/{cid}/updates", user=ADVISER, json={"message": "Internal only"})
    assert r.json()["type"] == "note" and r.json()["visible_to_client"] is False
    client_msgs = [e["message"] for e in api.get(f"/claims/{cid}", user=CLIENT_1 if False else __import__("conftest").CLIENT_3).json()["timeline"]]
    assert "Paint drying." in client_msgs and "Internal only" not in client_msgs
    assert api.post(f"/claims/{cid}/updates", user=ADVISER, json={"message": ""}).status_code == 422


def test_client_picks_a_repair_date_only_when_authorised(api):
    cid = claim_id("assessment")
    assert api.post(f"/claims/{cid}/repair-date", user=CLIENT_2, json={"drop_off_date": "2099-01-01"}).status_code == 409
    api.post(f"/claims/{cid}/transitions", user=ADVISER, json={"to_status": "quotes"})
    api.post(f"/claims/{cid}/transitions", user=ADVISER, json={"to_status": "authorised"})
    assert api.post(f"/claims/{cid}/repair-date", user=CLIENT_2, json={"drop_off_date": "2000-01-01"}).status_code == 422
    r = api.post(f"/claims/{cid}/repair-date", user=CLIENT_2, json={"drop_off_date": "2099-01-01"})
    assert r.status_code == 200 and r.json()["repair"]["drop_off_date"] == "2099-01-01"
    assert r.json()["timeline"][-1]["type"] == "repair_date_chosen"


def test_review_closes_a_completed_claim(api):
    from conftest import CLIENT_3
    cid = claim_id("in-repair")
    assert api.post(f"/claims/{cid}/review", user=CLIENT_3, json={"rating": 5}).status_code == 409  # not completed yet
    api.post(f"/claims/{cid}/transitions", user=ADVISER, json={"to_status": "completed"})
    ct = api.get(f"/claims/{cid}", user=CLIENT_3).json()
    assert [t["to_status"] for t in ct["allowed_transitions"]] == ["closed"]
    assert api.post(f"/claims/{cid}/review", user=CLIENT_3, json={"rating": 6}).status_code == 422
    r = api.post(f"/claims/{cid}/review", user=CLIENT_3, json={"rating": 5, "comment": "Quick and clear."})
    assert r.status_code == 200
    c = r.json()
    assert c["status"] == "closed" and c["closed_at"] and c["review"]["rating"] == 5 and c["review"]["comment"] == "Quick and clear."
    assert c["timeline"][-1]["type"] == "review_submitted"
    assert api.post(f"/claims/{cid}/review", user=CLIENT_3, json={"rating": 5}).status_code == 409


def test_police_deadline_status(api):
    d = new_draft(api)
    assert d["police"]["deadline_status"] == "pending" and d["police"]["report_deadline_at"].endswith("Z")
    old = api.patch(f"/claims/{d['id']}", user=CLIENT_1, json={"incident": {"occurred_at": "2020-01-01T00:00:00Z"}}).json()
    assert old["police"]["deadline_status"] == "overdue"
    met = api.patch(f"/claims/{d['id']}", user=CLIENT_1, json={"police": {"reported": True, "case_number": "CAS 1"}}).json()
    assert met["police"]["deadline_status"] == "met"
