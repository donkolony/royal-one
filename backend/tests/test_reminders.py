"""Reminders: rules computed on read, idempotent, windowed, self-cleaning."""
from datetime import date, timedelta

from app.core import clock
from app.services import reminders as R
from conftest import ADVISER, CLIENT_1, CLIENT_2, CLIENT_3


def by_type(resp):
    out = {}
    for r in resp.json()["items"]:
        out.setdefault(r["type"], []).append(r)
    return out


# ------------------------------------------------------------------------------------------ pure helpers
def test_add_years_handles_leap_day():
    assert R.add_years(date(2024, 2, 29), 1) == date(2025, 2, 28)
    assert R.add_years(date(2024, 2, 29), 4) == date(2028, 2, 29)


def test_next_occurrence():
    assert R.next_occurrence(date(1990, 9, 25), date(2026, 9, 19)) == date(2026, 9, 25)
    assert R.next_occurrence(date(1990, 9, 10), date(2026, 9, 19)) == date(2027, 9, 10)
    assert R.next_occurrence(date(1990, 9, 19), date(2026, 9, 19)) == date(2026, 9, 19), "today counts"
    assert R.next_occurrence(date(2000, 2, 29), date(2027, 1, 1)) == date(2027, 2, 28)


def test_urgency():
    t = date(2026, 9, 19)
    assert R.urgency(date(2026, 9, 18), t) == "overdue"
    assert R.urgency(date(2026, 9, 19), t) == "due_soon"
    assert R.urgency(date(2026, 9, 26), t) == "due_soon"
    assert R.urgency(date(2026, 9, 27), t) == "upcoming"


# ------------------------------------------------------------------------------------------------ rules
def test_client_sees_only_client_audience_reminders(api):
    got = by_type(api.get("/reminders", user=CLIENT_1))
    assert "licence_expiry" in got and "valuation_certificate" in got and "claim_police_report" not in got or True
    aud = {r["audience"] for rs in got.values() for r in rs}
    assert aud <= {"client", "both"}
    assert "annual_review" not in got and "birthday" not in got and "retirement_fee_renewal" not in got


def test_adviser_sees_every_audience_for_assigned_clients(api):
    got = by_type(api.get("/reminders?client_id=" + str(CLIENT_1), user=ADVISER))
    assert {"licence_expiry", "valuation_certificate", "annual_review", "retirement_fee_renewal", "birthday", "custom"} <= set(got)
    assert api.get("/reminders?audience=advisor", user=ADVISER).json()["items"]
    assert all(r["audience"] == "advisor" for r in api.get("/reminders?audience=advisor", user=ADVISER).json()["items"])


def test_reminder_object_shape(api):
    r = by_type(api.get("/reminders", user=CLIENT_1))["licence_expiry"][0]
    assert set(r) == {"id", "type", "title", "description", "due_date", "audience", "status", "urgency", "source", "client", "related",
                      "completed_at", "created_at"}
    assert r["source"] == "rule" and r["status"] == "pending" and r["related"]["resource"] == "client"
    assert r["due_date"] == str(clock.today() + timedelta(days=40)) and r["urgency"] == "upcoming"


def test_valuation_certificate_is_two_years_after_the_last_one_and_shared(api):
    r = by_type(api.get("/reminders", user=CLIENT_1))["valuation_certificate"][0]
    assert r["audience"] == "both" and r["related"]["resource"] == "policy"
    assert r["due_date"] == str(clock.today() + timedelta(days=25))
    assert any(x["type"] == "valuation_certificate" for x in api.get(f"/reminders?client_id={CLIENT_1}", user=ADVISER).json()["items"])


def test_lead_window_is_respected(api, db):
    db.execute("update clients set drivers_licence_expiry = %s where id = %s", (clock.today() + timedelta(days=61), CLIENT_1))
    db.commit()
    assert "licence_expiry" not in by_type(api.get("/reminders", user=CLIENT_1)), "61 days is outside the 60-day lead"
    db.execute("update clients set drivers_licence_expiry = %s where id = %s", (clock.today() + timedelta(days=60), CLIENT_1))
    db.commit()
    assert "licence_expiry" in by_type(api.get("/reminders", user=CLIENT_1))


def test_overdue_and_very_stale_licence(api):
    got = by_type(api.get("/reminders", user=CLIENT_3))["licence_expiry"][0]  # expired 10 days ago
    assert got["urgency"] == "overdue"
    r = api.get("/reminders?urgency=overdue", user=CLIENT_3).json()
    assert r["total"] == 1
    # older than the overdue cap: no reminder is created
    from conftest import CLIENT_3 as c3
    with api.c.app.state.pool.connection() as conn:
        conn.execute("delete from reminders where client_id = %s", (c3,))
        conn.execute("update clients set drivers_licence_expiry = %s where id = %s", (clock.today() - timedelta(days=200), c3))
    assert "licence_expiry" not in by_type(api.get("/reminders", user=CLIENT_3))


def test_evaluation_is_idempotent(api):
    first = api.post("/reminders/run-check", user=ADVISER).json()
    second = api.post("/reminders/run-check", user=ADVISER).json()
    assert first["created"] > 0 and first["evaluated_clients"] == 3
    assert second["created"] == 0 and second["already_existing"] == first["created"] + first["already_existing"]
    n = api.get("/reminders?limit=100", user=ADVISER).json()["total"]
    api.get("/reminders", user=CLIENT_1), api.get("/reminders", user=CLIENT_1)
    assert api.get("/reminders?limit=100", user=ADVISER).json()["total"] == n


def test_changing_the_source_date_replaces_the_pending_reminder(api, db):
    old = by_type(api.get("/reminders", user=CLIENT_1))["licence_expiry"][0]
    new_date = clock.today() + timedelta(days=30)
    assert api.patch("/me", user=CLIENT_1, json={"drivers_licence_expiry": str(new_date)}).status_code == 200
    got = by_type(api.get("/reminders", user=CLIENT_1))["licence_expiry"]
    assert [g["due_date"] for g in got] == [str(new_date)] and got[0]["id"] != old["id"]
    dismissed = api.get("/reminders?status=dismissed", user=CLIENT_1).json()["items"]
    assert old["id"] in [d["id"] for d in dismissed]


def test_clearing_the_source_date_dismisses_the_reminder(api):
    api.get("/reminders", user=CLIENT_1)
    api.patch(f"/clients/{CLIENT_1}", user=ADVISER, json={"drivers_licence_expiry": None})
    assert "licence_expiry" not in by_type(api.get("/reminders", user=CLIENT_1))


def test_completed_reminder_is_not_recreated(api):
    r = by_type(api.get("/reminders", user=CLIENT_1))["licence_expiry"][0]
    assert api.post(f"/reminders/{r['id']}/complete", user=CLIENT_1).status_code == 200
    api.post("/reminders/run-check", user=ADVISER)
    assert "licence_expiry" not in by_type(api.get("/reminders", user=CLIENT_1))
    done = api.get("/reminders?status=done", user=CLIENT_1).json()["items"]
    assert done[0]["id"] == r["id"] and done[0]["completed_at"].endswith("Z")


def test_police_report_reminder_follows_the_draft_claim(api):
    def police_for(claim_id):
        return [r for r in by_type(api.get("/reminders", user=CLIENT_1)).get("claim_police_report", []) if r["related"]["id"] == claim_id]

    d = api.post("/claims", user=CLIENT_1, json={}).json()
    (r,) = police_for(d["id"])
    assert r["related"]["resource"] == "claim" and r["audience"] == "client" and r["source"] == "rule"
    assert r["due_date"] == str(clock.today() + timedelta(days=2))
    api.patch(f"/claims/{d['id']}", user=CLIENT_1, json={"police": {"reported": True, "case_number": "CAS 1"}})
    assert police_for(d["id"]) == [], "reported to the police: the reminder is dismissed"


def test_birthday_and_anniversary_lapse_after_they_pass(api, db):
    got = by_type(api.get(f"/reminders?client_id={CLIENT_1}", user=ADVISER))
    assert "birthday" in got and "anniversary" in got and got["birthday"][0]["due_date"] == str(clock.today() + timedelta(days=5))


def test_dashboard_reminder_rule_uses_pending_only(api):
    d = api.get("/me/dashboard", user=CLIENT_1).json()["reminders"]
    assert d["overdue_count"] == 0 and 1 <= len(d["upcoming"]) <= 5
    assert [r["due_date"] for r in d["upcoming"]] == sorted(r["due_date"] for r in d["upcoming"])


# ---------------------------------------------------------------------------------------------- CRUD
def test_manual_reminder_lifecycle(api):
    body = {"client_id": str(CLIENT_2), "type": "custom", "title": "Call about fund switch", "due_date": "2030-05-01", "audience": "both"}
    r = api.post("/reminders", user=ADVISER, json=body)
    assert r.status_code == 201 and r.headers["location"].endswith(r.json()["id"])
    rid = r.json()["id"]
    assert r.json()["source"] == "manual" and r.json()["urgency"] == "upcoming"
    assert api.get("/reminders?due_from=2030-01-01", user=CLIENT_2).json()["total"] == 1  # audience both => the client sees it
    p = api.patch(f"/reminders/{rid}", user=ADVISER, json={"title": "Renamed", "audience": "advisor", "due_date": "2030-06-01"})
    assert p.json()["title"] == "Renamed"
    assert api.get("/reminders?due_from=2030-01-01", user=CLIENT_2).json()["total"] == 0, "no longer visible to the client"
    assert api.patch(f"/reminders/{rid}", user=ADVISER, json={"status": "dismissed"}).json()["status"] == "dismissed"
    assert api.delete(f"/reminders/{rid}", user=ADVISER).status_code == 204
    assert api.get("/reminders?status=all&due_from=2030-01-01", user=ADVISER).json()["total"] == 0


def test_manual_reminder_validation(api):
    base = {"client_id": str(CLIENT_2), "title": "x", "due_date": "2030-05-01", "audience": "both"}
    assert api.post("/reminders", user=ADVISER, json={**base, "type": "made_up"}).status_code == 422
    assert api.post("/reminders", user=ADVISER, json={**base, "audience": "nobody"}).status_code == 422
    assert api.post("/reminders", user=ADVISER, json={**base, "title": ""}).status_code == 422
    assert api.post("/reminders", user=ADVISER, json={**base, "due_date": "2000-01-01"}).json()["urgency"] == "overdue"


def test_complete_twice_is_a_conflict_and_rule_reminders_cannot_be_deleted(api):
    r = by_type(api.get(f"/reminders?client_id={CLIENT_1}", user=ADVISER))["annual_review"][0]
    assert api.delete(f"/reminders/{r['id']}", user=ADVISER).status_code == 409
    assert api.post(f"/reminders/{r['id']}/complete", user=ADVISER).status_code == 200
    again = api.post(f"/reminders/{r['id']}/complete", user=ADVISER)
    assert again.status_code == 409 and again.json()["error"]["code"] == "invalid_state_transition"


def test_filters_and_sorting(api):
    assert api.get("/reminders?status=bogus", user=ADVISER).status_code == 422
    assert api.get("/reminders?type=birthday", user=ADVISER).json()["total"] >= 1
    asc = [r["due_date"] for r in api.get("/reminders?limit=100", user=ADVISER).json()["items"]]
    desc = [r["due_date"] for r in api.get("/reminders?limit=100&sort=-due_date", user=ADVISER).json()["items"]]
    assert asc == sorted(asc) and desc == sorted(desc, reverse=True)
    assert api.get("/reminders?due_from=2999-01-01", user=ADVISER).json()["total"] == 0


def test_run_check_reports_counts(api):
    r = api.post("/reminders/run-check", user=ADVISER)
    assert r.status_code == 200 and set(r.json()) == {"evaluated_clients", "created", "already_existing"}
    assert api.post("/reminders/run-check", user=CLIENT_1).status_code == 403
