"""The identity vault (docs/AUDIT.md build step 5, brief section D).

A verified identity document is captured ONCE, stored in the private bucket, and REUSED by claims and requests instead of asking the
client again, while it is still valid. Every reuse is logged (who, for what, when) and audited.

Verification is SIMULATED behind `IdentityVerifier`. `DemoIdentityVerifier` does not contact any KYC provider and checks nothing about
the document itself except the expiry date an adviser enters: it exists so the workflow can be shown end to end. A real integration
implements the same interface. The UI and the API both say "demo".
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID, uuid4

import psycopg

from app.core import clock
from app.core.auth import Principal
from app.core.config import Settings
from app.core.db import Row, execute, fetch_all, fetch_one
from app.core.errors import bad_state, not_found, validation
from app.domain.radar_config import ASSUMPTIONS as A
from app.services import attachments as att, audit, workflow
from app.services.common import require_client_in_scope, update_row
from app.storage.base import Storage, safe_filename

DOC_TYPES = ("id_document", "drivers_licence", "proof_of_address")
LABELS = {"id_document": "ID document", "drivers_licence": "driver's licence", "proof_of_address": "proof of address"}
EXPIRY_WARNING_DAYS = 30
POA_MAX_AGE_DAYS = A["proof_of_address_max_age_days"]


# ------------------------------------------------------------------------------------------------ the interface
@dataclass
class VerificationResult:
    ok: bool
    reason: Optional[str] = None
    verifier: str = ""
    simulated: bool = True


class IdentityVerifier(Protocol):
    name: str

    def verify(self, doc_type: str, content_type: str, size_bytes: int, expiry_date: Optional[date]) -> VerificationResult: ...


class DemoIdentityVerifier:
    """DEMO ADAPTER. Not a KYC check. It accepts a document unless the expiry date the adviser typed is already in the past."""
    name = "demo_simulated"

    def verify(self, doc_type: str, content_type: str, size_bytes: int, expiry_date: Optional[date]) -> VerificationResult:
        if expiry_date is not None and expiry_date < clock.today():
            return VerificationResult(False, "The expiry date has passed.", self.name)
        return VerificationResult(True, None, self.name)


# --------------------------------------------------------------------------------------------------- state
def valid_document(conn: psycopg.Connection, client_id: UUID, doc_type: str, today: Optional[date] = None) -> Optional[Row]:
    """The newest verified document of this type that may still be relied on, or None."""
    today = today or clock.today()
    row = fetch_one(conn, "select * from identity_documents where client_id = %s and doc_type = %s and status = 'verified' "
                          "order by verified_at desc limit 1", (client_id, doc_type))
    if row is None:
        return None
    if row["expiry_date"] and row["expiry_date"] < today:
        return None
    if doc_type == "proof_of_address" and (today - row["verified_at"].astimezone(clock.SAST).date()).days > POA_MAX_AGE_DAYS:
        return None
    return row


def state_of(conn: psycopg.Connection, client_id: UUID, doc_type: str, today: Optional[date] = None) -> Dict[str, Any]:
    today = today or clock.today()
    row = fetch_one(conn, "select * from identity_documents where client_id = %s and doc_type = %s and status in ('verified', 'pending') "
                          "order by (status = 'verified') desc, uploaded_at desc limit 1", (client_id, doc_type))
    if row is None:
        return {"state": "missing", "document_id": None, "expiry_date": None, "verified_at": None}
    base = {"document_id": row["id"], "expiry_date": row["expiry_date"], "verified_at": row["verified_at"]}
    if row["status"] == "pending":
        return {"state": "pending", **base}
    if row["expiry_date"] and row["expiry_date"] < today:
        return {"state": "expired", **base}
    if doc_type == "proof_of_address" and (today - row["verified_at"].astimezone(clock.SAST).date()).days > POA_MAX_AGE_DAYS:
        return {"state": "stale", **base}
    if row["expiry_date"] and (row["expiry_date"] - today).days <= EXPIRY_WARNING_DAYS:
        return {"state": "expiring", **base}
    return {"state": "valid", **base}


# ------------------------------------------------------------------------------------------------------ reuse
def record_reuse(conn: psycopg.Connection, doc: Row, used_for: str, used_for_id: Optional[UUID], actor: Optional[Principal]) -> None:
    execute(conn, "insert into identity_reuse_log (document_id, client_id, used_for, used_for_id, used_by) values (%s,%s,%s,%s,%s)",
            (doc["id"], doc["client_id"], used_for, used_for_id, actor.id if actor else None))
    audit.record(conn, actor, "identity.reused", "identity_document", doc["id"], client_id=doc["client_id"],
                 summary=f"Reused the verified {LABELS[doc['doc_type']]} for a {used_for} instead of asking again",
                 details={"used_for": used_for, "used_for_id": used_for_id, "doc_type": doc["doc_type"]})


def attach_licence_to_claim(conn: psycopg.Connection, doc: Row, claim_id: UUID, actor: Principal) -> None:
    """Point the claim's licence attachment at the vault file (same private object, no second copy) and log the reuse."""
    from app.services.claims import add_event

    execute(conn, "insert into attachments (id, claim_id, kind, label, storage_path, filename, content_type, size_bytes, uploaded_by) "
                  "values (%s,%s,'drivers_licence',%s,%s,%s,%s,%s,%s)",
            (uuid4(), claim_id, "Verified driver's licence (from your identity vault)", doc["storage_path"], doc["filename"],
             doc["content_type"], doc["size_bytes"], doc["client_id"]))
    add_event(conn, claim_id, "attachment_added", "Driver's licence taken from your verified documents",
              message="You were not asked to upload it again.", actor_id=None)
    record_reuse(conn, doc, "claim", claim_id, actor)


def claim_state(conn: psycopg.Connection, client_id: UUID, claim_id: UUID) -> Dict[str, Any]:
    reused = fetch_one(conn, "select 1 as x from attachments where claim_id = %s and kind = 'drivers_licence' and storage_path like 'identity/%%'", (claim_id,))
    return {"reused": reused is not None, **state_of(conn, client_id, "drivers_licence")}


def on_request_created(conn: psycopg.Connection, type_def: Dict[str, Any], client_id: UUID, request_id: UUID, actor: Principal) -> None:
    """A request that needs identity or a supporting document takes it from the vault when it is valid, and says so."""
    from app.services import workflow as wf

    if type_def["requires_identity"]:
        doc = valid_document(conn, client_id, "id_document")
        if doc:
            record_reuse(conn, doc, "request", request_id, actor)
            wf.add_request_event(conn, request_id, "identity_reused", "Your verified ID was used", message="You were not asked to send it again.")
        else:
            wf.add_request_event(conn, request_id, "identity_needed", "We need to verify your ID first",
                                 message="Add your ID under Identity documents so your adviser can verify it.")
            wf.tell_one(conn, "client", client_id, kind="identity", title="We need a verified ID for your request",
                        body="Add it under Identity documents.", link={"resource": "request", "id": request_id})
    for d in type_def["documents"]:
        if d["kind"] == "proof_of_address" and d["reuse_from_vault"]:
            doc = valid_document(conn, client_id, "proof_of_address")
            if doc:
                record_reuse(conn, doc, "request", request_id, actor)
                wf.add_request_event(conn, request_id, "identity_reused", "Your proof of address on file was used")


# ------------------------------------------------------------------------------------------- upload and verify
def _object(r: Row) -> Dict[str, Any]:
    return {
        "id": r["id"], "client_id": r["client_id"], "doc_type": r["doc_type"], "label": LABELS[r["doc_type"]], "filename": r["filename"],
        "content_type": r["content_type"], "size_bytes": r["size_bytes"], "status": r["status"],
        "verification_source": r["verification_source"], "verifier": r["verifier"],
        "verified_by": {"id": r["verified_by"], "full_name": r.get("verifier_name")} if r["verified_by"] else None,
        "verified_at": r["verified_at"], "issued_date": r["issued_date"], "expiry_date": r["expiry_date"],
        "rejected_reason": r["rejected_reason"], "uploaded_at": r["uploaded_at"], "reuse_count": r.get("reuse_count", 0),
        "is_simulated_verification": r["verification_source"] == "simulated_verification",
    }


_SELECT = ("select d.*, v.full_name as verifier_name, (select count(*) from identity_reuse_log l where l.document_id = d.id) as reuse_count "
           "from identity_documents d left join profiles v on v.id = d.verified_by")


def list_for(conn: psycopg.Connection, p: Principal, client_id: Optional[UUID]) -> Dict[str, Any]:
    if p.is_client:
        client_id = p.id
    elif client_id is None:
        raise validation("client_id", "required", "client_id is required.")
    else:
        require_client_in_scope(conn, p, client_id)
    rows = fetch_all(conn, f"{_SELECT} where d.client_id = %s order by d.uploaded_at desc", (client_id,))
    log = fetch_all(conn, "select l.id, l.used_for, l.used_for_id, l.used_at, d.doc_type, u.full_name as used_by_name from identity_reuse_log l "
                          "join identity_documents d on d.id = l.document_id left join profiles u on u.id = l.used_by "
                          "where l.client_id = %s order by l.used_at desc limit 20", (client_id,))
    audit.record_view(conn, p, "identity.listed", "client", client_id, client_id=client_id, summary="Opened the identity vault")
    return {
        "client_id": client_id, "documents": [_object(r) for r in rows],
        "summary": {t: state_of(conn, client_id, t) for t in DOC_TYPES},
        "reuse_log": [{"id": r["id"], "doc_type": r["doc_type"], "label": LABELS[r["doc_type"]], "used_for": r["used_for"], "used_for_id": r["used_for_id"],
                       "used_at": r["used_at"], "used_by": r["used_by_name"]} for r in log],
        "verifier": {"name": DemoIdentityVerifier.name, "is_simulated": True,
                     "note": "Demo verification. No identity provider is contacted and nothing about the document itself is checked."},
        "rules": {"proof_of_address_max_age_days": POA_MAX_AGE_DAYS, "expiry_warning_days": EXPIRY_WARNING_DAYS},
    }


def upload(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, *, client_id: Optional[UUID], doc_type: str,
           expiry_date: Optional[date], filename: str, declared_type: Optional[str], data: bytes) -> Dict[str, Any]:
    if doc_type not in DOC_TYPES:
        raise validation("doc_type", "invalid_value", f"doc_type must be one of: {', '.join(DOC_TYPES)}.")
    if p.is_client:
        cid = p.id
    elif p.is_advisor:
        if client_id is None:
            raise validation("client_id", "required", "client_id is required.")
        cid = require_client_in_scope(conn, p, client_id)
    else:
        from app.core.errors import forbidden
        raise forbidden("Only the client or their adviser can add an identity document.")
    content_type = att.validate_upload("id_document", declared_type, data, settings.max_upload_bytes)
    doc_id = uuid4()
    path = f"identity/{cid}/{doc_id}-{safe_filename(filename)}"
    row = fetch_one(conn, "insert into identity_documents (id, client_id, doc_type, filename, content_type, size_bytes, storage_path, status, "
                          "verification_source, expiry_date, uploaded_by) values (%s,%s,%s,%s,%s,%s,%s,'pending','uploaded',%s,%s) returning id",
                    (doc_id, cid, doc_type, safe_filename(filename), content_type, len(data), path, expiry_date, p.id))
    storage.put(settings.attachments_bucket, path, data, content_type)
    audit.record(conn, p, "identity.uploaded", "identity_document", doc_id, client_id=cid, summary=f"Added a {LABELS[doc_type]} to the identity vault",
                 details={"doc_type": doc_type, "content_type": content_type, "size_bytes": len(data)})
    if p.is_client:
        workflow.tell_one(conn, "advisor", cid, kind="identity", title=f"{p.full_name} added a {LABELS[doc_type]}", body="Verify it so it can be reused.",
                          link={"resource": "client", "id": cid})
    return _object(fetch_one(conn, f"{_SELECT} where d.id = %s", (row["id"],)))


def _load(conn: psycopg.Connection, p: Principal, doc_id: UUID, lock: bool = False) -> Row:
    row = fetch_one(conn, f"{_SELECT} where d.id = %s and d.client_id = any(%s)" + (" for update of d" if lock else ""), (doc_id, p.client_ids(conn)))
    if row is None:
        raise not_found("Identity document")
    return row


def verify(conn: psycopg.Connection, p: Principal, doc_id: UUID, expiry_date: Optional[date], issued_date: Optional[date],
           verifier: IdentityVerifier = DemoIdentityVerifier()) -> Dict[str, Any]:
    if not p.is_advisor:
        from app.core.errors import forbidden
        raise forbidden("Only the client's adviser can verify an identity document.")
    row = _load(conn, p, doc_id, lock=True)
    if row["status"] != "pending":
        raise bad_state(f"This document is already {row['status']}.")
    expiry = expiry_date or row["expiry_date"]
    result = verifier.verify(row["doc_type"], row["content_type"], row["size_bytes"], expiry)
    if not result.ok:
        return reject(conn, p, doc_id, result.reason or "Verification failed.")
    execute(conn, "update identity_documents set status = 'superseded' where client_id = %s and doc_type = %s and status = 'verified'", (row["client_id"], row["doc_type"]))
    execute(conn, "update identity_documents set status = 'verified', verification_source = 'simulated_verification', verifier = %s, verified_by = %s, "
                  "verified_at = now(), expiry_date = %s, issued_date = %s where id = %s", (result.verifier, p.id, expiry, issued_date, doc_id))
    if row["doc_type"] == "drivers_licence" and expiry:
        update_row(conn, "clients", row["client_id"], {"drivers_licence_expiry": expiry})     # one licence date; the existing reminder covers it
    audit.record(conn, p, "identity.verified", "identity_document", doc_id, client_id=row["client_id"],
                 summary=f"Verified the {LABELS[row['doc_type']]} (demo verification, not a real KYC check)",
                 details={"doc_type": row["doc_type"], "verifier": result.verifier, "expiry_date": expiry, "simulated": True})
    workflow.tell_one(conn, "client", row["client_id"], kind="identity", title=f"Your {LABELS[row['doc_type']]} was verified",
                      body="It will be reused, so you will not be asked for it again while it is valid.", link={"resource": "client", "id": row["client_id"]})
    return _object(fetch_one(conn, f"{_SELECT} where d.id = %s", (doc_id,)))


def reject(conn: psycopg.Connection, p: Principal, doc_id: UUID, reason: str) -> Dict[str, Any]:
    if not p.is_advisor:
        from app.core.errors import forbidden
        raise forbidden("Only the client's adviser can reject an identity document.")
    row = _load(conn, p, doc_id, lock=True)
    if row["status"] != "pending":
        raise bad_state(f"This document is already {row['status']}.")
    execute(conn, "update identity_documents set status = 'rejected', rejected_reason = %s where id = %s", (reason, doc_id))
    audit.record(conn, p, "identity.rejected", "identity_document", doc_id, client_id=row["client_id"],
                 summary=f"Rejected the {LABELS[row['doc_type']]}", details={"doc_type": row["doc_type"], "reason": reason})
    workflow.tell_one(conn, "client", row["client_id"], kind="identity", title=f"Your {LABELS[row['doc_type']]} could not be accepted", body=reason,
                      link={"resource": "client", "id": row["client_id"]})
    return _object(fetch_one(conn, f"{_SELECT} where d.id = %s", (doc_id,)))


def document_url(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, doc_id: UUID) -> Dict[str, Any]:
    from datetime import timedelta

    row = _load(conn, p, doc_id)
    audit.record(conn, p, "identity.viewed", "identity_document", doc_id, client_id=row["client_id"],
                 summary=f"Opened the {LABELS[row['doc_type']]} file", details={"doc_type": row["doc_type"]})
    return {"url": storage.signed_url(settings.attachments_bucket, row["storage_path"], settings.signed_url_ttl_seconds),
            "expires_at": clock.now() + timedelta(seconds=settings.signed_url_ttl_seconds), "content_type": row["content_type"]}
