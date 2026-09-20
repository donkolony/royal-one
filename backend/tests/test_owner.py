"""The owner's Business Health view: role gating, honest numbers, and the drill-down guarantee (brief section B)."""
import pytest

from app.services import health
from conftest import (ADVISER, ADVISER_2, CLIENT_1, CLIENT_2, CLIENT_3, CLIENT_4, CLIENT_5, CLIENT_8, CLIENT_9, CLIENT_10, CLIENT_11, CLIENT_12,
                      OWNER, audit_rows)


@pytest.fixture
def bh(fapi):
    r = fapi.get("/owner/business-health", user=OWNER)
    assert r.status_code == 200, r.text
    return r.json()


def drill(fapi, metric, **kw):
    from urllib.parse import quote
    return fapi.get(f"/owner/drilldown?metric={quote(metric)}&limit=100", user=OWNER, **kw).json()


def who(d):
    return {i["client"]["id"] for i in d["items"]}


# ------------------------------------------------------------------------------------------------- access
def test_only_the_owner_can_open_it(fapi):
    assert fapi.get("/owner/business-health", user=ADVISER).status_code == 403
    assert fapi.get("/owner/business-health", user=CLIENT_1).status_code == 403
    assert fapi.get("/owner/business-health").status_code == 401
    assert fapi.get("/owner/drilldown?metric=at_risk.all", user=ADVISER).status_code == 403


def test_an_unknown_drilldown_metric_is_a_validation_error(fapi):
    assert fapi.get("/owner/drilldown?metric=nonsense", user=OWNER).status_code == 422


# ------------------------------------------------------------------- the owner can name the top three things to act on
def test_three_ranked_actions_each_with_a_place_to_go(bh):
    acts = bh["top_actions"]
    assert len(acts) == 3 and all(a["title"] and a["path"] and a["count"] > 0 for a in acts)
    tiers = [a["tier"] for a in acts]
    assert tiers == sorted(tiers, reverse=True), "urgency tier first"
    assert "tier" in bh["top_actions_rule"].lower() or "urgency" in bh["top_actions_rule"].lower()


# ------------------------------------------------------------------------ every number drills down to its records
def test_every_tile_count_equals_the_rows_behind_it(fapi, bh):
    checks = [(bh["revenue_at_risk"]["clients"], bh["revenue_at_risk"]["drilldown"]),
              (bh["revenue_opportunity"]["open_count"], bh["revenue_opportunity"]["drilldown"]),
              (bh["retention"]["not_contacted"]["count"], bh["retention"]["not_contacted"]["drilldown"]),
              (bh["retention"]["reviews_overdue"]["count"], bh["retention"]["reviews_overdue"]["drilldown"]),
              (bh["retention"]["at_risk"]["count"], bh["retention"]["at_risk"]["drilldown"]),
              (bh["compliance"]["open_gaps"], bh["compliance"]["drilldown"])]
    checks += [(r["count"], r["drilldown"]) for r in bh["revenue_at_risk"]["reasons"]]
    checks += [(n, f"products.{b}") for b, n in bh["products_per_client"]["distribution"].items()]
    for count, metric in checks:
        assert drill(fapi, metric)["total"] == count, metric


def test_the_at_risk_rand_total_equals_the_sum_of_its_records(fapi, bh):
    d = drill(fapi, "at_risk.all")
    assert d["value_cents"] == bh["revenue_at_risk"]["total_cents"] > 0
    assert d["value_cents"] == sum(i["value_cents"] for i in d["items"])
    assert all(i["value_cents"] >= 0 and i["link"]["path"].startswith("/") for i in d["items"])
    assert sum(1 for i in d["items"] if i["value_cents"] > 0) >= 4, "clients with no premium on file are at risk but worth R0 to the estimate"


def test_the_open_opportunity_value_equals_the_records_and_the_radar(fapi, bh):
    d = drill(fapi, "opportunities.open")
    assert d["value_cents"] == bh["revenue_opportunity"]["open_value_cents"]
    assert d["total"] == fapi.get("/opportunities?status=live&limit=100", user=OWNER).json()["total"]


def test_drilldown_rows_are_paged(fapi):
    page = fapi.get("/owner/drilldown?metric=opportunities.open&limit=3&offset=2", user=OWNER).json()
    assert len(page["items"]) == 3 and page["offset"] == 2 and page["total"] > 5


# ---------------------------------------------------------------------------------- the facts behind each tile
def test_revenue_at_risk_reasons_match_the_seeded_situations(fapi):
    assert who(drill(fapi, "at_risk.lapsed")) == {str(CLIENT_9), str(CLIENT_12)}
    assert who(drill(fapi, "at_risk.review_overdue")) == {str(c) for c in (CLIENT_2, CLIENT_3, CLIENT_4, CLIENT_12)}
    assert who(drill(fapi, "at_risk.identity")) == {str(CLIENT_5), str(CLIENT_12)}
    stuck = drill(fapi, "at_risk.stale_claims")["items"]
    assert [i["client"]["id"] for i in stuck] == [str(CLIENT_3)] and stuck[0]["link"]["path"].startswith("/claims/")


def test_clients_with_several_reasons_are_counted_once(fapi, bh):
    at_risk = drill(fapi, "at_risk.all")
    assert len(who(at_risk)) == len(at_risk["items"])
    assert sum(r["count"] for r in bh["revenue_at_risk"]["reasons"]) > bh["revenue_at_risk"]["clients"]
    nomvula = next(i for i in at_risk["items"] if i["client"]["id"] == str(CLIENT_12))
    assert nomvula["detail"].count(";") >= 2


def test_retention_finds_the_client_nobody_has_contacted(fapi):
    silent = drill(fapi, "retention.not_contacted")
    zanele = next(i for i in silent["items"] if i["client"]["id"] == str(CLIENT_8))
    assert zanele["detail"] == "No contact on record"
    assert str(CLIENT_10) not in who(silent), "a client contacted 60 days ago is fine"


def test_products_per_client_average_and_distribution(fapi, bh):
    p = bh["products_per_client"]
    assert sum(p["distribution"].values()) == bh["clients"] == 12
    active = fapi.get("/policies?limit=100&status=active", user=OWNER).json()["total"]
    assert p["average"] == round(active / 12, 2)


def test_compliance_health_counts_the_three_checks(bh):
    c = bh["compliance"]
    assert c["components"]["identity"] == {"ok": 8, "total": 12, "percent": 66.7}
    assert c["components"]["advice"]["ok"] == 6 and c["components"]["consent"]["ok"] == 9
    assert c["score_percent"] == round((8 + 6 + 9) * 100 / 36, 1)
    kinds = {(g["client"]["full_name"], g["kind"]) for g in c["gaps"]}
    assert ("Zanele Mthembu", "consent") in kinds or c["open_gaps"] > len(c["gaps"])
    assert "fix_path" in c["gaps"][0] and c["definition"]


def test_an_expiring_id_is_a_flag_but_does_not_fail_the_identity_check(fapi):
    gaps = drill(fapi, "compliance.gaps")["items"]
    sipho = [g for g in gaps if g["client"]["id"] == str(CLIENT_5) and g["kind"] == "identity"]
    assert sipho and sipho[0]["detail"] == "Identity document expires soon" and sipho[0]["severity"] == "medium"
    assert sipho[0]["link"]["path"] == f"/clients/{CLIENT_5}?tab=compliance"


# -------------------------------------------------------------------------------------- honest labelling of numbers
def test_estimates_and_models_say_what_they_are(bh):
    assert bh["is_demo_estimate"] is True and "estimate" in bh["label"].lower()
    p = bh["productivity"]
    assert "ILLUSTRATIVE" in p["label"] and p["admin_tasks_automated"]["how"] and p["client_facing_share"]["how"]
    assert "commission" in bh["revenue_at_risk"]["formula"]
    assert bh["retention"]["at_risk"]["formula"].startswith("Health =")


def test_the_real_metrics_are_computed_from_data_not_invented(bh):
    p = bh["productivity"]
    assert {a["adviser"]["full_name"]: a["clients"] for a in p["clients_per_adviser"]} == {"Sarah van der Merwe": 9, "Priya Naidoo": 3}
    assert p["avg_claim_handling_days"] is None and "0 closed" in p["avg_claim_handling_basis"], "no claim is closed in the seed: say so, do not fake an average"
    assert p["open_claims_avg_age_days"] > 0
    share = p["client_facing_share"]
    assert 0 < share["percent"] < 100 and share["client_facing_minutes"] > 0 and share["manual_admin_minutes"] > 0


def test_closing_a_claim_produces_a_real_average(fapi, fdb):
    fdb.execute("update claims set status = 'closed', closed_at = submitted_at + interval '10 days' where reference is not null and status = 'assessment'")
    fdb.commit()
    p = fapi.get("/owner/business-health", user=OWNER).json()["productivity"]
    assert p["avg_claim_handling_days"] == 10.0 and "1 closed" in p["avg_claim_handling_basis"]


def test_winning_an_opportunity_moves_the_owners_numbers(fapi):
    before = fapi.get("/owner/business-health", user=OWNER).json()
    top = fapi.get("/opportunities?limit=1", user=ADVISER).json()["items"][0]
    fapi.post(f"/opportunities/{top['id']}/outcome", user=ADVISER, json={"outcome": "won", "reason": "Client agreed"})
    after = fapi.get("/owner/business-health", user=OWNER).json()
    assert after["revenue_opportunity"]["open_count"] == before["revenue_opportunity"]["open_count"] - 1
    assert after["revenue_opportunity"]["open_value_cents"] == before["revenue_opportunity"]["open_value_cents"] - top["est_annual_value_cents"]
    sarah = next(a for a in after["revenue_opportunity"]["by_adviser"] if a["adviser"]["full_name"] == "Sarah van der Merwe")
    assert sarah["won"] == 1 and sarah["conversion_rate"] == 1.0


def test_opening_the_health_view_and_a_drilldown_is_audited(fapi, fdb):
    fapi.get("/owner/business-health", user=OWNER)
    drill(fapi, "at_risk.all")
    assert len(audit_rows(fdb, action="owner.health_viewed")) == 1
    (row,) = audit_rows(fdb, action="owner.drilldown_viewed")
    assert row["details"]["metric"] == "at_risk.all"


# ---------------------------------------------------------------------------------------------- client health
def test_client_health_components_add_up_and_print_their_formula(fapi):
    h = fapi.get(f"/clients/{CLIENT_1}/health", user=ADVISER).json()
    assert h["score"] == round(sum(c["points"] for c in h["components"])) and sum(c["weight"] for c in h["components"]) == 100
    assert {c["key"] for c in h["components"]} == {"engagement", "review", "goals", "documents", "claims"}
    assert h["formula"].startswith("Health =") and h["band"] in ("healthy", "watch", "at_risk")


def test_a_client_nobody_has_contacted_and_with_no_identity_is_at_risk(fapi):
    h = fapi.get(f"/clients/{CLIENT_8}/health", user=ADVISER).json()
    parts = {c["key"]: c for c in h["components"]}
    assert h["band"] == "at_risk" and parts["engagement"]["value"] == 0 and parts["documents"]["value"] == 0
    assert h["weakest"] in ("Recent contact", "Documents valid")


def test_the_well_looked_after_client_is_healthy(fapi):
    assert fapi.get(f"/clients/{CLIENT_10}/health", user=ADVISER).json()["band"] == "healthy"


def test_client_health_respects_scope_and_role(fapi):
    assert fapi.get(f"/clients/{CLIENT_1}/health", user=ADVISER_2).status_code == 404
    assert fapi.get(f"/clients/{CLIENT_1}/health", user=CLIENT_1).status_code == 403
    assert fapi.get(f"/clients/{CLIENT_1}/health", user=OWNER).status_code == 200


def test_the_scale_function_is_a_straight_line_between_full_and_zero():
    assert health._scale(10, 30, 180) == 1.0 and health._scale(180, 30, 180) == 0.0 and health._scale(105, 30, 180) == 0.5
