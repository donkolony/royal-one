"""Opportunity Radar: rules, evidence, honest numbers, and the lifecycle that feeds the owner's metrics (brief section A)."""
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from app.domain import radar_config
from app.llm.base import LLMError, LLMRouter
from app.services import radar
from conftest import (ADVISER, ADVISER_2, CLIENT_1, CLIENT_2, CLIENT_3, CLIENT_5, CLIENT_6, CLIENT_7, CLIENT_8, CLIENT_9, CLIENT_10, CLIENT_11,
                      CLIENT_12, OWNER, FakeProvider, audit_rows)

TODAY = date(2026, 9, 20)
CID = "11111111-1111-4111-8111-111111111111"


def facts(**over):
    base = dict(id=CID, name="Test Person", adviser_id=None, dob=date(1985, 1, 1), client_since=date(2020, 1, 1), licence_expiry=None,
                dependants=None, income=None, policies=[], items=[], goals=[], events=[])
    base.update(over)
    return base


def pol(category="life", status="active", cover=None, premium=None, freq="monthly", renewal=None, name="Product", number="P-1", pid="p1"):
    return dict(id=pid, category=category, status=status, cover_amount_cents=cover, premium_cents=premium, premium_frequency=freq,
                renewal_date=renewal, product_name=name, policy_number=number)


def goal(created_days_ago, target_in_days, current, target, status="active", title="Goal"):
    return dict(id="g1", title=title, status=status, target_date=TODAY + timedelta(days=target_in_days), current_amount_cents=current,
                target_amount_cents=target, created_at=datetime.combine(TODAY - timedelta(days=created_days_ago), datetime.min.time(), tzinfo=timezone.utc))


def signals(f):
    return {c.signal: c for c in radar.detect(f, TODAY)}


# ============================================================================================ pure rules
def test_under_insurance_is_computed_from_visible_numbers():
    f = facts(income=85_000_000, dependants=2, items=[dict(kind="liability", category="home_loan", amount_cents=176_000_000)],
              policies=[pol("life", cover=200_000_000, premium=95_000)])
    c = signals(f)["under_insured_life"]
    assert c.evidence["estimated_need_cents"] == 176_000_000 + 5 * 85_000_000 == 601_000_000
    assert c.evidence["existing_life_cover_cents"] == 200_000_000 and c.evidence["gap_cents"] == 401_000_000
    assert c.premium == round(401_000_000 / 100_000_000 * 240_000)
    assert c.value == round(c.premium * 0.15) and "assumed commission" in c.formula and not c.touchpoint


def test_under_insurance_never_guesses_without_an_income():
    assert "under_insured_life" not in signals(facts(income=None, dependants=3))


def test_a_small_or_proportionally_small_gap_is_ignored():
    f = facts(income=60_000_000, policies=[pol("life", cover=290_000_000)])     # need R3.0m, cover R2.9m: R100k, 3%
    assert "under_insured_life" not in signals(f)


def test_a_goal_behind_a_straight_line_is_flagged_with_the_catch_up_amount():
    c = signals(facts(goals=[goal(365, 550, 6_000_000, 30_000_000)]))["goal_behind"]
    assert c.evidence["progress_percent"] == 20.0 and 39 <= c.evidence["expected_percent"] <= 41
    assert c.evidence["required_monthly_cents"] == round((30_000_000 - 6_000_000) / c.evidence["months_left"])


def test_a_goal_within_tolerance_achieved_or_overdue_is_not_flagged():
    assert "goal_behind" not in signals(facts(goals=[goal(200, 165, 9_000_000, 10_000_000)]))
    assert "goal_behind" not in signals(facts(goals=[goal(365, 550, 6_000_000, 30_000_000, status="achieved")]))
    assert "goal_behind" not in signals(facts(goals=[goal(365, -5, 6_000_000, 30_000_000)]))


def test_life_events_inside_the_window_surface_and_old_ones_do_not():
    ev = lambda kind, days: dict(id=f"e{days}", kind=kind, occurred_on=TODAY - timedelta(days=days), note=None)
    got = radar.detect(facts(events=[ev("new_baby", 25), ev("marriage", 400)]), TODAY)
    assert [c.title for c in got if c.signal == "life_event"] == ["New baby: a natural time to talk"]


def test_a_divorce_is_a_touchpoint_with_no_sale_estimate():
    c = radar.detect(facts(events=[dict(id="e", kind="divorce", occurred_on=TODAY, note=None)]), TODAY)[0]
    assert c.touchpoint and c.value == 0 and "touchpoint" in c.formula


def test_retirement_approaching_uses_the_configured_age_and_window():
    assert "life_event" in signals(facts(dob=date(1967, 6, 1)))            # 59
    assert "life_event" not in signals(facts(dob=date(1990, 6, 1)))


def test_a_renewal_soon_is_a_touchpoint():
    got = [c for c in radar.detect(facts(policies=[pol("motor", renewal=TODAY + timedelta(days=15), name="Car cover")]), TODAY) if c.signal == "life_event"]
    assert got and got[0].touchpoint and "renews" in got[0].title


def test_missing_cover_follows_the_assets_on_file():
    f = facts(items=[dict(kind="asset", category="property", amount_cents=1), dict(kind="asset", category="vehicle", amount_cents=1)],
              dependants=1, income=1, policies=[pol("life", cover=10 ** 12)])
    cats = {c.subject for c in radar.detect(f, TODAY) if c.signal == "missing_cover"}
    assert cats == {"motor", "personal_other", "funeral", "disability"}


def test_a_lapsed_category_is_reported_once_as_lapsed_not_again_as_missing():
    f = facts(items=[dict(kind="asset", category="vehicle", amount_cents=1)], policies=[pol("motor", status="lapsed", premium=98_000)])
    got = radar.detect(f, TODAY)
    assert [c.signal for c in got if c.signal in ("lapsed_cover", "missing_cover")] == ["lapsed_cover"]


def test_a_single_product_is_only_suggested_when_nothing_else_is_worth_selling():
    only = facts(policies=[pol("health")])
    assert "single_product" in signals(only)
    with_gap = facts(policies=[pol("health")], dependants=2)
    assert "single_product" not in signals(with_gap) and "missing_cover" in signals(with_gap)
    assert "single_product" not in signals(facts(policies=[pol("health")], client_since=TODAY - timedelta(days=30)))


def test_the_licence_window_covers_just_expired_and_soon_to_expire():
    assert "expiring_document" in signals(facts(licence_expiry=TODAY + timedelta(days=25)))
    assert "expiring_document" in signals(facts(licence_expiry=TODAY - timedelta(days=10)))
    assert "expiring_document" not in signals(facts(licence_expiry=TODAY + timedelta(days=400)))


def test_the_estimate_reads_the_config_so_changing_an_assumption_changes_the_number(monkeypatch):
    f = facts(items=[dict(kind="asset", category="vehicle", amount_cents=1)])
    before = signals(f)["missing_cover"].value
    monkeypatch.setitem(radar_config.ASSUMPTIONS["commission_rate"], "motor", 0.30)
    assert signals(f)["missing_cover"].value == before * 3


def test_the_same_fact_has_a_stable_dedupe_key():
    a = radar.detect(facts(licence_expiry=TODAY + timedelta(days=25)), TODAY)[0]
    b = radar.detect(facts(licence_expiry=TODAY + timedelta(days=25)), TODAY)[0]
    assert a.dedupe_key == b.dedupe_key


# ================================================================================ acceptance on the demo data
def live(fapi, user=ADVISER, **qs):
    q = "&".join(f"{k}={v}" for k, v in qs.items())
    return fapi.get("/opportunities?limit=100&" + q, user=user).json()


def test_the_demo_data_surfaces_at_least_eight_opportunities_across_four_signal_types(fapi):
    d = fapi.get("/opportunities?limit=100&status=all", user=OWNER).json()
    types = {i["signal"] for i in d["items"]}
    assert d["total"] >= 8 and len(types) >= 4
    assert types == set(radar_config.SIGNALS), "the demo dataset exercises every rule"


def test_every_opportunity_is_traceable_to_its_source_data(fapi):
    for o in fapi.get("/opportunities?limit=100&status=all", user=OWNER).json()["items"]:
        assert o["evidence"] and o["value_formula"] and o["why_now"] and o["suggested_action"] and o["is_demo_estimate"] is True
        assert o["client"]["full_name"] and o["adviser"]["full_name"]
        if not o["is_touchpoint"]:
            assert o["est_annual_value_cents"] > 0 and o["est_annual_premium_cents"] > 0


def test_the_demo_star_client_is_under_insured_with_the_evidence_on_the_card(fapi):
    items = live(fapi, client_id=CLIENT_1)["items"]
    star = next(i for i in items if i["signal"] == "under_insured_life")
    assert star["client"]["full_name"] == "Thabo Mokoena" and star["evidence"]["gap_cents"] == 401_000_000
    assert {"missing_cover", "expiring_document"} <= {i["signal"] for i in items}


def test_the_fully_covered_client_has_no_opportunities(fapi):
    assert live(fapi, client_id=CLIENT_10, status="all")["total"] == 0


def test_the_list_is_ranked_by_estimated_value_and_repeated_reads_do_not_duplicate(fapi):
    first = live(fapi)
    values = [i["est_annual_value_cents"] for i in first["items"]]
    assert values == sorted(values, reverse=True)
    assert live(fapi)["total"] == first["total"]


def test_filters_by_signal_and_unknown_signal_is_rejected(fapi):
    got = live(fapi, signal="lapsed_cover")["items"]
    assert got and {i["signal"] for i in got} == {"lapsed_cover"}
    assert fapi.get("/opportunities?signal=nonsense", user=ADVISER).status_code == 422


# ============================================================================================== lifecycle
def first(fapi, signal, client=None, user=ADVISER):
    qs = {"signal": signal, **({"client_id": client} if client else {})}
    return live(fapi, user=user, **qs)["items"][0]


def test_create_task_makes_an_adviser_reminder_and_marks_it_actioned(fapi, fdb):
    o = first(fapi, "under_insured_life", CLIENT_1)
    r = fapi.post(f"/opportunities/{o['id']}/task", user=ADVISER)
    assert r.status_code == 200 and r.json()["status"] == "actioned" and r.json()["task_reminder_id"]
    rem = fdb.execute("select * from reminders where id = %s", (r.json()["task_reminder_id"],)).fetchone()
    assert rem["audience"] == "advisor" and rem["related_resource"] == "opportunity" and rem["client_id"] == CLIENT_1
    assert fapi.post(f"/opportunities/{o['id']}/task", user=ADVISER).status_code == 409
    assert [e["kind"] for e in r.json()["events"]] == ["surfaced", "task_created"]


def test_logging_outreach_actions_it_and_records_the_channel(fapi):
    o = first(fapi, "lapsed_cover", CLIENT_9)
    r = fapi.post(f"/opportunities/{o['id']}/outreach", user=ADVISER, json={"channel": "whatsapp", "note": "Sent a message"})
    assert r.status_code == 200 and r.json()["status"] == "actioned"
    assert r.json()["events"][-1]["channel"] == "whatsapp"
    assert fapi.post(f"/opportunities/{o['id']}/outreach", user=ADVISER, json={"channel": "fax"}).status_code == 422


def test_snoozing_hides_it_from_the_live_list_and_it_returns_when_the_date_passes(fapi, fdb):
    o = first(fapi, "single_product")
    assert fapi.post(f"/opportunities/{o['id']}/snooze", user=ADVISER, json={"days": 7}).json()["status"] == "snoozed"
    assert o["id"] not in [i["id"] for i in live(fapi)["items"]]
    fdb.execute("update opportunities set snoozed_until = current_date - 1 where id = %s", (o["id"],))
    fdb.commit()
    assert o["id"] in [i["id"] for i in live(fapi)["items"]]
    assert fapi.post(f"/opportunities/{o['id']}/snooze", user=ADVISER, json={"days": 0}).status_code == 422


def test_marking_one_won_updates_the_owners_metrics(fapi):
    before = fapi.get("/opportunities/summary", user=OWNER).json()
    o = first(fapi, "under_insured_life", CLIENT_1)
    fapi.post(f"/opportunities/{o['id']}/outreach", user=ADVISER, json={"channel": "email"})
    r = fapi.post(f"/opportunities/{o['id']}/outcome", user=ADVISER, json={"outcome": "won", "reason": "Client took R3m extra life cover"})
    assert r.status_code == 200 and r.json()["status"] == "won" and r.json()["won_value_cents"] == o["est_annual_value_cents"]
    after = fapi.get("/opportunities/summary", user=OWNER).json()
    assert after["totals"]["won"] == before["totals"]["won"] + 1
    assert after["totals"]["won_value_cents"] == before["totals"]["won_value_cents"] + o["est_annual_value_cents"]
    assert after["totals"]["open_value_cents"] == before["totals"]["open_value_cents"] - o["est_annual_value_cents"]
    assert after["totals"]["conversion_rate"] == 1.0
    sarah = next(a for a in after["by_adviser"] if a["adviser"]["id"] == str(ADVISER))
    assert sarah["won"] == 1 and sarah["actioned"] >= 1
    assert next(s for s in after["by_signal"] if s["signal"] == "under_insured_life")["won"] == 1


def test_a_reason_is_required_and_an_actual_value_overrides_the_estimate(fapi):
    o = first(fapi, "lapsed_cover", CLIENT_12, user=ADVISER_2)
    assert fapi.post(f"/opportunities/{o['id']}/outcome", user=ADVISER_2, json={"outcome": "won", "reason": "x"}).status_code == 422
    r = fapi.post(f"/opportunities/{o['id']}/outcome", user=ADVISER_2,
                  json={"outcome": "won", "reason": "Reinstated the policy", "actual_annual_value_cents": 123_400})
    assert r.json()["won_value_cents"] == 123_400 and r.json()["outcome_reason"] == "Reinstated the policy"


def test_a_lost_opportunity_needs_a_reason_and_can_be_reopened_but_a_won_one_cannot(fapi):
    o = first(fapi, "single_product")
    assert fapi.post(f"/opportunities/{o['id']}/outcome", user=ADVISER, json={"outcome": "lost", "reason": "Client declined"}).json()["status"] == "lost"
    assert fapi.post(f"/opportunities/{o['id']}/task", user=ADVISER).status_code == 409
    assert fapi.post(f"/opportunities/{o['id']}/reopen", user=ADVISER).json()["status"] == "open"
    fapi.post(f"/opportunities/{o['id']}/outcome", user=ADVISER, json={"outcome": "won", "reason": "Took a funeral plan"})
    assert fapi.post(f"/opportunities/{o['id']}/reopen", user=ADVISER).status_code == 409


def test_a_won_opportunity_does_not_come_back_on_the_next_read(fapi):
    o = first(fapi, "single_product")
    fapi.post(f"/opportunities/{o['id']}/outcome", user=ADVISER, json={"outcome": "won", "reason": "Sold"})
    again = live(fapi, status="all")["items"]
    assert [i["status"] for i in again if i["id"] == o["id"]] == ["won"]
    assert len([i for i in again if i["signal"] == "single_product" and i["client"]["id"] == o["client"]["id"]]) == 1


def test_when_the_data_changes_the_open_opportunity_expires_instead_of_lingering(fapi):
    o = first(fapi, "single_product", CLIENT_8)
    assert fapi.patch(f"/clients/{CLIENT_8}", user=ADVISER, json={"dependants": 2}).status_code == 200   # now a missing-cover case
    got = live(fapi, status="all")["items"]
    assert next(i for i in got if i["id"] == o["id"])["status"] == "expired"


def test_the_estimate_follows_the_data_when_the_evidence_changes(fapi):
    o = first(fapi, "under_insured_life", CLIENT_1)
    fapi.patch(f"/clients/{CLIENT_1}", user=ADVISER, json={"annual_income_cents": 100_000_000})
    o2 = fapi.get(f"/opportunities/{o['id']}", user=ADVISER).json()
    assert o2["evidence"]["annual_income_cents"] == 100_000_000 and o2["est_annual_value_cents"] > o["est_annual_value_cents"]


# ====================================================================================== who can do what
def test_a_client_cannot_see_the_radar_at_all(fapi):
    assert fapi.get("/opportunities", user=CLIENT_1).status_code == 403
    assert fapi.get("/opportunities/summary", user=CLIENT_1).status_code == 403


def test_the_owner_sees_everything_but_cannot_act(fapi):
    o = first(fapi, "under_insured_life", CLIENT_1)
    assert fapi.get(f"/opportunities/{o['id']}", user=OWNER).status_code == 200
    for path, body in (("task", None), ("outcome", {"outcome": "won", "reason": "nope"}), ("snooze", {"days": 3}), ("outreach", {"channel": "email"})):
        assert fapi.post(f"/opportunities/{o['id']}/{path}", user=OWNER, json=body or {}).status_code == 403, path


def test_an_adviser_sees_only_their_own_clients_opportunities(fapi):
    mine = {i["adviser"]["id"] for i in live(fapi, status="all")["items"]}
    theirs = {i["adviser"]["id"] for i in fapi.get("/opportunities?limit=100&status=all", user=ADVISER_2).json()["items"]}
    assert mine == {str(ADVISER)} and theirs == {str(ADVISER_2)}


def test_another_advisers_opportunity_is_a_404_and_the_attempt_is_logged(fapi, fdb):
    o = first(fapi, "under_insured_life", CLIENT_1)
    assert fapi.get(f"/opportunities/{o['id']}", user=ADVISER_2).status_code == 404
    assert fapi.post(f"/opportunities/{o['id']}/outcome", user=ADVISER_2, json={"outcome": "won", "reason": "not mine"}).status_code == 404
    assert fapi.get(f"/opportunities?client_id={CLIENT_1}", user=ADVISER_2).status_code == 404
    assert len(audit_rows(fdb, action="access.denied", actor_id=ADVISER_2)) >= 1


def test_actions_are_audited(fapi, fdb):
    o = first(fapi, "single_product")
    fapi.post(f"/opportunities/{o['id']}/task", user=ADVISER)
    fapi.post(f"/opportunities/{o['id']}/outcome", user=ADVISER, json={"outcome": "lost", "reason": "Not now"})
    acts = [r["action"] for r in audit_rows(fdb, client_id=o["client"]["id"]) if r["action"].startswith("opportunity.")]
    assert "opportunity.task_created" in acts and "opportunity.lost" in acts


def test_owner_summary_lists_every_adviser_and_the_definitions(fapi):
    s = fapi.get("/opportunities/summary", user=OWNER).json()
    assert {a["adviser"]["full_name"] for a in s["by_adviser"]} == {"Sarah van der Merwe", "Priya Naidoo"}
    assert s["totals"]["surfaced"] >= 8 and s["totals"]["open_value_cents"] > 0
    assert "conversion" in s["definitions"] and s["assumptions"]["label"].startswith("Demo estimate")
    mine = fapi.get("/opportunities/summary", user=ADVISER).json()
    assert [a["adviser"]["full_name"] for a in mine["by_adviser"]] == ["Sarah van der Merwe"]


def test_assumptions_are_served_for_the_how_is_this_calculated_tooltip(fapi):
    a = fapi.get("/opportunities/assumptions", user=ADVISER).json()
    assert a["values"]["life_income_multiple"] == 5 and "under_insured_life" in a["signals"] and "placeholder" in a["label"].lower()


# =============================================================================================== life events
def test_an_adviser_records_a_life_event_and_it_creates_an_opportunity(fapi):
    r = fapi.post(f"/clients/{CLIENT_8}/life-events", user=ADVISER, json={"kind": "marriage", "occurred_on": date.today().isoformat(), "note": "Married in Durban"})
    assert r.status_code == 201 and r.json()["kind"] == "marriage"
    assert any(i["signal"] == "life_event" and "Marriage" in i["title"] for i in live(fapi, client_id=CLIENT_8)["items"])
    assert fapi.get(f"/clients/{CLIENT_8}/life-events", user=OWNER).json()["items"][0]["kind"] == "marriage"


def test_a_life_event_cannot_be_in_the_future_or_recorded_by_the_wrong_people(fapi):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert fapi.post(f"/clients/{CLIENT_8}/life-events", user=ADVISER, json={"kind": "marriage", "occurred_on": tomorrow}).status_code == 422
    ok = {"kind": "marriage", "occurred_on": date.today().isoformat()}
    assert fapi.post(f"/clients/{CLIENT_8}/life-events", user=OWNER, json=ok).status_code == 403
    assert fapi.post(f"/clients/{CLIENT_8}/life-events", user=ADVISER_2, json=ok).status_code == 404
    assert fapi.post(f"/clients/{CLIENT_8}/life-events", user=CLIENT_8, json=ok).status_code == 403


# ================================================================================================ outreach drafts
def _draft(api, o, channel="email", user=ADVISER):
    return api.post(f"/opportunities/{o['id']}/draft", user=user, json={"channel": channel})


def test_the_default_draft_is_a_template_that_never_shows_the_internal_calculation(fapi):
    o = first(fapi, "under_insured_life", CLIENT_1)
    d = _draft(fapi, o).json()
    assert d["source"] == "template" and d["requires_human_review"] is True and d["subject"] and d["body"].startswith("Hi Thabo,")
    assert "401" not in d["body"] and "gap" not in d["body"].lower()
    w = _draft(fapi, o, "whatsapp").json()
    assert w["subject"] is None and "Royal Square" in w["body"] and len(w["body"]) < len(d["body"]) + 80


def test_an_ai_polished_draft_is_used_only_when_it_adds_no_new_figures(make_full_app):
    ok = json.dumps({"subject": "Quick check-in", "body": "Hi Thabo, I looked at your file and want to make sure your family is protected. 20 minutes this week?"})
    api = make_full_app(LLMRouter([FakeProvider(script=[ok])]))
    o = first(api, "under_insured_life", CLIENT_1)
    d = _draft(api, o).json()
    assert d["source"] == "ai" and d["body"].startswith("Hi Thabo, I looked")


def test_an_ai_draft_that_invents_a_number_is_discarded(make_full_app):
    bad = json.dumps({"subject": "Cover", "body": "Hi Thabo, you are short R9 999 999 of cover and it will cost R300 a month."})
    api = make_full_app(LLMRouter([FakeProvider(script=[bad])]))
    o = first(api, "under_insured_life", CLIENT_1)
    d = _draft(api, o).json()
    assert d["source"] == "template" and any("discarded" in w for w in d["warnings"])


def test_a_failing_model_falls_back_to_the_template_instead_of_an_error(make_full_app):
    api = make_full_app(LLMRouter([FakeProvider(script=[LLMError("unavailable", "boom")])], retry_delay_s=0))
    o = first(api, "under_insured_life", CLIENT_1)
    r = _draft(api, o)
    assert r.status_code == 200 and r.json()["source"] == "template" and r.json()["warnings"]


def test_drafting_is_adviser_only_and_audited_as_not_sent(fapi, fdb):
    o = first(fapi, "single_product")
    assert _draft(fapi, o, user=OWNER).status_code == 403 and _draft(fapi, o, user=CLIENT_3).status_code == 403
    _draft(fapi, o)
    (row,) = audit_rows(fdb, action="opportunity.draft_generated")
    assert "not sent" in row["summary"] and row["details"]["source"] == "template"
