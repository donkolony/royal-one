"""Clients, policies, net worth, financial items, goals."""
from datetime import timedelta

import pytest

from app import seed
from app.core import clock
from conftest import ADVISER, ADVISER_2, CLIENT_1, CLIENT_2, CLIENT_3, CLIENT_4

INSURER = lambda api, name: next(i["id"] for i in api.get("/insurers", user=ADVISER).json()["items"] if i["name"] == name)


# ------------------------------------------------------------------------------------------------ me
def test_me_for_client_and_adviser(api):
    c = api.get("/me", user=CLIENT_1).json()
    assert c["role"] == "client" and c["advisor"] is None
    assert c["client"]["adviser"]["email"] == "adviser@demo.example" and c["client"]["drivers_licence_expiry"]
    a = api.get("/me", user=ADVISER).json()
    assert a["client"] is None and a["advisor"] == {"id": str(ADVISER)}


def test_patch_me_permissions(api):
    assert api.patch("/me", user=CLIENT_1, json={"phone": "+27 82 999 9999"}).json()["phone"] == "+27 82 999 9999"
    assert api.patch("/me", user=CLIENT_1, json={"drivers_licence_expiry": "2028-01-01"}).json()["client"]["drivers_licence_expiry"] == "2028-01-01"
    r = api.patch("/me", user=ADVISER, json={"drivers_licence_expiry": "2028-01-01"})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "drivers_licence_expiry"
    assert api.patch("/me", user=ADVISER, json={"phone": "+27 1"}).json()["phone"] == "+27 1"
    assert api.patch("/me", user=CLIENT_1, json={"full_name": "Hacker"}).status_code == 422
    assert api.patch("/me", user=CLIENT_1, json={"role": "advisor"}).status_code == 422


# --------------------------------------------------------------------------------------------- clients
def test_client_list_search_sort_paging(api):
    r = api.get("/clients", user=ADVISER).json()
    assert [c["full_name"] for c in r["items"]] == ["Johan Smit", "Lerato Dlamini", "Thabo Mokoena"]
    assert set(r["items"][0]) == {"id", "full_name", "email", "phone", "date_of_birth", "drivers_licence_expiry", "client_since",
                                  "last_annual_review_date", "dependants", "annual_income_cents", "counts", "created_at"}
    assert api.get("/clients?search=lerato", user=ADVISER).json()["total"] == 1
    assert api.get("/clients?search=CLIENT3@", user=ADVISER).json()["total"] == 1
    assert api.get("/clients?sort=-full_name", user=ADVISER).json()["items"][0]["full_name"] == "Thabo Mokoena"
    assert api.get("/clients?limit=2&offset=2", user=ADVISER).json()["items"].__len__() == 1


def test_client_counts(api):
    c = api.get(f"/clients/{CLIENT_1}", user=ADVISER).json()
    # open_claims is 1, not 2: the client's private draft claim must not leak into adviser-facing counts.
    assert c["counts"] == {"policies": 4, "open_claims": 1, "active_goals": 3, "pending_requests": 2, "pending_reminders": 1}


def test_patch_client(api):
    r = api.patch(f"/clients/{CLIENT_2}", user=ADVISER, json={"full_name": "Renamed Client", "phone": None, "date_of_birth": "1985-05-05",
                                                            "last_annual_review_date": "2026-01-01"})
    assert r.status_code == 200 and r.json()["full_name"] == "Renamed Client" and r.json()["phone"] is None
    assert r.json()["last_annual_review_date"] == "2026-01-01"
    assert api.patch(f"/clients/{CLIENT_2}", user=ADVISER, json={"full_name": None}).status_code == 422
    assert api.patch(f"/clients/{CLIENT_2}", user=ADVISER, json={"email": "x@y.example"}).status_code == 422, "email is the login identity"


# --------------------------------------------------------------------------------------------- policies
def test_policy_list_filters_and_shape(api):
    r = api.get("/policies", user=CLIENT_1).json()
    assert r["total"] == 4
    p = next(x for x in r["items"] if x["category"] == "motor")
    assert p["insurer"]["name"] == "Santam" and p["premium_frequency"] == "monthly" and p["asset_description"]
    assert set(p) == {"id", "client_id", "insurer", "category", "product_name", "policy_number", "status", "asset_description",
                      "cover_amount_cents", "current_value_cents", "premium_cents", "premium_frequency", "start_date", "renewal_date",
                      "valuation_certificate_date"}
    assert api.get("/policies?category=life", user=CLIENT_1).json()["total"] == 1
    assert api.get("/policies?category=weird", user=CLIENT_1).status_code == 422
    assert api.get("/policies", user=ADVISER).json()["total"] == 7  # 4 + 2 + 1 across the adviser's 3 clients
    assert api.get(f"/policies?client_id={CLIENT_2}", user=ADVISER).json()["total"] == 2
    assert api.get(f"/policies/{p['id']}", user=CLIENT_1).json()["id"] == p["id"]


def test_adviser_creates_and_edits_a_policy(api):
    body = {"client_id": str(CLIENT_3), "insurer_id": INSURER(api, "Discovery"), "category": "health", "product_name": "Medical aid plus",
            "policy_number": "DEMO-HLT-9", "premium_cents": 300000, "premium_frequency": "monthly", "renewal_date": "2027-01-01"}
    r = api.post("/policies", user=ADVISER, json=body)
    assert r.status_code == 201 and r.json()["insurer"]["name"] == "Discovery" and r.json()["status"] == "active"
    pid = r.json()["id"]
    assert api.get(f"/policies/{pid}", user=CLIENT_3).status_code == 200
    r = api.patch(f"/policies/{pid}", user=ADVISER, json={"status": "lapsed", "premium_cents": None})
    assert r.json()["status"] == "lapsed" and r.json()["premium_cents"] is None
    assert api.patch(f"/policies/{pid}", user=ADVISER, json={"product_name": None}).status_code == 422
    assert api.patch(f"/policies/{pid}", user=ADVISER, json={"insurer_id": "00000000-0000-4000-8000-000000000000"}).status_code == 422
    assert api.post("/policies", user=ADVISER, json={**body, "category": "spaceship"}).status_code == 422
    assert api.post("/policies", user=ADVISER, json={**body, "client_id": str(CLIENT_4)}).status_code == 404
    assert api.post("/policies", user=CLIENT_3, json=body).status_code == 403


# ----------------------------------------------------------------------------------------- net worth
def test_net_worth_endpoint_requires_client_id_for_advisers(api):
    r = api.get("/net-worth", user=ADVISER)
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "client_id"
    assert api.get(f"/net-worth?client_id={CLIENT_2}", user=ADVISER).json()["net_worth_cents"] == 4200000 - 1500000
    assert api.get("/net-worth", user=CLIENT_2).json()["net_worth_cents"] == 2700000


def test_lapsed_investment_policies_do_not_count_toward_net_worth(api, db):
    before = api.get("/net-worth", user=CLIENT_1).json()["total_assets_cents"]
    db.execute("update policies set status = 'lapsed' where id = %s", (seed.uid("policy-c1-invest"),))
    db.commit()
    assert api.get("/net-worth", user=CLIENT_1).json()["total_assets_cents"] == before - 25000000


# ----------------------------------------------------------------------------------- financial items
def test_financial_items_crud(api):
    r = api.post("/financial-items", user=ADVISER, json={"client_id": str(CLIENT_2), "kind": "asset", "category": "vehicle",
                                                        "label": "Car", "amount_cents": 15000000, "as_of_date": "2026-09-01"})
    assert r.status_code == 201, r.text
    item = r.json()
    assert api.get("/net-worth", user=CLIENT_2).json()["net_worth_cents"] == 2700000 + 15000000
    assert api.get("/financial-items", user=CLIENT_2).json()["total"] == 3
    assert api.get(f"/financial-items?client_id={CLIENT_2}&kind=liability", user=ADVISER).json()["total"] == 1
    assert api.patch(f"/financial-items/{item['id']}", user=ADVISER, json={"amount_cents": 10000000}).json()["amount_cents"] == 10000000
    assert api.patch(f"/financial-items/{item['id']}", user=ADVISER, json={"category": "home_loan"}).status_code == 422, "an asset cannot be a loan"
    assert api.patch(f"/financial-items/{item['id']}", user=ADVISER, json={"amount_cents": 0}).status_code == 422
    assert api.delete(f"/financial-items/{item['id']}", user=ADVISER).status_code == 204
    assert api.delete(f"/financial-items/{item['id']}", user=ADVISER).status_code == 404


@pytest.mark.parametrize("patch", [
    {"kind": "liability", "category": "cash"},         # category does not belong to the kind
    {"amount_cents": -5}, {"amount_cents": 1.5}, {"amount_cents": "100"}, {"label": ""}, {"as_of_date": "yesterday"},
])
def test_financial_item_validation(api, patch):
    body = {"client_id": str(CLIENT_2), "kind": "asset", "category": "cash", "label": "x", "amount_cents": 5, "as_of_date": "2026-09-01", **patch}
    assert api.post("/financial-items", user=ADVISER, json=body).status_code == 422


def test_clients_cannot_change_the_balance_sheet(api):
    item = api.get("/financial-items", user=CLIENT_1).json()["items"][0]
    assert api.patch(f"/financial-items/{item['id']}", user=CLIENT_1, json={"amount_cents": 1}).status_code == 403
    assert api.delete(f"/financial-items/{item['id']}", user=CLIENT_1).status_code == 403
    assert api.patch(f"/financial-items/{item['id']}", user=ADVISER_2, json={"amount_cents": 1}).status_code == 404


# --------------------------------------------------------------------------------------------- goals
def test_goal_progress_and_shape(api):
    goals = {g["title"]: g for g in api.get("/goals", user=CLIENT_1).json()["items"]}
    g = goals["Retire at 60"]
    assert g["progress_percent"] == 36.0 and g["type"] == "individual" and g["status"] == "active"
    assert set(g) == {"id", "title", "description", "category", "type", "status", "target_amount_cents", "current_amount_cents",
                      "progress_percent", "target_date", "participants", "created_by", "created_at", "updated_at"}
    assert goals["Emergency fund"]["progress_percent"] == 65.0
    shared = goals["Children's university fund"]
    assert shared["type"] == "shared" and {p["full_name"] for p in shared["participants"]} == {"Thabo Mokoena", "Lerato Dlamini"}
    assert api.get("/goals", user=CLIENT_2).json()["total"] == 1, "a shared goal appears for every participant"


def test_goal_status_filter(api):
    assert api.get("/goals", user=CLIENT_3).json()["total"] == 0
    assert api.get("/goals?status=achieved", user=CLIENT_3).json()["total"] == 1
    assert api.get("/goals?status=all", user=CLIENT_3).json()["total"] == 1
    assert api.get("/goals?status=bogus", user=CLIENT_3).status_code == 422


def test_create_goal_individual_and_shared(api):
    body = {"client_ids": [str(CLIENT_2)], "title": "New car", "category": "other", "target_amount_cents": 20000000,
            "current_amount_cents": 5000000, "target_date": str(clock.today() + timedelta(days=200)), "description": "Saving"}
    r = api.post("/goals", user=ADVISER, json=body)
    assert r.status_code == 201 and r.json()["type"] == "individual" and r.json()["progress_percent"] == 25.0
    assert r.json()["created_by"] == str(ADVISER)
    r = api.post("/goals", user=ADVISER, json={**body, "client_ids": [str(CLIENT_1), str(CLIENT_3)]})
    assert r.json()["type"] == "shared" and len(r.json()["participants"]) == 2


@pytest.mark.parametrize("patch", [
    {"client_ids": []}, {"client_ids": [str(CLIENT_1), str(CLIENT_1)]}, {"target_amount_cents": 0}, {"current_amount_cents": -1},
    {"title": ""}, {"title": "x" * 121}, {"category": "yacht"}, {"target_date": "2000-01-01"}, {"client_ids": [str(CLIENT_1)] * 6},
])
def test_goal_validation(api, patch):
    body = {"client_ids": [str(CLIENT_1)], "title": "T", "category": "other", "target_amount_cents": 100, **patch}
    assert api.post("/goals", user=ADVISER, json=body).status_code == 422


def test_goal_becomes_achieved_when_progress_reaches_target(api):
    goal = api.get("/goals", user=CLIENT_1).json()["items"][0]
    r = api.patch(f"/goals/{goal['id']}", user=ADVISER, json={"current_amount_cents": goal["target_amount_cents"]})
    assert r.json()["status"] == "achieved" and r.json()["progress_percent"] == 100.0
    r = api.patch(f"/goals/{goal['id']}", user=ADVISER, json={"current_amount_cents": goal["target_amount_cents"] * 2})
    assert r.json()["progress_percent"] == 100.0, "progress is capped at 100"
    r = api.patch(f"/goals/{goal['id']}", user=ADVISER, json={"target_amount_cents": goal["target_amount_cents"] * 4})
    assert r.json()["status"] == "active", "raising the target reopens an achieved goal"


def test_goal_patch_participants_and_archive(api):
    goal = next(g for g in api.get("/goals", user=CLIENT_1).json()["items"] if g["type"] == "shared")
    r = api.patch(f"/goals/{goal['id']}", user=ADVISER, json={"client_ids": [str(CLIENT_1)]})
    assert r.json()["type"] == "individual"
    assert api.get("/goals", user=CLIENT_2).json()["total"] == 0
    assert api.patch(f"/goals/{goal['id']}", user=ADVISER, json={"client_ids": [str(CLIENT_4)]}).status_code == 422
    assert api.patch(f"/goals/{goal['id']}", user=ADVISER, json={"title": None}).status_code == 422
    assert api.delete(f"/goals/{goal['id']}", user=ADVISER).status_code == 204
    assert api.get(f"/goals/{goal['id']}", user=CLIENT_1).json()["status"] == "archived"
    assert goal["id"] not in [g["id"] for g in api.get("/goals", user=CLIENT_1).json()["items"]]
    assert api.patch(f"/goals/{goal['id']}", user=ADVISER, json={"status": "active"}).json()["status"] == "active"


def test_clients_cannot_edit_goals(api):
    goal = api.get("/goals", user=CLIENT_1).json()["items"][0]
    assert api.patch(f"/goals/{goal['id']}", user=CLIENT_1, json={"current_amount_cents": 1}).status_code == 403
    assert api.delete(f"/goals/{goal['id']}", user=CLIENT_1).status_code == 403
