"""Client health and compliance health: deliberately simple formulas that the UI prints next to the number.

CLIENT HEALTH (0-100, higher is healthier). Five components, each scored 0 to 1 and multiplied by its weight:

    engagement  30   days since the adviser last reached the client (30 or fewer = 1, 180 or more = 0, straight line between)
    review      25   days since the last annual review (365 or fewer = 1, 545 or more = 0; none recorded = 0)
    goals       20   average of (actual progress / expected progress) over active goals, capped at 1; no goals = 1
    documents   15   verified, unexpired ID = 1; expiring within 30 days = 0.5; otherwise 0
    claims      10   no open claim stuck in one status for more than the stale threshold = 1, otherwise 0

    "Last reached" is the newest of: an advice record, logged outreach on an opportunity, an adviser's update on the client's
    claim, or a handled request. Below `at_risk_health_below` a client is "at risk".

COMPLIANCE HEALTH is three yes/no checks per client, weighted equally:

    identity   a verified ID document that has not expired
    advice     an approved, client-acknowledged advice record within the last 12 months
    consent    the latest data-processing consent is "granted"

The score is (checks passed) / (3 x clients). Documents that are still valid but expire within 30 days are flagged as a gap
of their own, without failing the identity check.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List
from uuid import UUID

import psycopg

from app.core import clock
from app.core.db import fetch_all
from app.domain.radar_config import ASSUMPTIONS as A

WEIGHTS = {"engagement": 30, "review": 25, "goals": 20, "documents": 15, "claims": 10}
LABELS = {"engagement": "Recent contact", "review": "Review up to date", "goals": "Goals on track", "documents": "Documents valid",
          "claims": "No stuck claims"}
EXPIRY_WARNING_DAYS = 30
ADVICE_MAX_AGE_DAYS = 365


def _scale(days: float, full: float, zero: float) -> float:
    """1.0 at `full` days or fewer, 0.0 at `zero` days or more, a straight line between."""
    if days <= full:
        return 1.0
    if days >= zero:
        return 0.0
    return round((zero - days) / (zero - full), 3)


# ------------------------------------------------------------------------------------------------- compliance
def compliance_status(conn: psycopg.Connection, client_ids: List[UUID], today: date) -> Dict[UUID, Dict[str, Any]]:
    """The three compliance checks for each client, with the facts behind each answer."""
    if not client_ids:
        return {}
    ids = fetch_all(
        conn,
        "select distinct on (client_id) client_id, id, status, expiry_date from identity_documents "
        "where client_id = any(%s) and doc_type = 'id_document' and status in ('verified', 'pending') "
        "order by client_id, (status = 'verified') desc, uploaded_at desc", (client_ids,))
    identity = {r["client_id"]: r for r in ids}
    advice = {r["client_id"]: r for r in fetch_all(
        conn, "select distinct on (client_id) client_id, created_at, client_acknowledged from advice_records "
              "where client_id = any(%s) order by client_id, created_at desc", (client_ids,))}
    consent = {r["client_id"]: r for r in fetch_all(
        conn, "select distinct on (client_id) client_id, status, recorded_at from consents "
              "where client_id = any(%s) and purpose = 'data_processing' order by client_id, recorded_at desc", (client_ids,))}
    out: Dict[UUID, Dict[str, Any]] = {}
    for cid in client_ids:
        d, a, c = identity.get(cid), advice.get(cid), consent.get(cid)
        if d is None:
            id_state, expiry = "missing", None
        elif d["status"] == "pending":
            id_state, expiry = "pending", d["expiry_date"]
        elif d["expiry_date"] and d["expiry_date"] < today:
            id_state, expiry = "expired", d["expiry_date"]
        elif d["expiry_date"] and (d["expiry_date"] - today).days <= EXPIRY_WARNING_DAYS:
            id_state, expiry = "expiring", d["expiry_date"]
        else:
            id_state, expiry = "valid", d["expiry_date"]
        if a is None:
            adv_state = "missing"
        elif (today - a["created_at"].astimezone(clock.SAST).date()).days > ADVICE_MAX_AGE_DAYS:
            adv_state = "stale"
        elif not a["client_acknowledged"]:
            adv_state = "unacknowledged"
        else:
            adv_state = "current"
        con_state = "missing" if c is None else ("current" if c["status"] == "granted" else "withdrawn")
        out[cid] = {
            "identity": {"state": id_state, "ok": id_state in ("valid", "expiring"), "expiry_date": expiry, "document_id": d["id"] if d else None},
            "advice": {"state": adv_state, "ok": adv_state == "current", "last_at": a["created_at"] if a else None},
            "consent": {"state": con_state, "ok": con_state == "current", "recorded_at": c["recorded_at"] if c else None},
        }
    return out


_GAP_TEXT = {
    ("identity", "missing"): "No verified identity document on file", ("identity", "pending"): "Identity document uploaded but not yet verified",
    ("identity", "expired"): "Identity document has expired", ("identity", "expiring"): "Identity document expires soon",
    ("advice", "missing"): "No advice record on file", ("advice", "stale"): "Advice record is more than 12 months old",
    ("advice", "unacknowledged"): "Advice record has not been acknowledged by the client",
    ("consent", "missing"): "No data-processing consent recorded", ("consent", "withdrawn"): "Data-processing consent was withdrawn",
}


def compliance_gaps(status: Dict[UUID, Dict[str, Any]], names: Dict[UUID, str]) -> List[Dict[str, Any]]:
    gaps = []
    for cid, s in status.items():
        for kind in ("identity", "advice", "consent"):
            state = s[kind]["state"]
            if not s[kind]["ok"] or (kind == "identity" and state == "expiring"):
                gaps.append({"client": {"id": cid, "full_name": names.get(cid)}, "kind": kind, "state": state,
                             "label": _GAP_TEXT[(kind, state)], "severity": "high" if state in ("missing", "expired", "withdrawn") else "medium",
                             "fix_path": f"/clients/{cid}?tab=compliance"})
    gaps.sort(key=lambda g: (g["severity"] != "high", g["client"]["full_name"] or ""))
    return gaps


def compliance_summary(conn: psycopg.Connection, client_ids: List[UUID], names: Dict[UUID, str], today: date) -> Dict[str, Any]:
    status = compliance_status(conn, client_ids, today)
    n = len(client_ids)

    def part(kind: str) -> Dict[str, Any]:
        ok = sum(1 for s in status.values() if s[kind]["ok"])
        return {"ok": ok, "total": n, "percent": round(ok * 100 / n, 1) if n else None}

    comps = {k: part(k) for k in ("identity", "advice", "consent")}
    passed = sum(c["ok"] for c in comps.values())
    full = sum(1 for s in status.values() if all(s[k]["ok"] for k in ("identity", "advice", "consent")))
    return {
        "score_percent": round(passed * 100 / (3 * n), 1) if n else None,
        "fully_compliant_clients": full, "clients": n, "components": comps,
        "gaps": compliance_gaps(status, names),
        "definition": "Score = checks passed / (3 x clients). Checks: a verified, unexpired ID document; an approved and client-acknowledged "
                      "advice record from the last 12 months; a granted data-processing consent.",
    }


# --------------------------------------------------------------------------------------------------- client health
def last_contact(conn: psycopg.Connection, client_ids: List[UUID]) -> Dict[UUID, datetime]:
    rows = fetch_all(
        conn,
        """
        select client_id, max(ts) as ts from (
          select client_id, created_at as ts from advice_records where client_id = any(%(ids)s)
          union all
          select o.client_id, e.created_at from opportunity_events e join opportunities o on o.id = e.opportunity_id
            where e.kind = 'outreach_logged' and o.client_id = any(%(ids)s)
          union all
          select c.client_id, e.created_at from claim_events e join claims c on c.id = e.claim_id join profiles a on a.id = e.actor_id
            where a.role = 'advisor' and c.client_id = any(%(ids)s)
          union all
          select client_id, updated_at from requests where handled_by is not null and client_id = any(%(ids)s)
        ) t group by client_id
        """, {"ids": client_ids})
    return {r["client_id"]: r["ts"] for r in rows}


def client_health(conn: psycopg.Connection, client_ids: List[UUID], today: date) -> Dict[UUID, Dict[str, Any]]:
    if not client_ids:
        return {}
    contact = last_contact(conn, client_ids)
    clients = {r["id"]: r for r in fetch_all(conn, "select id, last_annual_review_date, client_since from clients where id = any(%s)", (client_ids,))}
    goals = fetch_all(conn, "select gp.client_id, g.created_at, g.target_date, g.current_amount_cents, g.target_amount_cents from goals g "
                            "join goal_participants gp on gp.goal_id = g.id where g.status = 'active' and gp.client_id = any(%s)", (client_ids,))
    stale = {r["client_id"] for r in fetch_all(
        conn, "select distinct client_id from claims where client_id = any(%s) and status in ('registered','assessment','quotes','authorised','in_repair','completed') "
              "and status_changed_at <= now() - make_interval(days => %s)", (client_ids, A["stale_claim_days"]))}
    comp = compliance_status(conn, client_ids, today)
    out: Dict[UUID, Dict[str, Any]] = {}
    for cid in client_ids:
        c = clients[cid]
        parts: Dict[str, tuple] = {}
        ts = contact.get(cid)
        days = (clock.now() - ts).days if ts else None
        parts["engagement"] = (0.0 if days is None else _scale(days, 30, 180), "no contact recorded" if days is None else f"{days} day(s) since last contact")
        rv = c["last_annual_review_date"]
        rdays = (today - rv).days if rv else None
        parts["review"] = (0.0 if rdays is None else _scale(rdays, 365, 545), "no review recorded" if rdays is None else f"last review {rdays} day(s) ago")
        ratios = []
        for g in goals:
            if g["client_id"] != cid or not g["target_date"]:
                continue
            start = g["created_at"].astimezone(clock.SAST).date()
            total = (g["target_date"] - start).days
            if total < A["goal_min_days"]:
                continue
            expected = max(0.0, min(100.0, (today - start).days / total * 100))
            actual = min(100.0, g["current_amount_cents"] * 100 / g["target_amount_cents"])
            ratios.append(1.0 if expected < 5 else min(1.0, actual / expected))
        parts["goals"] = ((sum(ratios) / len(ratios)) if ratios else 1.0, f"{len(ratios)} goal(s) with a target date" if ratios else "no dated goals")
        idn = comp[cid]["identity"]["state"]
        parts["documents"] = ({"valid": 1.0, "expiring": 0.5}.get(idn, 0.0), f"identity {idn}")
        parts["claims"] = (0.0 if cid in stale else 1.0, "a claim is stuck" if cid in stale else "no stuck claims")
        components = [{"key": k, "label": LABELS[k], "weight": WEIGHTS[k], "value": round(v, 3), "points": round(WEIGHTS[k] * v, 1), "detail": d}
                      for k, (v, d) in parts.items()]
        score = round(sum(x["points"] for x in components))
        out[cid] = {
            "score": score, "band": "at_risk" if score < A["at_risk_health_below"] else ("watch" if score < 80 else "healthy"),
            "components": components, "last_contact_at": ts, "days_since_contact": days,
            "weakest": min(components, key=lambda x: x["points"] / x["weight"])["label"],
        }
    return out


HEALTH_FORMULA = (
    "Health = 30 x recent contact + 25 x review up to date + 20 x goals on track + 15 x documents valid + 10 x no stuck claims, "
    "each scored 0 to 1. At risk = below " + str(A["at_risk_health_below"]) + "."
)
