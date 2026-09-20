"""The compliance file per client, the regulator/insurer pack, timelines and the retention review (docs/AUDIT.md build step 6).

`build_pack` assembles, in one pass over the database, everything a regulator or an insurer would ask for about one client: identity
(with reuse), consents, advice records, documents, claims and requests with their timelines, and the access history from the audit
trail, plus whether the trail's hash chain still verifies. It is generated on demand, timestamped, and its own generation is audited.
The pack carries a content hash so the recipient can tell whether it was altered after export.

Data minimisation: needs-analysis fields (income, dependants), bank details and request payloads are NOT in the pack.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import psycopg

from app.core import clock
from app.core.auth import Principal
from app.core.config import Settings
from app.core.db import fetch_all, fetch_one
from app.core.errors import validation
from app.services import advice as advice_svc, audit, consents, health, identity
from app.services.common import require_client_in_scope

PACK_SECTIONS = ["client", "compliance_status", "identity", "consents", "advice_records", "policies", "documents", "claims", "requests", "access_history", "integrity"]


def _j(o: Any) -> Any:
    return json.loads(json.dumps(o, default=lambda x: x.isoformat() if isinstance(x, (datetime, date)) else str(x)))


def build_pack(conn: psycopg.Connection, p: Principal, client_id: UUID, *, fmt: str = "json") -> Dict[str, Any]:
    started = time.monotonic()
    require_client_in_scope(conn, p, client_id)
    c = fetch_one(conn, "select pr.id, pr.full_name, pr.email, pr.phone, c.date_of_birth, c.client_since, c.last_annual_review_date, c.drivers_licence_expiry, "
                        "ad.full_name as adviser_name, ad.id as adviser_id from clients c join profiles pr on pr.id = c.id join profiles ad on ad.id = c.adviser_id where c.id = %s", (client_id,))
    names = {client_id: c["full_name"]}
    status = health.compliance_status(conn, [client_id], clock.today())[client_id]
    vault = identity.list_for(conn, p, client_id)
    for d in vault["documents"]:
        d.pop("client_id", None)
    advice = [{k: v for k, v in r.items() if k != "client"} for r in advice_svc.list_records(conn, p, client_id)["items"]]
    con = consents.list_for(conn, p, client_id)
    pols = fetch_all(conn, "select p.product_name, p.category, p.policy_number, p.status, p.start_date, p.renewal_date, i.name as insurer from policies p "
                           "join insurers i on i.id = p.insurer_id where p.client_id = %s order by p.category, p.product_name", (client_id,))
    docs = fetch_all(conn, "select a.kind, a.filename, a.content_type, a.size_bytes, a.uploaded_at, u.full_name as uploaded_by, "
                           "case when a.claim_id is not null then 'claim' else 'request' end as attached_to, coalesce(c.reference, r.type) as reference "
                           "from attachments a join profiles u on u.id = a.uploaded_by left join claims c on c.id = a.claim_id left join requests r on r.id = a.request_id "
                           "where coalesce(c.client_id, r.client_id) = %s and a.storage_path not like 'identity/%%' order by a.uploaded_at", (client_id,))
    claims = []
    for cl in fetch_all(conn, "select c.id, c.reference, c.status, c.submitted_at, c.closed_at, c.insurer_claim_number, i.name as insurer from claims c "
                              "left join insurers i on i.id = c.insurer_id where c.client_id = %s and c.status <> 'draft' order by c.submitted_at", (client_id,)):
        ev = fetch_all(conn, "select e.title, e.message, e.created_at, e.visible_to_client, coalesce(a.full_name, 'System') as actor, coalesce(a.role, 'system') as role "
                             "from claim_events e left join profiles a on a.id = e.actor_id where e.claim_id = %s order by e.created_at, e.id", (cl["id"],))
        claims.append({**cl, "events": ev})
    reqs = []
    for r in fetch_all(conn, "select id, type, status, submitted_at, completed_at, adviser_response, payload from requests where client_id = %s order by submitted_at", (client_id,)):
        ev = fetch_all(conn, "select e.title, e.message, e.created_at, coalesce(a.full_name, 'System') as actor from request_events e left join profiles a on a.id = e.actor_id "
                             "where e.request_id = %s order by e.created_at, e.id", (r["id"],))
        reqs.append({"id": r["id"], "type": r["type"], "status": r["status"], "submitted_at": r["submitted_at"], "completed_at": r["completed_at"],
                     "adviser_response": r["adviser_response"], "fields_supplied": sorted(r["payload"].keys()), "events": ev})
    access = audit.entries_for_client(conn, client_id, 300)
    chain = audit.verify_chain(conn)
    body = {
        "client": {"id": c["id"], "full_name": c["full_name"], "email": c["email"], "phone": c["phone"], "date_of_birth": c["date_of_birth"], "client_since": c["client_since"],
                   "last_annual_review_date": c["last_annual_review_date"], "adviser": {"id": c["adviser_id"], "full_name": c["adviser_name"]}},
        "compliance_status": status,
        "identity": {"summary": vault["summary"], "documents": vault["documents"], "reuse_log": vault["reuse_log"], "verifier": vault["verifier"]},
        "consents": {"notice_version": con["notice_version"], "notice_is_draft": con["notice_is_draft"], "current": con["current"], "history": con["history"]},
        "advice_records": advice, "policies": pols, "documents": docs, "claims": claims, "requests": reqs,
    }
    body = _j(body)
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    pack = {
        "reference": f"PACK-{clock.today():%Y%m%d}-{digest[:8].upper()}", "generated_at": clock.now(), "generated_by": {"id": p.id, "full_name": p.full_name, "role": p.role},
        "sections": PACK_SECTIONS, "content_sha256": digest, **body,
        "access_history": _j(access),
        "integrity": {"audit_chain_ok": chain["ok"], "audit_entries_checked": chain["checked"], "first_bad_id": chain["first_bad_id"],
                      "note": "Tamper evidence is demo level: see docs/api.md 5.15."},
        "excluded_for_data_minimisation": ["annual income", "dependants", "bank details", "request field values", "document contents"],
    }
    pack["generation_ms"] = int((time.monotonic() - started) * 1000)
    audit.record(conn, p, "compliance.pack_exported", "client", client_id, client_id=client_id, summary=f"Generated a compliance pack ({fmt})",
                 details={"format": fmt, "reference": pack["reference"], "content_sha256": digest, "generation_ms": pack["generation_ms"]})
    return pack


# ------------------------------------------------------------------------------------------------------- PDF
def _latin(s: Any) -> str:
    """The built-in PDF fonts are Latin-1: keep the text readable rather than crash on a curly quote or an emoji."""
    return str(s if s is not None else "").replace("–", "-").replace("—", "-").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').encode("latin-1", "replace").decode("latin-1")


def _dt(v: Any) -> str:
    if not v:
        return "-"
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(clock.SAST).strftime("%d %b %Y %H:%M")
    except ValueError:
        return str(v)


def render_pdf(pack: Dict[str, Any]) -> bytes:
    from fpdf import FPDF

    class Pdf(FPDF):
        def footer(self) -> None:
            self.set_y(-12)
            self.set_font("helvetica", "", 8)
            self.cell(0, 6, _latin(f"{pack['reference']}  |  page {self.page_no()}  |  Demo data: synthetic, for demonstration only"), align="C")

    pdf = Pdf(format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    def h1(t: str) -> None:
        pdf.set_font("helvetica", "B", 15)
        pdf.set_text_color(0, 46, 108)
        pdf.cell(0, 9, _latin(t), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

    def h2(t: str) -> None:
        pdf.ln(3)
        pdf.set_font("helvetica", "B", 11)
        pdf.set_fill_color(230, 236, 246)
        pdf.cell(0, 7, _latin(t), new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_font("helvetica", "", 9)

    def line(t: str, bold: bool = False) -> None:
        pdf.set_font("helvetica", "B" if bold else "", 9)
        pdf.multi_cell(0, 5, _latin(t), new_x="LMARGIN", new_y="NEXT")

    c = pack["client"]
    h1("Compliance pack")
    line(f"Client: {c['full_name']}    Adviser: {c['adviser']['full_name']}", True)
    line(f"Reference {pack['reference']}    Generated {_dt(pack['generated_at'])} by {pack['generated_by']['full_name']} ({pack['generated_by']['role']})")
    line(f"Content SHA-256: {pack['content_sha256']}")
    line("This pack is generated from the platform's records. Personal data in it is synthetic demo data.")
    st = pack["compliance_status"]
    h2("Compliance status")
    for k, lab in (("identity", "Identity"), ("advice", "Advice record"), ("consent", "Consent")):
        line(f"{lab}: {st[k]['state']}" + (f" (expires {st[k]['expiry_date']})" if k == "identity" and st[k].get("expiry_date") else ""))
    h2("Identity documents (verification is simulated in this demo)")
    for d in pack["identity"]["documents"] or []:
        line(f"- {d['label']}: {d['status']}, verified {_dt(d['verified_at'])} by {(d.get('verified_by') or {}).get('full_name') or '-'}, expiry {d['expiry_date'] or '-'}, reused {d['reuse_count']}x")
    if not pack["identity"]["documents"]:
        line("None on file.")
    for r in pack["identity"]["reuse_log"][:15]:
        line(f"  Reuse: {r['label']} used for a {r['used_for']} on {_dt(r['used_at'])}")
    h2("Consents (privacy notice " + pack["consents"]["notice_version"] + ", draft for legal review)")
    for row in pack["consents"]["history"]:
        line(f"- {_dt(row['recorded_at'])}: {row['purpose']} {row['status']} ({row['method']})")
    if not pack["consents"]["history"]:
        line("None recorded.")
    h2("Advice records")
    for a in pack["advice_records"]:
        line(f"{_dt(a['created_at'])} - {a['interaction_type']} by {a['adviser']['full_name']}; approved {_dt(a['approved_at'])}; client acknowledged: {'yes, ' + str(a['acknowledgement_method']) if a['client_acknowledged'] else 'no'}", True)
        line("  " + a["final_summary"])
    if not pack["advice_records"]:
        line("None on file.")
    h2("Policies")
    for x in pack["policies"]:
        line(f"- {x['insurer']}: {x['product_name']} ({x['category']}) {x['policy_number']} - {x['status']}")
    h2("Claims")
    for cl in pack["claims"]:
        line(f"{cl['reference']} ({cl['insurer'] or 'insurer not set'}) - {cl['status']}, submitted {_dt(cl['submitted_at'])}", True)
        for e in cl["events"]:
            line(f"  {_dt(e['created_at'])}  {e['actor']}: {e['title']}")
    if not pack["claims"]:
        line("None.")
    h2("Requests")
    for r in pack["requests"]:
        line(f"{r['type']} - {r['status']}, submitted {_dt(r['submitted_at'])}", True)
        for e in r["events"]:
            line(f"  {_dt(e['created_at'])}  {e['actor']}: {e['title']}")
    if not pack["requests"]:
        line("None.")
    h2("Documents (metadata only)")
    for d in pack["documents"]:
        line(f"- {d['kind']} {d['filename']} on {d['attached_to']} {d['reference']}, uploaded {_dt(d['uploaded_at'])} by {d['uploaded_by']}")
    if not pack["documents"]:
        line("None.")
    h2(f"Access history (latest {len(pack['access_history'])} entries)")
    for e in pack["access_history"][:120]:
        line(f"{_dt(e['occurred_at'])}  {e['actor']['full_name'] or 'System'} ({e['actor']['role']})  {e['action']}: {e['summary']}")
    h2("Integrity")
    line(f"Audit-trail hash chain verifies: {'yes' if pack['integrity']['audit_chain_ok'] else 'NO'} ({pack['integrity']['audit_entries_checked']} entries). {pack['integrity']['note']}")
    line("Excluded for data minimisation: " + ", ".join(pack["excluded_for_data_minimisation"]) + ".")
    return bytes(pdf.output())


# ------------------------------------------------------------------------------------------------------ timeline
_NOISE = {"client.viewed", "claim.viewed", "opportunity.viewed", "identity.listed", "assistant.query", "access.denied", "audit.exported", "compliance.pack_exported",
          "owner.health_viewed", "owner.drilldown_viewed", "demo.reset"}
_CLIENT_SAFE_PREFIXES = ("claim.", "request.", "document.", "identity.", "consent.", "advice.", "goal.", "reminder.completed", "life_event.")


def timeline(conn: psycopg.Connection, p: Principal, client_id: Optional[UUID], limit: int = 100) -> Dict[str, Any]:
    cid = p.id if p.is_client else client_id
    if cid is None:
        raise validation("client_id", "required", "client_id is required.")
    if not p.is_client:
        require_client_in_scope(conn, p, cid)
    rows = fetch_all(conn, "select l.id, l.occurred_at, l.actor_id, l.actor_role, l.action, l.entity_type, l.entity_id, l.summary, a.full_name as actor_name from audit_log l "
                           "left join profiles a on a.id = l.actor_id where l.client_id = %s order by l.id desc limit 600", (cid,))
    out = []
    for r in rows:
        if r["action"] in _NOISE or r["action"].startswith(("opportunity.", "ai.")):
            continue        # who looked at what, and internal sales notes, are in the audit log, not in a client's timeline
        if p.is_client and not r["action"].startswith(_CLIENT_SAFE_PREFIXES):
            continue
        if p.is_client and r["action"] == "claim.note_added":
            continue        # an adviser-only note: the timeline for a client shows only what the claim's own timeline shows them
        out.append({"id": r["id"], "occurred_at": r["occurred_at"], "actor": {"id": r["actor_id"], "full_name": r["actor_name"] or ("System" if not r["actor_id"] else None), "role": r["actor_role"]},
                    "action": r["action"], "summary": r["summary"], "entity_type": r["entity_type"], "entity_id": r["entity_id"]})
        if len(out) >= limit:
            break
    return {"client_id": cid, "items": out}


# ------------------------------------------------------------------------------------------------ overview / retention
def overview(conn: psycopg.Connection, p: Principal) -> Dict[str, Any]:
    ids = p.client_ids(conn)
    rows = fetch_all(conn, "select c.id, pr.full_name, ad.full_name as adviser_name from clients c join profiles pr on pr.id = c.id join profiles ad on ad.id = c.adviser_id "
                           "where c.id = any(%s) order by pr.full_name", (ids,))
    names = {r["id"]: r["full_name"] for r in rows}
    summary = health.compliance_summary(conn, ids, names, clock.today())
    status = health.compliance_status(conn, ids, clock.today())
    return {"summary": summary, "clients": [{"id": r["id"], "full_name": r["full_name"], "adviser": r["adviser_name"],
                                            "identity": status[r["id"]]["identity"]["state"], "advice": status[r["id"]]["advice"]["state"],
                                            "consent": status[r["id"]]["consent"]["state"]} for r in rows]}


def retention_review(conn: psycopg.Connection, p: Principal, settings: Settings) -> Dict[str, Any]:
    """Records past the configured retention period, FLAGGED for a human decision. Nothing is deleted automatically."""
    years = settings.retention_years
    cutoff = clock.today() - timedelta(days=365 * years)
    ids = p.client_ids(conn)
    items: List[Dict[str, Any]] = []
    for r in fetch_all(conn, "select c.id, c.client_id, pr.full_name, c.reference, c.closed_at from claims c join profiles pr on pr.id = c.client_id "
                            "where c.client_id = any(%s) and c.status = 'closed' and c.closed_at < %s order by c.closed_at", (ids, cutoff)):
        items.append({"kind": "closed_claim", "label": f"Closed claim {r['reference']}", "client": {"id": r["client_id"], "full_name": r["full_name"]}, "date": r["closed_at"], "entity_id": r["id"]})
    for r in fetch_all(conn, "select q.id, q.client_id, pr.full_name, q.type, coalesce(q.completed_at, q.updated_at) as d from requests q join profiles pr on pr.id = q.client_id "
                            "where q.client_id = any(%s) and q.status in ('completed', 'declined') and coalesce(q.completed_at, q.updated_at) < %s order by d", (ids, cutoff)):
        items.append({"kind": "closed_request", "label": f"Closed request ({r['type']})", "client": {"id": r["client_id"], "full_name": r["full_name"]}, "date": r["d"], "entity_id": r["id"]})
    for r in fetch_all(conn, "select d.id, d.client_id, pr.full_name, d.doc_type, d.status, d.uploaded_at from identity_documents d join profiles pr on pr.id = d.client_id "
                            "where d.client_id = any(%s) and d.status in ('superseded', 'rejected') and d.uploaded_at < %s order by d.uploaded_at", (ids, cutoff)):
        items.append({"kind": "identity_document", "label": f"{d_label(r['doc_type'])} ({r['status']})", "client": {"id": r["client_id"], "full_name": r["full_name"]}, "date": r["uploaded_at"], "entity_id": r["id"]})
    return {"retention_years": years, "cutoff_date": cutoff, "total": len(items), "items": _j(items), "action": "flag_only",
            "note": "The retention period is a configuration placeholder (RETENTION_YEARS) to be set by counsel or the compliance officer. "
                    "Nothing is deleted automatically: this list is for a human to review."}


def d_label(doc_type: str) -> str:
    text = identity.LABELS[doc_type]
    return "ID document" if doc_type == "id_document" else text[0].upper() + text[1:]
