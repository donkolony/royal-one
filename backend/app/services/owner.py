"""The owner's Business Health view (docs/AUDIT.md build step 3, brief section B).

Every tile answers "where is money made or lost?", and every number can be drilled into the records behind it: the tiles and
`drilldown()` read the same lists, so a count on the screen always equals the number of rows you land on.

Money is a DEMO ESTIMATE from radar_config.ASSUMPTIONS. Productivity figures are an ILLUSTRATIVE MODEL (tracked activity counts x
assumed minutes), not a stopwatch, and say so in the payload.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import psycopg

from app.core import clock
from app.core.auth import Principal
from app.core.db import fetch_all, fetch_one
from app.core.errors import validation
from app.core.http import Paging
from app.domain.radar_config import ASSUMPTIONS as A, DEMO_LABEL, SIGNALS
from app.services import audit, health, radar

REASONS = {
    "lapsed": ("Lapsed policies", "A policy with status 'lapsed': the cover has stopped."),
    "review_overdue": ("Reviews overdue", "No annual review in 12 months (or never, for a client of more than a year)."),
    "stale_claims": ("Claims stuck", f"An open claim has sat in one status for more than {A['stale_claim_days']} days."),
    "identity": ("Identity expiring", "The verified ID document has expired or expires within 30 days."),
}


def _annual(p: Dict[str, Any]) -> int:
    pr = p["premium_cents"] or 0
    return pr * 12 if p["premium_frequency"] == "monthly" else pr


def _commission(p: Dict[str, Any]) -> int:
    return round(_annual(p) * A["commission_rate"].get(p["category"], 0))


def _link(path: str) -> Dict[str, str]:
    return {"path": path}


class _Ctx:
    """Everything the tiles and the drill-downs need, loaded once."""

    def __init__(self, conn: psycopg.Connection, p: Principal):
        self.today = clock.today()
        self.ids = p.client_ids(conn)
        radar.refresh(conn, self.ids, self.today)
        rows = fetch_all(conn, "select c.id, pr.full_name, c.adviser_id, ap.full_name as adviser_name, c.last_annual_review_date, c.client_since "
                               "from clients c join profiles pr on pr.id = c.id join profiles ap on ap.id = c.adviser_id where c.id = any(%s) order by pr.full_name",
                         (self.ids,))
        self.clients = {r["id"]: r for r in rows}
        self.names = {cid: r["full_name"] for cid, r in self.clients.items()}
        self.policies = fetch_all(conn, "select client_id, category, status, premium_cents, premium_frequency, renewal_date from policies where client_id = any(%s)", (self.ids,))
        self.claims = fetch_all(
            conn, "select c.id, c.client_id, c.reference, c.status, c.status_changed_at, c.submitted_at, c.closed_at from claims c "
                  "where c.client_id = any(%s) and c.status <> 'draft'", (self.ids,))
        self.health = health.client_health(conn, self.ids, self.today)
        self.compliance = health.compliance_status(conn, self.ids, self.today)
        self.comp_summary = health.compliance_summary(conn, self.ids, self.names, self.today)
        self.opps = fetch_all(conn, radar._SELECT + " where o.client_id = any(%s) and o.status in ('open','actioned')", (self.ids,))

    def rec(self, cid: UUID, detail: str, value: Optional[int] = None, path: Optional[str] = None) -> Dict[str, Any]:
        c = self.clients[cid]
        return {"client": {"id": cid, "full_name": c["full_name"]}, "adviser": {"id": c["adviser_id"], "full_name": c["adviser_name"]},
                "detail": detail, "value_cents": value, "link": _link(path or f"/clients/{cid}")}

    def at_stake(self, cid: UUID) -> int:
        return sum(_commission(p) for p in self.policies if p["client_id"] == cid and p["status"] in ("active", "lapsed"))

    def annual_premium(self, cid: UUID) -> int:
        return sum(_annual(p) for p in self.policies if p["client_id"] == cid and p["status"] == "active")

    # ---- the record lists behind every tile
    def lists(self) -> Dict[str, List[Dict[str, Any]]]:
        t = self.today
        out: Dict[str, List[Dict[str, Any]]] = {}
        out["at_risk.lapsed"] = [
            self.rec(cid, f"{n} lapsed polic{'y' if n == 1 else 'ies'}: " + ", ".join(sorted({p['category'] for p in self.policies if p['client_id'] == cid and p['status'] == 'lapsed'})),
                     self.at_stake(cid))
            for cid, n in ((cid, sum(1 for p in self.policies if p["client_id"] == cid and p["status"] == "lapsed")) for cid in self.ids) if n]
        overdue = []
        for cid, c in self.clients.items():
            r, since = c["last_annual_review_date"], c["client_since"]
            if r is not None and (t - r).days >= A["review_interval_days"]:
                overdue.append(self.rec(cid, f"Last review {(t - r).days} days ago", self.at_stake(cid)))
            elif r is None and since and (t - since).days >= A["review_interval_days"]:
                overdue.append(self.rec(cid, "No review on record", self.at_stake(cid)))
        out["at_risk.review_overdue"] = overdue
        out["at_risk.stale_claims"] = [
            self.rec(c["client_id"], f"Claim {c['reference']} in '{c['status']}' for {(clock.now() - c['status_changed_at']).days} days",
                     self.at_stake(c["client_id"]), f"/claims/{c['id']}")
            for c in self.claims if c["status"] in ("registered", "assessment", "quotes", "authorised", "in_repair", "completed")
            and (clock.now() - c["status_changed_at"]).days >= A["stale_claim_days"]]
        out["at_risk.identity"] = [
            self.rec(cid, f"Identity {s['identity']['state']}" + (f" ({s['identity']['expiry_date']})" if s["identity"]["expiry_date"] else ""), self.at_stake(cid))
            for cid, s in self.compliance.items() if s["identity"]["state"] in ("expired", "expiring")]
        seen: Dict[UUID, List[str]] = {}
        for key in ("lapsed", "review_overdue", "stale_claims", "identity"):
            for r in out[f"at_risk.{key}"]:
                seen.setdefault(r["client"]["id"], []).append(REASONS[key][0])
        out["at_risk.all"] = [self.rec(cid, "; ".join(why), self.at_stake(cid)) for cid, why in seen.items()]
        out["opportunities.open"] = [
            {**self.rec(o["client_id"], o["title"], o["est_annual_value_cents"], f"/radar?client={o['client_id']}"), "signal": SIGNALS[o["signal"]]["label"]}
            for o in sorted(self.opps, key=lambda o: -o["est_annual_value_cents"])]
        limit = A["not_contacted_days"]
        out["retention.not_contacted"] = [
            self.rec(cid, "No contact on record" if h["days_since_contact"] is None else f"Last contact {h['days_since_contact']} days ago", self.at_stake(cid))
            for cid, h in self.health.items() if h["days_since_contact"] is None or h["days_since_contact"] > limit]
        out["retention.reviews_overdue"] = out["at_risk.review_overdue"]
        out["retention.at_risk"] = [self.rec(cid, f"Health {h['score']}/100, weakest: {h['weakest'].lower()}", self.at_stake(cid))
                                    for cid, h in sorted(self.health.items(), key=lambda kv: kv[1]["score"]) if h["band"] == "at_risk"]
        out["compliance.gaps"] = [{**self.rec(g["client"]["id"], g["label"], None, g["fix_path"]), "severity": g["severity"], "kind": g["kind"]}
                                  for g in self.comp_summary["gaps"]]
        counts = {cid: sum(1 for p in self.policies if p["client_id"] == cid and p["status"] == "active") for cid in self.ids}
        for bucket in ("0", "1", "2", "3", "4+"):
            out[f"products.{bucket}"] = [self.rec(cid, f"{n} active product(s)") for cid, n in counts.items()
                                         if (str(n) == bucket if bucket != "4+" else n >= 4)]
        return out


# ------------------------------------------------------------------------------------------------------- tiles
def _productivity(conn: psycopg.Connection, ctx: _Ctx) -> Dict[str, Any]:
    days = 30
    since = clock.now() - timedelta(days=days)
    acts = {(r["action"], r["actor_role"]): r["n"] for r in fetch_all(
        conn, "select action, actor_role, count(*) as n from audit_log where occurred_at >= %s group by 1, 2", (since,))}

    def n(prefix: str, role: Optional[str] = None, exclude: tuple = ()) -> int:
        return sum(v for (a, r), v in acts.items() if a.startswith(prefix) and a not in exclude and (role is None or r == role))

    m_auto, m_face, m_admin = A["minutes_per_admin_task"], A["minutes_per_client_facing_activity"], A["minutes_per_manual_admin_activity"]
    reminders_auto = fetch_one(conn, "select count(*) as n from reminders where source = 'rule' and created_at >= %s and client_id = any(%s)", (since, ctx.ids))["n"]
    advice = fetch_one(conn, "select count(*) as n from advice_records where created_at >= %s and client_id = any(%s)", (since, ctx.ids))["n"]
    automated = {
        "identity_reused": {"count": n("identity.reused"), "minutes_each": m_auto["identity_reused"]},
        "request_via_form": {"count": n("request.created", "client"), "minutes_each": m_auto["request_via_form"]},
        "status_update_propagated": {"count": n("claim.status_changed") + n("workflow.status_changed"), "minutes_each": m_auto["status_update_propagated"]},
        "reminder_auto_created": {"count": reminders_auto, "minutes_each": m_auto["reminder_auto_created"]},
    }
    for v in automated.values():
        v["minutes"] = v["count"] * v["minutes_each"]
    face = {"advice_records": advice, "outreach_logged": n("opportunity.outreach_logged"), "opportunities_won": n("opportunity.won")}
    face_min = advice * m_face["advice_record"] + face["outreach_logged"] * m_face["outreach_logged"] + face["opportunities_won"] * m_face["opportunity_won"]
    admin = {"claim_updates": n("claim.", "advisor", ("claim.viewed",)), "requests_handled": n("request.updated", "advisor"),
             "goal_or_reminder_edits": n("goal.", "advisor") + n("reminder.", "advisor")}
    admin_min = admin["claim_updates"] * m_admin["claim_update"] + admin["requests_handled"] * m_admin["request_handled"] + admin["goal_or_reminder_edits"] * m_admin["goal_or_reminder_edit"]
    closed = [c for c in ctx.claims if c["status"] == "closed" and c["closed_at"] and c["submitted_at"]]
    open_ = [c for c in ctx.claims if c["status"] != "closed" and c["submitted_at"]]
    completed_req = fetch_one(conn, "select count(*) as n from requests where status = 'completed' and completed_at >= %s and client_id = any(%s)", (since, ctx.ids))["n"]
    per_adviser: Dict[UUID, Dict[str, Any]] = {}
    for c in ctx.clients.values():
        per_adviser.setdefault(c["adviser_id"], {"adviser": {"id": c["adviser_id"], "full_name": c["adviser_name"]}, "clients": 0})["clients"] += 1
    return {
        "window_days": days, "label": "ILLUSTRATIVE MODEL: tracked activity x assumed minutes, not a stopwatch.",
        "clients_per_adviser": sorted(per_adviser.values(), key=lambda x: x["adviser"]["full_name"]),
        "avg_claim_handling_days": round(sum((c["closed_at"] - c["submitted_at"]).total_seconds() for c in closed) / len(closed) / 86400, 1) if closed else None,
        "avg_claim_handling_basis": f"Average of closed_at minus submitted_at over {len(closed)} closed claim(s).",
        "open_claims_avg_age_days": round(sum((clock.now() - c["submitted_at"]).total_seconds() for c in open_) / len(open_) / 86400, 1) if open_ else None,
        "workflows_completed": completed_req + sum(1 for c in closed if c["closed_at"] >= since),
        "admin_tasks_automated": {"items": automated, "count": sum(v["count"] for v in automated.values()), "minutes_avoided": sum(v["minutes"] for v in automated.values()),
                                  "how": "Count of each automated task in the last 30 days x assumed minutes an adviser would otherwise spend."},
        "client_facing_share": {
            "percent": round(face_min * 100 / (face_min + admin_min), 1) if (face_min + admin_min) else None,
            "client_facing_minutes": face_min, "manual_admin_minutes": admin_min, "client_facing": face, "manual_admin": admin,
            "how": "client-facing minutes / (client-facing + manual admin minutes), using the assumed minutes per logged activity in the last 30 days.",
        },
    }


def _top_actions(ctx: _Ctx, lists: Dict[str, List[Dict[str, Any]]], risk_total: int, opp_total: int) -> List[Dict[str, Any]]:
    """Ranking rule: urgency tier first (compliance and stuck claims = 3, money at risk and open opportunities = 2, retention = 1),
    then the estimated rand value. Deterministic and printed with the result."""
    acts: List[Dict[str, Any]] = []

    def add(key: str, title: str, detail: str, tier: int, value: int, path: str, count: int) -> None:
        if count:
            acts.append({"key": key, "title": title, "detail": detail, "tier": tier, "impact_cents": value, "count": count, "path": path})

    gaps = lists["compliance.gaps"]
    high = [g for g in gaps if g["severity"] == "high"]
    add("compliance", f"Close {len(gaps)} compliance gap(s)", f"{len(high)} are high severity: missing, expired or withdrawn.", 3, 0, "/compliance", len(gaps))
    stuck = lists["at_risk.stale_claims"]
    add("stale_claims", f"Unstick {len(stuck)} claim(s)", "Open claims that have not moved for over a week.", 3, sum(r["value_cents"] or 0 for r in stuck), "/drill/at_risk.stale_claims", len(stuck))
    add("at_risk", f"Protect {_rand(risk_total)} of revenue at risk", f"{len(lists['at_risk.all'])} client(s): lapsed cover, overdue reviews, stuck claims or expiring ID.", 2, risk_total, "/drill/at_risk.all", len(lists["at_risk.all"]))
    add("opportunities", f"Work {len(lists['opportunities.open'])} open opportunit{'y' if len(lists['opportunities.open']) == 1 else 'ies'}", f"Worth about {_rand(opp_total)} a year (demo estimate).", 2, opp_total, "/radar", len(lists["opportunities.open"]))
    add("not_contacted", f"Contact {len(lists['retention.not_contacted'])} client(s) not reached in {A['not_contacted_days']} days", "Silence is how clients drift away.", 1, sum(r["value_cents"] or 0 for r in lists["retention.not_contacted"]), "/drill/retention.not_contacted", len(lists["retention.not_contacted"]))
    acts.sort(key=lambda a: (-a["tier"], -a["impact_cents"]))
    return acts[:3]


def _rand(cents: int) -> str:
    return radar.rand(cents)


def business_health(conn: psycopg.Connection, p: Principal) -> Dict[str, Any]:
    ctx = _Ctx(conn, p)
    lists = ctx.lists()
    risk_total = sum(r["value_cents"] or 0 for r in lists["at_risk.all"])
    risk_premium = sum(ctx.annual_premium(r["client"]["id"]) for r in lists["at_risk.all"])
    opp = radar.summary(conn, p)
    opp_total = opp["totals"]["open_value_cents"]
    n_clients = len(ctx.ids)
    counts = {c: sum(1 for pl in ctx.policies if pl["client_id"] == c and pl["status"] == "active") for c in ctx.ids}
    dist = {b: len(lists[f"products.{b}"]) for b in ("0", "1", "2", "3", "4+")}
    audit.record_view(conn, p, "owner.health_viewed", "business_health", None, summary="Opened Business Health")
    return {
        "generated_at": clock.now(), "is_demo_estimate": True, "label": DEMO_LABEL, "clients": n_clients,
        "top_actions": _top_actions(ctx, lists, risk_total, opp_total),
        "top_actions_rule": "Urgency tier first (compliance and stuck claims, then money at risk and open opportunities, then retention), then estimated value.",
        "revenue_at_risk": {
            "total_cents": risk_total, "premium_cents": risk_premium, "clients": len(lists["at_risk.all"]), "drilldown": "at_risk.all",
            "formula": "For each at-risk client: sum of annual premium x assumed commission rate over their active and lapsed policies. Clients with several reasons count once.",
            "reasons": [{"key": k, "label": lab, "how": how, "count": len(lists[f"at_risk.{k}"]), "value_cents": sum(r["value_cents"] or 0 for r in lists[f"at_risk.{k}"]),
                         "drilldown": f"at_risk.{k}"} for k, (lab, how) in REASONS.items()],
        },
        "revenue_opportunity": {
            "open_value_cents": opp_total, "open_count": len(lists["opportunities.open"]), "drilldown": "opportunities.open",
            "by_adviser": [{"adviser": a["adviser"], "open": a["open"], "open_value_cents": a["open_value_cents"], "won": a["won"], "lost": a["lost"],
                            "actioned": a["actioned"], "surfaced": a["surfaced"], "conversion_rate": a["conversion_rate"]} for a in opp["by_adviser"]],
            "by_signal": [{"signal": s["signal"], "label": s["label"], "open": s["open"], "open_value_cents": s["open_value_cents"], "won": s["won"]} for s in opp["by_signal"]],
            "totals": opp["totals"], "definitions": opp["definitions"],
        },
        "productivity": _productivity(conn, ctx),
        "retention": {
            "not_contacted": {"days": A["not_contacted_days"], "count": len(lists["retention.not_contacted"]), "drilldown": "retention.not_contacted"},
            "reviews_overdue": {"count": len(lists["retention.reviews_overdue"]), "drilldown": "retention.reviews_overdue", "rule": f"No review in {A['review_interval_days']} days."},
            "at_risk": {"count": len(lists["retention.at_risk"]), "threshold": A["at_risk_health_below"], "drilldown": "retention.at_risk", "formula": health.HEALTH_FORMULA},
        },
        "products_per_client": {"average": round(sum(counts.values()) / n_clients, 2) if n_clients else None, "distribution": dist,
                                "drilldown_prefix": "products.", "how": "Active policies per client."},
        "compliance": {**{k: v for k, v in ctx.comp_summary.items() if k != "gaps"}, "open_gaps": len(ctx.comp_summary["gaps"]), "gaps": ctx.comp_summary["gaps"][:8], "drilldown": "compliance.gaps"},
    }


def drilldown(conn: psycopg.Connection, p: Principal, metric: str, paging: Paging) -> Dict[str, Any]:
    ctx = _Ctx(conn, p)
    lists = ctx.lists()
    if metric not in lists:
        raise validation("metric", "invalid_value", "Unknown metric. Use one of the drilldown keys returned by /owner/business-health.")
    rows = lists[metric]
    audit.record_view(conn, p, "owner.drilldown_viewed", "business_health", metric, summary=f"Opened the records behind '{metric}'", details={"metric": metric, "rows": len(rows)})
    return {"metric": metric, "total": len(rows), "limit": paging.limit, "offset": paging.offset, "items": rows[paging.offset: paging.offset + paging.limit],
            "value_cents": sum(r["value_cents"] or 0 for r in rows), "is_demo_estimate": True}


def client_health_for(conn: psycopg.Connection, p: Principal, client_id: UUID) -> Dict[str, Any]:
    from app.services.common import require_client_in_scope
    require_client_in_scope(conn, p, client_id)
    h = health.client_health(conn, [client_id], clock.today())[client_id]
    return {**h, "formula": health.HEALTH_FORMULA, "at_risk_below": A["at_risk_health_below"]}
