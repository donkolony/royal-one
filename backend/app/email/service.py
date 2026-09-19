"""Adviser email (docs/api.md section 5.14): the MockEmailProvider over seeded tables, plus rule-based flags and links.

Everything returned carries `is_simulated: true`. Flags and automatic links are computed on read with deterministic
rules (no LLM); only a manual link is stored. Email bodies are untrusted input.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from uuid import UUID

import psycopg

from app.core.auth import Principal
from app.core.db import Row, execute, fetch_all, fetch_one
from app.core.errors import ApiError, not_found, validation
from app.core.http import Paging
from app.domain import constants as C
from app.schemas.models import EmailLinkBody

_DEADLINE = re.compile(r"\b(deadline|urgent|overdue|asap)\b", re.I)


class Mailbox:
    """Everything needed to classify one adviser's threads, loaded once per request."""

    def __init__(self, conn: psycopg.Connection, p: Principal):
        ids = p.client_ids(conn)
        self.p = p
        self.clients = {r["email"].lower(): r for r in fetch_all(conn, "select id, email, full_name from profiles where id = any(%s)", (ids,))}
        domains: set = set()
        for r in fetch_all(conn, "select email_domains from insurers"):
            domains.update(d.lower() for d in r["email_domains"])
        self.claims = fetch_all(
            conn,
            "select c.id, c.client_id, c.reference, c.insurer_claim_number, c.insurer_handler_email, pr.full_name as client_name "
            "from claims c join profiles pr on pr.id = c.client_id where c.client_id = any(%s) and c.status <> 'draft'",
            (ids,),
        )
        for c in self.claims:
            if c["insurer_handler_email"]:
                domains.add(c["insurer_handler_email"].split("@")[-1].lower())
        self.insurer_domains = domains
        self.claim_by_id = {c["id"]: c for c in self.claims}

    def role_of(self, email: str) -> str:
        e = email.lower()
        if e in self.clients:
            return "client"
        if e.split("@")[-1] in self.insurer_domains:
            return "insurer"
        return "other"

    def participant(self, name: Optional[str], email: str) -> Dict[str, Any]:
        return {"name": name, "email": email, "role": self.role_of(email)}


def _load_threads(conn: psycopg.Connection, p: Principal, thread_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
    sql, params = "select * from email_threads where advisor_id = %s", [p.id]
    if thread_id:
        sql += " and id = %s"
        params.append(thread_id)
    threads = fetch_all(conn, sql, params)
    if not threads:
        return []
    msgs = fetch_all(conn, "select * from email_messages where thread_id = any(%s) order by sent_at, id", ([t["id"] for t in threads],))
    by_thread: Dict[UUID, List[Row]] = {t["id"]: [] for t in threads}
    for m in msgs:
        by_thread[m["thread_id"]].append(m)
    return [{**t, "messages": by_thread[t["id"]]} for t in threads]


def _thread_object(box: Mailbox, t: Dict[str, Any]) -> Dict[str, Any]:
    msgs = t["messages"]
    text = (t["subject"] + "\n" + "\n".join(m["body_text"] for m in msgs)).lower()

    people: Dict[str, Dict[str, Any]] = {}
    for m in msgs:
        people.setdefault(m["from_email"].lower(), box.participant(m["from_name"], m["from_email"]))
        for r in list(m["to_recipients"]) + list(m["cc_recipients"]):
            people.setdefault(r["email"].lower(), box.participant(r.get("name"), r["email"]))
    sender_roles = {box.role_of(m["from_email"]) for m in msgs}

    claim_hit = next(
        (c for c in sorted(box.claims, key=lambda c: c["reference"] or "")
         if (c["reference"] and c["reference"].lower() in text) or (c["insurer_claim_number"] and c["insurer_claim_number"].lower() in text)),
        None,
    )
    flags: List[str] = []
    if "insurer" in sender_roles:
        flags.append("insurer_sender")
    if "client" in sender_roles:
        flags.append("client_sender")
    if claim_hit:
        flags.append("claim_reference_match")
    if _DEADLINE.search(text):
        flags.append("deadline_keyword")

    if t["manual_claim_id"] or t["manual_client_id"]:
        claim = box.claim_by_id.get(t["manual_claim_id"]) if t["manual_claim_id"] else None
        client_id = claim["client_id"] if claim else t["manual_client_id"]
        link = {"client_id": client_id, "claim_id": t["manual_claim_id"], "linked_by": "manual"}
    elif claim_hit:
        link = {"client_id": claim_hit["client_id"], "claim_id": claim_hit["id"], "linked_by": "auto"}
    else:
        client_person = next((pp for pp in people.values() if pp["role"] == "client"), None)
        link = ({"client_id": box.clients[client_person["email"].lower()]["id"], "claim_id": None, "linked_by": "auto"}
                if client_person else {"client_id": None, "claim_id": None, "linked_by": None})

    last = msgs[-1]
    snippet = re.sub(r"\s+", " ", last["body_text"]).strip()
    return {
        "id": t["id"], "subject": t["subject"], "snippet": snippet[:140] + ("…" if len(snippet) > 140 else ""),
        "participants": list(people.values()), "message_count": len(msgs), "last_message_at": last["sent_at"],
        "unread": t["unread"], "importance": "high" if flags else "normal",
        "flags": [{"code": f, "label": C.EMAIL_FLAG_LABELS[f]} for f in flags],
        "link": link, "is_simulated": True,
    }


def status(p: Principal) -> Dict[str, Any]:
    return {"provider": "mock", "is_simulated": True, "connected": True, "account": p.email}


def list_threads(
    conn: psycopg.Connection, p: Principal, paging: Paging, *, client_id: Optional[UUID], claim_id: Optional[UUID],
    flagged: Optional[bool], linked: Optional[bool], unread: Optional[bool], search: Optional[str], sort: Optional[str],
) -> Dict[str, Any]:
    if sort not in (None, "last_message_at", "-last_message_at"):
        raise validation("sort", "invalid_value", "Sort must be last_message_at or -last_message_at.")
    box = Mailbox(conn, p)
    items = [_thread_object(box, t) for t in _load_threads(conn, p) if t["messages"]]
    if client_id:
        items = [t for t in items if t["link"]["client_id"] == client_id]
    if claim_id:
        items = [t for t in items if t["link"]["claim_id"] == claim_id]
    if flagged is not None:
        items = [t for t in items if bool(t["flags"]) == flagged]
    if linked is not None:
        items = [t for t in items if bool(t["link"]["client_id"] or t["link"]["claim_id"]) == linked]
    if unread is not None:
        items = [t for t in items if t["unread"] == unread]
    if search:
        s = search.lower()
        items = [t for t in items if s in t["subject"].lower() or s in t["snippet"].lower()]
    items.sort(key=lambda t: t["last_message_at"], reverse=(sort != "last_message_at"))
    return paging.envelope(items[paging.offset: paging.offset + paging.limit], len(items))


def _one(conn: psycopg.Connection, p: Principal, thread_id: UUID) -> Dict[str, Any]:
    rows = _load_threads(conn, p, thread_id)
    if not rows or not rows[0]["messages"]:
        raise not_found("Email thread")
    return rows[0]


def get_thread(conn: psycopg.Connection, p: Principal, thread_id: UUID) -> Dict[str, Any]:
    t = _one(conn, p, thread_id)
    box = Mailbox(conn, p)
    messages = [
        {
            "id": m["id"], "from": box.participant(m["from_name"], m["from_email"]),
            "to": [box.participant(r.get("name"), r["email"]) for r in m["to_recipients"]],
            "cc": [box.participant(r.get("name"), r["email"]) for r in m["cc_recipients"]],
            "sent_at": m["sent_at"], "body_text": m["body_text"], "has_attachments": m["has_attachments"],
        }
        for m in t["messages"]
    ]
    execute(conn, "update email_threads set unread = false where id = %s", (thread_id,))
    obj = _thread_object(box, t)
    obj["unread"] = False
    return {"thread": obj, "messages": messages}


def set_link(conn: psycopg.Connection, p: Principal, thread_id: UUID, body: EmailLinkBody) -> Dict[str, Any]:
    _one(conn, p, thread_id)  # 404 unless this is the adviser's own thread
    if body.claim_id is None and body.client_id is None:
        raise validation("claim_id", "required", "Provide claim_id or client_id.")
    ids = p.client_ids(conn)
    client_id = body.client_id
    if body.claim_id:
        claim = fetch_one(conn, "select id, client_id from claims where id = %s and client_id = any(%s) and status <> 'draft'", (body.claim_id, ids))
        if claim is None:
            raise validation("claim_id", "invalid_value", "Choose one of your clients' claims.")
        if client_id and client_id != claim["client_id"]:
            raise validation("client_id", "invalid_value", "That claim belongs to a different client.")
        client_id = claim["client_id"]
    elif client_id not in ids:
        raise validation("client_id", "invalid_value", "Choose one of your clients.")
    execute(conn, "update email_threads set manual_client_id = %s, manual_claim_id = %s where id = %s", (client_id, body.claim_id, thread_id))
    return _thread_object(Mailbox(conn, p), _one(conn, p, thread_id))


def clear_link(conn: psycopg.Connection, p: Principal, thread_id: UUID) -> None:
    _one(conn, p, thread_id)
    execute(conn, "update email_threads set manual_client_id = null, manual_claim_id = null where id = %s", (thread_id,))


def flagged_unread(conn: psycopg.Connection, p: Principal) -> List[Dict[str, Any]]:
    box = Mailbox(conn, p)
    out = []
    for t in _load_threads(conn, p):
        if not t["messages"] or not t["unread"]:
            continue
        obj = _thread_object(box, t)
        if obj["flags"]:
            client = None
            if obj["link"]["client_id"]:
                row = fetch_one(conn, "select id, full_name from profiles where id = %s", (obj["link"]["client_id"],))
                client = {"id": row["id"], "full_name": row["full_name"]} if row else None
            out.append({"id": obj["id"], "subject": obj["subject"], "last_message_at": obj["last_message_at"], "client": client})
    out.sort(key=lambda t: t["last_message_at"], reverse=True)
    return out


def oauth_not_built() -> ApiError:
    return ApiError(501, "not_implemented", "Live Gmail is not available in this build. Email is simulated.")
