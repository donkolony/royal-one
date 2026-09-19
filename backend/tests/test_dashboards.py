"""Dashboards: one call per home screen."""
from app.core import clock
from conftest import ADVISER, ADVISER_2, CLIENT_1, CLIENT_3, claim_id


def test_client_dashboard_shape_and_content(api):
    d = api.get("/me/dashboard", user=CLIENT_1).json()
    assert set(d) == {"generated_at", "client", "adviser", "net_worth", "policies", "open_claims", "goals", "reminders", "pending_requests"}
    assert d["client"]["full_name"] == "Demo Client One" and d["adviser"]["full_name"] == "Demo Adviser"
    assert d["policies"]["count"] == 4 and len(d["policies"]["items"]) == 4
    assert {g["title"] for g in d["goals"]["items"]} == {"Retire at 60", "Emergency fund", "Children's university fund"}
    assert d["pending_requests"]["count"] == 2


def test_net_worth_is_balance_sheet_plus_active_investment_and_retirement_policies(api):
    nw = api.get("/me/dashboard", user=CLIENT_1).json()["net_worth"]
    # assets: 2,400,000 + 220,000 + 85,000 (items) + 250,000 (investment policy) + 1,800,000 (retirement policy)
    assert nw["total_assets_cents"] == 240000000 + 22000000 + 8500000 + 25000000 + 180000000
    assert nw["total_liabilities_cents"] == 165000000 + 11000000
    assert nw["net_worth_cents"] == nw["total_assets_cents"] - nw["total_liabilities_cents"]
    sources = {(b["category"], b["source"]) for b in nw["breakdown"]}
    assert ("investments", "policy") in sources and ("retirement", "policy") in sources and ("property", "balance_sheet") in sources
    assert nw["currency"] == "ZAR" and nw["as_of"] == str(clock.today())


def test_client_dashboard_open_claims_include_own_draft(api):
    d = api.get("/me/dashboard", user=CLIENT_1).json()["open_claims"]
    assert d["count"] == 2 and {c["status"] for c in d["items"]} == {"submitted", "draft"}
    assert all(c["status_label"] in ("Sent to Royal Square", "Not sent yet") for c in d["items"])


def test_adviser_view_of_a_client_excludes_drafts_and_shows_all_reminders(api):
    d = api.get(f"/clients/{CLIENT_1}/dashboard", user=ADVISER).json()
    assert {c["status"] for c in d["open_claims"]["items"]} == {"submitted"}
    assert d["open_claims"]["items"][0]["status_label"] == "Submitted"  # adviser tone
    audiences = {r["audience"] for r in d["reminders"]["upcoming"]}
    assert "advisor" in audiences, "the adviser sees adviser-audience reminders for this client"
    client_view = api.get("/me/dashboard", user=CLIENT_1).json()["reminders"]["upcoming"]
    assert "advisor" not in {r["audience"] for r in client_view}


def test_advisor_dashboard(api):
    d = api.get("/advisor/dashboard", user=ADVISER).json()
    assert set(d) == {"generated_at", "counts", "claims_by_status", "needs_attention", "upcoming_reminders"}
    c = d["counts"]
    assert c["clients"] == 3 and c["open_claims"] == 3 and c["pending_requests"] == 3
    assert c["overdue_reminders"] >= 1 and c["reminders_due_7d"] >= 1
    by = {x["status"]: x["count"] for x in d["claims_by_status"]}
    assert by["submitted"] == 1 and by["assessment"] == 1 and by["in_repair"] == 1 and by["registered"] == 0
    assert [x["status"] for x in d["claims_by_status"]][0] == "submitted"


def test_needs_attention_is_prioritised_and_capped(api):
    items = api.get("/advisor/dashboard", user=ADVISER).json()["needs_attention"]
    kinds = [i["kind"] for i in items]
    assert kinds[0] == "reminder", "overdue reminders come first"
    assert {"reminder", "claim", "request", "email"} <= set(kinds)
    assert len(items) <= 10
    claim_titles = [i["title"] for i in items if i["kind"] == "claim"]
    assert any(t.startswith("New claim submitted: CLM-") for t in claim_titles)
    assert any("has been in" in t for t in claim_titles), "the seeded in-repair claim is stale"
    for i in items:
        assert set(i) == {"kind", "id", "title", "subtitle", "client", "due_at", "link"}
        assert i["link"]["id"]


def test_needs_attention_email_item_is_the_flagged_unread_thread(api):
    items = [i for i in api.get("/advisor/dashboard", user=ADVISER).json()["needs_attention"] if i["kind"] == "email"]
    assert items and items[0]["link"]["resource"] == "email_thread"


def test_another_advisers_dashboard_is_empty(api):
    d = api.get("/advisor/dashboard", user=ADVISER_2).json()
    assert d["counts"]["clients"] == 1 and d["counts"]["open_claims"] == 0 and d["needs_attention"] == []


def test_stale_claim_alert_disappears_when_the_claim_moves(api):
    cid = claim_id("in-repair")
    api.post(f"/claims/{cid}/transitions", user=ADVISER, json={"to_status": "completed"})
    titles = [i["title"] for i in api.get("/advisor/dashboard", user=ADVISER).json()["needs_attention"]]
    assert not any("CLM" in t and "has been in" in t and "In repair" in t for t in titles)


def test_dashboard_for_a_client_with_nothing(api, db):
    d = api.get("/me/dashboard", user=CLIENT_3).json()
    assert d["client"]["full_name"] == "Demo Client Three" and d["pending_requests"]["count"] == 0
    assert d["goals"]["items"] == []  # the only goal is achieved, so not active
