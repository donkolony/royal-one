"""Opportunity Radar (docs/AUDIT.md build step 2, brief section A).

Detection is RULES ON DATA: deterministic, explainable, testable without a model. Every opportunity carries the evidence
(the actual numbers and fields) that triggered it and a value formula that reads `radar_config.ASSUMPTIONS`. Those figures are
demo estimates and are labelled as such everywhere they are shown.

AI is used for exactly one thing: optionally polishing the wording of an outreach draft (`draft`). The draft is never sent and
never saved to a client record; the adviser edits it and logs the outreach themselves. If the model is unavailable or adds a
number that is not in the facts, the deterministic template is returned instead.

Like reminders, detection is computed on read (`refresh`) and is idempotent: `dedupe_key` makes the same fact surface once.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from app.core import clock
from app.core.auth import Principal
from app.core.db import Row, execute, fetch_all, fetch_one
from app.core.errors import ApiError, bad_state, forbidden, not_found, validation
from app.core.http import Paging
from app.domain.radar_config import ASSUMPTIONS as A, CATEGORY_LABELS, SIGNALS, public_assumptions
from app.llm.base import LLMRouter, Message
from app.services import audit
from app.services.common import require_client_in_scope

LIVE = ("open", "actioned")
CHANNELS = ("email", "whatsapp", "call", "meeting")


# ------------------------------------------------------------------------------------------------ small helpers
def rand(cents: int) -> str:
    """South African style: R1 250 000."""
    return "R" + f"{round(cents / 100):,}".replace(",", " ")


def _first(name: str) -> str:
    return (name or "").split()[0] if name else "there"


def _annual(policy: Row) -> Optional[int]:
    p = policy.get("premium_cents")
    if not p:
        return None
    return p * 12 if policy.get("premium_frequency") == "monthly" else p


def _age(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _value(category: str, premium_cents: int) -> Tuple[int, str]:
    rate = A["commission_rate"][category]
    return round(premium_cents * rate), f"{rand(premium_cents)} a year x {int(rate * 100)}% assumed commission"


@dataclass
class Candidate:
    signal: str
    client_id: UUID
    subject: str
    title: str
    why_now: str
    suggested_action: str
    talking_points: List[str]
    evidence: Dict[str, Any]
    period: str = ""
    touchpoint: bool = False
    premium: int = 0
    value: int = 0
    formula: str = ""

    @property
    def dedupe_key(self) -> str:
        return f"{self.signal}:{self.client_id}:{self.subject}:{self.period}"


# ----------------------------------------------------------------------------------------------- the seven rules
def _under_insured(f: Dict[str, Any], today: date) -> List[Candidate]:
    income = f["income"]
    if not income:
        return []          # no income on file: the rule does not guess
    liabilities = sum(i["amount_cents"] for i in f["items"] if i["kind"] == "liability")
    need = liabilities + A["life_income_multiple"] * income
    existing = sum((p["cover_amount_cents"] or 0) for p in f["policies"] if p["category"] == "life" and p["status"] == "active")
    gap = need - existing
    if gap < A["life_min_gap_cents"] or gap / need < A["life_min_gap_ratio"]:
        return []
    premium = round(gap / 100_000_000 * A["life_premium_per_r1m_annual_cents"])
    value, formula = _value("life", premium)
    formula = f"gap {rand(gap)} / R1m x {rand(A['life_premium_per_r1m_annual_cents'])} = {rand(premium)} a year; {formula}"
    return [Candidate(
        "under_insured_life", f["id"], "life", f"Life cover looks {rand(gap)} short",
        f"Existing life cover is {rand(existing)} against an estimated need of {rand(need)}.",
        f"Book a needs-analysis review and discuss additional life cover of about {rand(gap)}.",
        [f"Liabilities on file: {rand(liabilities)}", f"Annual income on file: {rand(income)} (x{A['life_income_multiple']} = {rand(A['life_income_multiple'] * income)})",
         f"Existing life cover: {rand(existing)}", f"Dependants: {f['dependants'] if f['dependants'] is not None else 'not recorded'}"],
        {"annual_income_cents": income, "total_liabilities_cents": liabilities, "income_multiple": A["life_income_multiple"],
         "estimated_need_cents": need, "existing_life_cover_cents": existing, "gap_cents": gap, "dependants": f["dependants"]},
        premium=premium, value=value, formula=formula)]


def _goals_behind(f: Dict[str, Any], today: date) -> List[Candidate]:
    out = []
    for g in f["goals"]:
        if g["status"] != "active" or not g["target_date"]:
            continue
        start = g["created_at"].astimezone(clock.SAST).date()
        total = (g["target_date"] - start).days
        left_days = (g["target_date"] - today).days
        if total < A["goal_min_days"] or left_days <= 0:
            continue
        expected = min(100.0, max(0.0, (today - start).days / total * 100))
        actual = min(100.0, g["current_amount_cents"] * 100 / g["target_amount_cents"])
        if actual + A["goal_behind_tolerance_pct"] >= expected:
            continue
        months = max(1, round(left_days / 30.4))
        remaining = g["target_amount_cents"] - g["current_amount_cents"]
        monthly = round(remaining / months)
        premium = monthly * 12
        value, formula = _value("investment", premium)
        formula = f"needs {rand(monthly)} a month over {months} months = {rand(premium)} a year; {formula}"
        out.append(Candidate(
            "goal_behind", f["id"], str(g["id"]), f"'{g['title']}' is behind schedule",
            f"{actual:.0f}% saved against {expected:.0f}% expected by now, with {months} months left.",
            f"Review contributions towards '{g['title']}' and agree a monthly amount of about {rand(monthly)}.",
            [f"Saved {rand(g['current_amount_cents'])} of {rand(g['target_amount_cents'])} ({actual:.0f}%)",
             f"Straight-line expectation today: {expected:.0f}%", f"Needed from here: {rand(monthly)} a month for {months} months"],
            {"goal_id": str(g["id"]), "goal_title": g["title"], "target_cents": g["target_amount_cents"], "current_cents": g["current_amount_cents"],
             "progress_percent": round(actual, 1), "expected_percent": round(expected, 1), "months_left": months, "required_monthly_cents": monthly,
             "target_date": g["target_date"]},
            premium=premium, value=value, formula=formula))
    return out


_EVENT_TEXT = {
    "new_baby": ("New baby", "life", "review life, funeral and education cover"),
    "marriage": ("Marriage", "life", "update beneficiaries and review joint cover"),
    "new_vehicle": ("New vehicle", "motor", "confirm the new vehicle is insured"),
    "property_purchase": ("Property purchase", "personal_other", "arrange home cover and protect the bond"),
    "divorce": ("Divorce", None, "update beneficiaries and review cover"),
    "job_change": ("Job change", "disability", "review income protection and retirement contributions"),
}


def _life_events(f: Dict[str, Any], today: date) -> List[Candidate]:
    out = []
    for e in f["events"]:
        age_days = (today - e["occurred_on"]).days
        if not 0 <= age_days <= A["life_event_window_days"]:
            continue
        label, cat, action = _EVENT_TEXT[e["kind"]]
        premium, value, formula = 0, 0, "touchpoint: no sale estimated"
        if cat:
            premium = A["avg_annual_premium_cents"][cat]
            value, f2 = _value(cat, premium)
            formula = f"assumed {rand(premium)} a year for {CATEGORY_LABELS[cat]}; {f2}"
        out.append(Candidate(
            "life_event", f["id"], f"event-{e['id']}", f"{label}: a natural time to talk",
            f"{label} recorded {age_days} day(s) ago" + (f" ({e['note']})" if e.get("note") else "") + ".",
            f"Call and {action}.", [f"{label} on {e['occurred_on']}", f"Suggested: {action}"],
            {"event_id": str(e["id"]), "kind": e["kind"], "occurred_on": e["occurred_on"], "days_ago": age_days},
            touchpoint=cat is None, premium=premium, value=value, formula=formula))
    if f["dob"]:
        age = _age(f["dob"], today)
        if A["retirement_age"] - A["retirement_window_years"] <= age <= A["retirement_age"]:
            premium = A["avg_annual_premium_cents"]["retirement"]
            value, f2 = _value("retirement", premium)
            out.append(Candidate(
                "life_event", f["id"], "retirement", "Retirement is approaching",
                f"Age {age}; assumed retirement age {A['retirement_age']}.",
                "Review the retirement plan, contributions and the gap to the retirement goal.",
                [f"Age {age}, planning age {A['retirement_age']}"], {"kind": "retirement_approaching", "age": age, "retirement_age": A["retirement_age"]},
                period=str(f["dob"].year + A["retirement_age"]), premium=premium, value=value,
                formula=f"assumed {rand(premium)} a year contribution; {f2}"))
    for p in f["policies"]:
        r = p["renewal_date"]
        if p["status"] == "active" and r and -7 <= (r - today).days <= A["renewal_window_days"]:
            out.append(Candidate(
                "life_event", f["id"], f"renewal-{p['id']}", f"{p['product_name']} renews on {r}",
                f"Renewal in {(r - today).days} day(s).", "Use the renewal as a reason to review the whole portfolio.",
                [f"{p['product_name']} ({p['category']}) renews {r}"], {"kind": "renewal", "policy_id": str(p["id"]), "renewal_date": r},
                period=r.isoformat(), touchpoint=True, formula="touchpoint: no sale estimated"))
    return out


def _missing_cover(f: Dict[str, Any], today: date, active_cats: set) -> List[Candidate]:
    items, out = f["items"], []
    vehicle = any(i["category"] in ("vehicle", "vehicle_finance") for i in items)
    home = any(i["category"] in ("property", "home_loan") for i in items)
    rules = [
        ("motor", vehicle, "a vehicle (or vehicle finance) is on the balance sheet"),
        ("personal_other", home, "a property (or home loan) is on the balance sheet"),
        ("funeral", (f["dependants"] or 0) >= 1, f"{f['dependants']} dependant(s) on file"),
        ("disability", bool(f["income"]), "there is an income to protect"),
    ]
    for cat, applies, why in rules:
        if not applies or cat in active_cats:
            continue
        premium = A["avg_annual_premium_cents"][cat]
        value, formula = _value(cat, premium)
        out.append(Candidate(
            "missing_cover", f["id"], cat, f"No active {CATEGORY_LABELS[cat]}",
            f"{why[0].upper() + why[1:]}, but there is no active {CATEGORY_LABELS[cat]} policy.",
            f"Ask about {CATEGORY_LABELS[cat]} and quote it.", [f"Reason: {why}", f"Active categories: {', '.join(sorted(active_cats)) or 'none'}"],
            {"category": cat, "reason": why, "active_categories": sorted(active_cats)},
            premium=premium, value=value, formula=f"assumed {rand(premium)} a year; {formula}"))
    return out


def _lapsed(f: Dict[str, Any], today: date) -> List[Candidate]:
    out = []
    for p in f["policies"]:
        if p["status"] != "lapsed":
            continue
        premium = _annual(p) or A["avg_annual_premium_cents"].get(p["category"], 0)
        value, formula = _value(p["category"], premium)
        out.append(Candidate(
            "lapsed_cover", f["id"], str(p["id"]), f"{p['product_name']} has lapsed",
            f"The {CATEGORY_LABELS.get(p['category'], p['category'])} policy {p['policy_number']} is lapsed, so the client is unprotected.",
            "Call to understand why it lapsed and offer to reinstate or replace it.",
            [f"{p['product_name']} ({p['policy_number']}) is lapsed", "Check whether a missed debit order or a cost concern caused it"],
            {"policy_id": str(p["id"]), "policy_number": p["policy_number"], "category": p["category"], "annual_premium_cents": premium},
            premium=premium, value=value, formula=formula))
    return out


def _single_product(f: Dict[str, Any], today: date, active: List[Row], active_cats: set) -> List[Candidate]:
    since = f["client_since"]
    if len(active) != 1 or not since or (today - since).days < A["single_product_min_tenure_days"]:
        return []
    only = active[0]
    for cat in ("life", "funeral", "personal_other", "disability"):
        if cat not in active_cats:
            break
    else:
        return []
    premium = A["avg_annual_premium_cents"][cat]
    value, formula = _value(cat, premium)
    return [Candidate(
        "single_product", f["id"], "cross-sell", "Only one product with us",
        f"{_first(f['name'])} has held only '{only['product_name']}' for {(today - since).days // 365} year(s).",
        f"Review the whole picture and introduce {CATEGORY_LABELS[cat]}.", [f"Only active policy: {only['product_name']} ({only['category']})",
                                                                            f"Suggested next: {CATEGORY_LABELS[cat]}"],
        {"active_policies": 1, "only_policy": only["product_name"], "suggested_category": cat, "client_since": since},
        premium=premium, value=value, formula=f"assumed {rand(premium)} a year; {formula}")]


def _expiring_licence(f: Dict[str, Any], today: date) -> List[Candidate]:
    d = f["licence_expiry"]
    if not d or not -30 <= (d - today).days <= A["document_expiry_window_days"]:
        return []
    days = (d - today).days
    state = f"expires in {days} day(s)" if days >= 0 else f"expired {-days} day(s) ago"
    return [Candidate(
        "expiring_document", f["id"], "drivers_licence", "Driver's licence " + ("expiring soon" if days >= 0 else "has expired"),
        f"The driver's licence on file {state} ({d}).", "Ask for the renewed licence and use the call to check the motor cover.",
        [f"Licence expiry on file: {d}", "A valid licence is needed for a motor claim"], {"document": "drivers_licence", "expiry_date": d, "days_left": days},
        period=d.isoformat(), touchpoint=True, formula="touchpoint: no sale estimated")]


def _expiring_identity(f: Dict[str, Any], today: date) -> List[Candidate]:
    out = []
    for d in f.get("idocs", []):
        if d["doc_type"] != "id_document":
            continue
        days = (d["expiry_date"] - today).days
        if not -30 <= days <= A["document_expiry_window_days"]:
            continue
        state = f"expires in {days} day(s)" if days >= 0 else f"expired {-days} day(s) ago"
        out.append(Candidate(
            "expiring_document", f["id"], "id_document", "ID document " + ("expiring soon" if days >= 0 else "has expired"),
            f"The verified ID on file {state} ({d['expiry_date']}).", "Ask for the renewed ID and re-verify it, so claims and applications stay smooth.",
            [f"ID expiry on file: {d['expiry_date']}", "A valid ID is reused in claims and applications, so an expired one causes friction"],
            {"document": "id_document", "expiry_date": d["expiry_date"], "days_left": days}, period=d["expiry_date"].isoformat(),
            touchpoint=True, formula="touchpoint: no sale estimated"))
    return out


def detect(f: Dict[str, Any], today: date) -> List[Candidate]:
    """All opportunities for one client's facts. Pure: no database, no clock, no model."""
    active = [p for p in f["policies"] if p["status"] == "active"]
    active_cats = {p["category"] for p in active}
    out = _under_insured(f, today) + _goals_behind(f, today) + _life_events(f, today)
    lapsed_cats = {p["category"] for p in f["policies"] if p["status"] == "lapsed"}
    out += _missing_cover(f, today, active_cats | lapsed_cats) + _lapsed(f, today)
    if not [c for c in out if not c.touchpoint]:
        out += _single_product(f, today, active, active_cats)
    out += _expiring_licence(f, today) + _expiring_identity(f, today)
    return out


# ------------------------------------------------------------------------------------------- loading and refreshing
def load_facts(conn: psycopg.Connection, client_ids: List[UUID]) -> List[Dict[str, Any]]:
    if not client_ids:
        return []
    clients = fetch_all(
        conn,
        "select c.id, p.full_name, c.adviser_id, c.date_of_birth, c.client_since, c.drivers_licence_expiry, c.dependants, c.annual_income_cents "
        "from clients c join profiles p on p.id = c.id where c.id = any(%s)", (client_ids,))
    pols = fetch_all(conn, "select id, client_id, category, product_name, policy_number, status, cover_amount_cents, premium_cents, premium_frequency, "
                           "renewal_date from policies where client_id = any(%s)", (client_ids,))
    items = fetch_all(conn, "select client_id, kind, category, amount_cents from financial_items where client_id = any(%s)", (client_ids,))
    goals = fetch_all(conn, "select gp.client_id, g.* from goals g join goal_participants gp on gp.goal_id = g.id where gp.client_id = any(%s)", (client_ids,))
    events = fetch_all(conn, "select id, client_id, kind, occurred_on, note from life_events where client_id = any(%s)", (client_ids,))
    idocs = fetch_all(conn, "select client_id, doc_type, expiry_date from identity_documents where client_id = any(%s) and status = 'verified' and expiry_date is not null", (client_ids,))
    out = []
    for c in clients:
        cid = c["id"]
        out.append({
            "id": cid, "name": c["full_name"], "adviser_id": c["adviser_id"], "dob": c["date_of_birth"], "client_since": c["client_since"],
            "licence_expiry": c["drivers_licence_expiry"], "dependants": c["dependants"], "income": c["annual_income_cents"],
            "policies": [p for p in pols if p["client_id"] == cid], "items": [i for i in items if i["client_id"] == cid],
            "goals": [g for g in goals if g["client_id"] == cid], "events": [e for e in events if e["client_id"] == cid],
            "idocs": [d for d in idocs if d["client_id"] == cid],
        })
    return out


def _event(conn: psycopg.Connection, opp_id: UUID, kind: str, actor: Optional[Principal], note: Optional[str] = None, channel: Optional[str] = None) -> None:
    execute(conn, "insert into opportunity_events (opportunity_id, kind, actor_id, channel, note) values (%s,%s,%s,%s,%s)",
            (opp_id, kind, actor.id if actor else None, channel, note))


def refresh(conn: psycopg.Connection, client_ids: List[UUID], today: Optional[date] = None) -> Dict[str, int]:
    """Bring `opportunities` in line with the data. Idempotent and cheap enough to run on every read."""
    today = today or clock.today()
    if not client_ids:
        return {"created": 0, "updated": 0, "expired": 0}
    found: Dict[str, Candidate] = {}
    for facts in load_facts(conn, client_ids):
        for c in detect(facts, today):
            found[c.dedupe_key] = c
    existing = {r["dedupe_key"]: r for r in fetch_all(
        conn, "select id, dedupe_key, status, snoozed_until from opportunities where client_id = any(%s)", (client_ids,))}
    created = updated = expired = 0
    for key, c in found.items():
        row = existing.get(key)
        cols = (c.title, c.why_now, c.suggested_action, Jsonb(c.talking_points), Jsonb(c.evidence, dumps=_dumps), c.touchpoint, c.premium, c.value, c.formula)
        if row is None:
            new = fetch_one(
                conn,
                "insert into opportunities (client_id, signal, dedupe_key, title, why_now, suggested_action, talking_points, evidence, is_touchpoint, "
                "est_annual_premium_cents, est_annual_value_cents, value_formula) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "on conflict (dedupe_key) do nothing returning id", (c.client_id, c.signal, key) + cols)
            if new:
                _event(conn, new["id"], "surfaced", None)
                created += 1
        elif row["status"] in ("open", "snoozed", "actioned"):
            unsnooze = row["status"] == "snoozed" and row["snoozed_until"] and row["snoozed_until"] <= today
            execute(conn, "update opportunities set title=%s, why_now=%s, suggested_action=%s, talking_points=%s, evidence=%s, is_touchpoint=%s, "
                          "est_annual_premium_cents=%s, est_annual_value_cents=%s, value_formula=%s, last_seen_at=now(), "
                          "status = case when %s then 'open' else status end, updated_at = now() where id=%s", cols + (unsnooze, row["id"]))
            if unsnooze:
                _event(conn, row["id"], "unsnoozed", None)
            updated += 1
    for key, row in existing.items():
        if key not in found and row["status"] in ("open", "snoozed"):
            execute(conn, "update opportunities set status='expired', closed_at=now(), updated_at=now() where id=%s", (row["id"],))
            _event(conn, row["id"], "expired", None, "The condition that surfaced it is no longer true.")
            expired += 1
    return {"created": created, "updated": updated, "expired": expired}


def _dumps(o: Any) -> str:
    return json.dumps(o, default=str)


# --------------------------------------------------------------------------------------------------- reading
_SELECT = """
select o.*, cp.full_name as client_name, c.adviser_id, ap.full_name as adviser_name
from opportunities o
join clients c on c.id = o.client_id
join profiles cp on cp.id = o.client_id
join profiles ap on ap.id = c.adviser_id
"""


def opportunity_object(r: Row, events: Optional[List[Row]] = None) -> Dict[str, Any]:
    out = {
        "id": r["id"], "client": {"id": r["client_id"], "full_name": r["client_name"]},
        "adviser": {"id": r["adviser_id"], "full_name": r["adviser_name"]},
        "signal": r["signal"], "signal_label": SIGNALS[r["signal"]]["label"], "title": r["title"], "why_now": r["why_now"],
        "suggested_action": r["suggested_action"], "talking_points": r["talking_points"], "evidence": r["evidence"],
        "is_touchpoint": r["is_touchpoint"], "est_annual_premium_cents": r["est_annual_premium_cents"],
        "est_annual_value_cents": r["est_annual_value_cents"], "value_formula": r["value_formula"], "is_demo_estimate": True,
        "status": r["status"], "snoozed_until": r["snoozed_until"], "outcome_reason": r["outcome_reason"],
        "won_value_cents": r["won_value_cents"], "task_reminder_id": r["task_reminder_id"], "surfaced_at": r["surfaced_at"],
        "actioned_at": r["actioned_at"], "closed_at": r["closed_at"],
    }
    if events is not None:
        out["events"] = [{"id": e["id"], "kind": e["kind"], "actor": {"id": e["actor_id"], "full_name": e.get("actor_name")} if e["actor_id"] else None,
                          "channel": e["channel"], "note": e["note"], "created_at": e["created_at"]} for e in events]
    return out


def _load(conn: psycopg.Connection, p: Principal, opp_id: UUID, lock: bool = False) -> Row:
    row = fetch_one(conn, f"{_SELECT} where o.id = %s and o.client_id = any(%s)" + (" for update of o" if lock else ""), (opp_id, p.client_ids(conn)))
    if row is None:
        raise not_found("Opportunity")
    return row


def list_opportunities(
    conn: psycopg.Connection, p: Principal, paging: Paging, *, status: str, signal: Optional[str], client_id: Optional[UUID],
    adviser_id: Optional[UUID], sort: str,
) -> Dict[str, Any]:
    ids = p.client_ids(conn)
    if client_id is not None:
        require_client_in_scope(conn, p, client_id)
        ids = [client_id]
    refresh(conn, ids)
    where, params = ["o.client_id = any(%s)"], [ids]
    if status == "live":
        where.append("o.status = any(%s)")
        params.append(list(LIVE))
    elif status != "all":
        where.append("o.status = %s")
        params.append(status)
    if signal:
        if signal not in SIGNALS:
            raise validation("signal", "invalid_value", f"signal must be one of: {', '.join(SIGNALS)}.")
        where.append("o.signal = %s")
        params.append(signal)
    if adviser_id:
        where.append("c.adviser_id = %s")
        params.append(adviser_id)
    order = "o.surfaced_at desc" if sort == "surfaced" else "o.est_annual_value_cents desc, o.surfaced_at desc"
    clause = " and ".join(where)
    total = fetch_one(conn, f"select count(*) as n from opportunities o join clients c on c.id = o.client_id where {clause}", params)["n"]
    rows = fetch_all(conn, f"{_SELECT} where {clause} order by {order}, o.id limit %s offset %s", params + [paging.limit, paging.offset])
    return paging.envelope([opportunity_object(r) for r in rows], total)


def get_opportunity(conn: psycopg.Connection, p: Principal, opp_id: UUID) -> Dict[str, Any]:
    row = _load(conn, p, opp_id)
    refresh(conn, [row["client_id"]])        # the card must show today's evidence, not the evidence from the last list read
    row = _load(conn, p, opp_id)
    events = fetch_all(conn, "select e.*, a.full_name as actor_name from opportunity_events e left join profiles a on a.id = e.actor_id "
                             "where e.opportunity_id = %s order by e.created_at, e.id", (opp_id,))
    audit.record_view(conn, p, "opportunity.viewed", "opportunity", opp_id, client_id=row["client_id"], summary=f"Opened the opportunity '{row['title']}'")
    return opportunity_object(row, events)


def summary(conn: psycopg.Connection, p: Principal) -> Dict[str, Any]:
    """The owner's conversion metrics. Definitions are part of the payload so the UI can print them."""
    ids = p.client_ids(conn)
    refresh(conn, ids)
    rows = fetch_all(conn, f"{_SELECT} where o.client_id = any(%s)", (ids,))

    def block(rs: List[Row]) -> Dict[str, Any]:
        won, lost = [r for r in rs if r["status"] == "won"], [r for r in rs if r["status"] == "lost"]
        live = [r for r in rs if r["status"] in LIVE]
        decided = len(won) + len(lost)
        return {
            "surfaced": len(rs), "open": len([r for r in rs if r["status"] == "open"]), "snoozed": len([r for r in rs if r["status"] == "snoozed"]),
            "actioned": len([r for r in rs if r["actioned_at"]]), "won": len(won), "lost": len(lost),
            "expired": len([r for r in rs if r["status"] == "expired"]),
            "open_value_cents": sum(r["est_annual_value_cents"] for r in live), "won_value_cents": sum(r["won_value_cents"] or 0 for r in won),
            "conversion_rate": round(len(won) / decided, 3) if decided else None,
        }

    by_signal = []
    for sig, meta in SIGNALS.items():
        b = block([r for r in rows if r["signal"] == sig])
        by_signal.append({"signal": sig, "label": meta["label"], **b})
    advisers = (fetch_all(conn, "select id, full_name from profiles where role = 'advisor'") if p.is_owner
                else [{"id": p.id, "full_name": p.full_name}])
    by_adviser = sorted(
        ({"adviser": {"id": a["id"], "full_name": a["full_name"]}, **block([r for r in rows if r["adviser_id"] == a["id"]])} for a in advisers),
        key=lambda x: -x["open_value_cents"])
    return {
        "totals": block(rows), "by_signal": by_signal, "by_adviser": by_adviser,
        "definitions": {
            "surfaced": "Every opportunity a rule has detected, ever.", "actioned": "A task was created or outreach was logged.",
            "won / lost": "An adviser recorded the outcome with a reason.", "conversion": "won / (won + lost).",
            "open value": "Sum of the demo-estimated annual value of live opportunities: open or actioned; snoozed ones are parked (touchpoints count as R0).",
        },
        "assumptions": public_assumptions(),
    }


def assumptions() -> Dict[str, Any]:
    return public_assumptions()


# -------------------------------------------------------------------------------------------------- lifecycle
def _require_adviser_of(conn: psycopg.Connection, p: Principal, opp_id: UUID) -> Row:
    if not p.is_advisor:
        raise forbidden("Only the client's adviser can act on an opportunity. The owner has a read-only view.")
    return _load(conn, p, opp_id, lock=True)


def _mark_actioned(conn: psycopg.Connection, row: Row) -> None:
    execute(conn, "update opportunities set status = case when status in ('open','snoozed') then 'actioned' else status end, "
                  "actioned_at = coalesce(actioned_at, now()), updated_at = now() where id = %s", (row["id"],))


def _require_live(row: Row) -> None:
    if row["status"] not in ("open", "snoozed", "actioned"):
        raise bad_state(f"This opportunity is already {row['status']}.")


def create_task(conn: psycopg.Connection, p: Principal, opp_id: UUID) -> Dict[str, Any]:
    row = _require_adviser_of(conn, p, opp_id)
    _require_live(row)
    if row["task_reminder_id"]:
        raise bad_state("A task already exists for this opportunity.")
    due = clock.today() + timedelta(days=A["task_due_days"])
    rem = fetch_one(
        conn,
        "insert into reminders (client_id, type, title, description, due_date, audience, source, related_resource, related_id, created_by) "
        "values (%s,'custom',%s,%s,%s,'advisor','manual','opportunity',%s,%s) returning id",
        (row["client_id"], f"Follow up: {row['title']}", row["suggested_action"], due, row["id"], p.id))
    execute(conn, "update opportunities set task_reminder_id = %s where id = %s", (rem["id"], opp_id))
    _mark_actioned(conn, row)
    _event(conn, opp_id, "task_created", p)
    audit.record(conn, p, "opportunity.task_created", "opportunity", opp_id, client_id=row["client_id"],
                 summary=f"Created a follow-up task for '{row['title']}'", details={"reminder_id": rem["id"], "due_date": due})
    return get_opportunity(conn, p, opp_id)


def log_outreach(conn: psycopg.Connection, p: Principal, opp_id: UUID, channel: str, note: Optional[str]) -> Dict[str, Any]:
    row = _require_adviser_of(conn, p, opp_id)
    _require_live(row)
    _mark_actioned(conn, row)
    _event(conn, opp_id, "outreach_logged", p, note, channel)
    audit.record(conn, p, "opportunity.outreach_logged", "opportunity", opp_id, client_id=row["client_id"],
                 summary=f"Logged {channel} outreach for '{row['title']}'", details={"channel": channel})
    return get_opportunity(conn, p, opp_id)


def snooze(conn: psycopg.Connection, p: Principal, opp_id: UUID, days: int) -> Dict[str, Any]:
    row = _require_adviser_of(conn, p, opp_id)
    if row["status"] not in ("open", "snoozed"):
        raise bad_state(f"A {row['status']} opportunity cannot be snoozed.")
    until = clock.today() + timedelta(days=days)
    execute(conn, "update opportunities set status='snoozed', snoozed_until=%s, updated_at=now() where id=%s", (until, opp_id))
    _event(conn, opp_id, "snoozed", p, f"Until {until}")
    audit.record(conn, p, "opportunity.snoozed", "opportunity", opp_id, client_id=row["client_id"],
                 summary=f"Snoozed '{row['title']}' for {days} day(s)", details={"until": until})
    return get_opportunity(conn, p, opp_id)


def record_outcome(conn: psycopg.Connection, p: Principal, opp_id: UUID, outcome: str, reason: str, actual_value_cents: Optional[int]) -> Dict[str, Any]:
    row = _require_adviser_of(conn, p, opp_id)
    _require_live(row)
    won_value = None
    if outcome == "won":
        won_value = actual_value_cents if actual_value_cents is not None else row["est_annual_value_cents"]
    execute(conn, "update opportunities set status=%s, outcome_reason=%s, won_value_cents=%s, closed_at=now(), closed_by=%s, "
                  "actioned_at=coalesce(actioned_at, now()), updated_at=now() where id=%s", (outcome, reason, won_value, p.id, opp_id))
    _event(conn, opp_id, outcome, p, reason)
    audit.record(conn, p, f"opportunity.{outcome}", "opportunity", opp_id, client_id=row["client_id"],
                 summary=f"Marked '{row['title']}' as {outcome}", details={"reason": reason, "won_value_cents": won_value})
    return get_opportunity(conn, p, opp_id)


def reopen(conn: psycopg.Connection, p: Principal, opp_id: UUID) -> Dict[str, Any]:
    row = _require_adviser_of(conn, p, opp_id)
    if row["status"] not in ("lost", "expired", "snoozed"):
        raise bad_state("Only a lost, expired or snoozed opportunity can be reopened. A won one is part of the results and stays.")
    execute(conn, "update opportunities set status='open', snoozed_until=null, closed_at=null, closed_by=null, outcome_reason=null, updated_at=now() where id=%s", (opp_id,))
    _event(conn, opp_id, "reopened", p)
    audit.record(conn, p, "opportunity.reopened", "opportunity", opp_id, client_id=row["client_id"], summary=f"Reopened '{row['title']}'")
    return get_opportunity(conn, p, opp_id)


# ------------------------------------------------------------------------------------------------- life events
def record_life_event(conn: psycopg.Connection, p: Principal, client_id: UUID, kind: str, occurred_on: date, note: Optional[str]) -> Dict[str, Any]:
    if not p.is_advisor:
        raise forbidden("Only the client's adviser can record a life event.")
    require_client_in_scope(conn, p, client_id)
    if occurred_on > clock.today():
        raise validation("occurred_on", "invalid_date", "A life event cannot be in the future.")
    row = fetch_one(conn, "insert into life_events (client_id, kind, occurred_on, note, recorded_by) values (%s,%s,%s,%s,%s) returning *",
                    (client_id, kind, occurred_on, note, p.id))
    audit.record(conn, p, "life_event.recorded", "life_event", row["id"], client_id=client_id,
                 summary=f"Recorded a life event: {_EVENT_TEXT[kind][0]}", details={"kind": kind, "occurred_on": occurred_on})
    return {k: row[k] for k in ("id", "client_id", "kind", "occurred_on", "note", "created_at")}


def list_life_events(conn: psycopg.Connection, p: Principal, client_id: UUID) -> Dict[str, Any]:
    require_client_in_scope(conn, p, client_id)
    rows = fetch_all(conn, "select id, client_id, kind, occurred_on, note, created_at from life_events where client_id = %s order by occurred_on desc", (client_id,))
    return {"items": rows}


# --------------------------------------------------------------------------------------------- outreach drafts
def _outreach_line(signal: str, ev: Dict[str, Any], title: str) -> str:
    """Client-safe wording: says what we noticed, never the internal calculation."""
    if signal == "under_insured_life":
        return "I was going through your file and your life cover may not be keeping up with your commitments and your family's needs."
    if signal == "goal_behind":
        return f"I noticed your goal '{ev.get('goal_title')}' is a little behind where we planned to be, and there are simple ways to get it back on track."
    if signal == "life_event":
        return {"new_baby": "Congratulations on the new arrival! It is a good moment to make sure your family is properly protected.",
                "marriage": "Congratulations on your marriage! It is a good moment to update your cover and beneficiaries.",
                "new_vehicle": "Congratulations on the new vehicle. I want to make sure it is properly covered.",
                "property_purchase": "Congratulations on the property. I want to make sure your home and bond are protected.",
                "job_change": "I saw that your work situation has changed, so it is a good time to check your income protection.",
                "divorce": "I am sorry to hear about the change in your circumstances. Let us make sure your cover and beneficiaries are up to date.",
                "retirement_approaching": "With retirement getting closer, it is a good time to check that your plan is on track.",
                "renewal": "One of your policies comes up for renewal soon, which is a good time to review everything together."}.get(ev.get("kind"), title + ".")
    if signal == "missing_cover":
        return f"I noticed you do not currently have {CATEGORY_LABELS.get(ev.get('category'), 'that cover')} with us, and I would like to make sure that is a deliberate choice."
    if signal == "single_product":
        return "You have been with us for a while and I would like to make sure your protection is complete."
    if signal == "lapsed_cover":
        return f"Your policy {ev.get('policy_number')} has lapsed, which means you are currently unprotected. I would like to help you sort that out."
    if signal == "expiring_document":
        return "Your driver's licence on our file is about to expire (or already has), and we need the renewed copy to keep your records and claims smooth."
    return title + "."


_SUBJECTS = {"under_insured_life": "A quick check on your life cover", "goal_behind": "Getting your goal back on track",
             "life_event": "Congratulations, and a quick check-in", "missing_cover": "Is your cover complete?",
             "single_product": "A quick review of your cover", "lapsed_cover": "About your lapsed policy",
             "expiring_document": "Your document is due for renewal"}


def template_draft(row: Row, channel: str, adviser_name: str) -> Dict[str, Any]:
    first, adv = _first(row["client_name"]), _first(adviser_name)
    line = _outreach_line(row["signal"], row["evidence"], row["title"])
    ask = "Would you have 20 minutes this week for a quick call? Reply here and we will find a time."
    if channel == "whatsapp":
        return {"subject": None, "body": f"Hi {first}, it is {adv} from Royal Square. {line} {ask}"}
    return {"subject": _SUBJECTS[row["signal"]], "body": f"Hi {first},\n\n{line}\n\n{ask}\n\nKind regards,\n{adv}\nRoyal Square Financial"}


_NUM = re.compile(r"\d[\d ,.]*\d|\d")


def _numbers(text: str) -> set:
    return {re.sub(r"[ ,.]", "", n) for n in _NUM.findall(text)}


_SYSTEM = (
    "You polish short messages that a South African financial adviser will review and send to a client. Keep the meaning, keep it warm, "
    "plain and under 90 words. Use ONLY the facts in the message you are given: do not add numbers, prices, product names, "
    "guarantees or promises. Respond with JSON only: {\"subject\": string or null, \"body\": string}."
)


def draft(conn: psycopg.Connection, llm: LLMRouter, p: Principal, opp_id: UUID, channel: str) -> Dict[str, Any]:
    if not p.is_advisor:
        raise forbidden("Only the client's adviser can draft outreach.")
    row = _load(conn, p, opp_id)
    base = template_draft(row, channel, p.full_name)
    out = {"channel": channel, **base, "source": "template", "requires_human_review": True, "warnings": [],
           "note": "Edit before sending. Royal Square does not send messages from this screen."}
    if llm.providers:
        try:
            text = f"Channel: {channel}\nSubject: {base['subject']}\nBody:\n{base['body']}"
            res = llm.generate([Message("system", _SYSTEM), Message("user", text)], json_mode=True)
            data = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", res.text.strip(), flags=re.S))
            body = re.sub(r"<[^>]*>", "", str(data.get("body", ""))).strip()
            subject = re.sub(r"<[^>]*>", "", str(data.get("subject") or "")).strip() or base["subject"]
            extra = _numbers(body + " " + (subject or "")) - _numbers(base["body"] + " " + (base["subject"] or ""))
            if body and not extra:
                out.update(body=body, subject=subject if channel == "email" else None, source="ai")
            else:
                out["warnings"].append("The AI wording was discarded because it added figures that are not in the facts. Showing the standard wording.")
        except (ApiError, ValueError, AttributeError):
            out["warnings"].append("The AI writer is unavailable, so this is the standard wording.")
    _event(conn, opp_id, "draft_generated", p, channel=channel)
    audit.record(conn, p, "opportunity.draft_generated", "opportunity", opp_id, client_id=row["client_id"],
                 summary=f"Generated a {channel} outreach draft for '{row['title']}' (not sent)", details={"channel": channel, "source": out["source"]})
    return out
