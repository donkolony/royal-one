"""Synthetic demo data. Used by `scripts/seed.py` and by the tests, so the tests also verify the demo dataset.

All people, numbers and addresses are invented. Emails use the reserved `.example` domain. Dates are relative to
"today" so reminders and stale-claim alerts always have something to show.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import NAMESPACE_URL, UUID, uuid5

import psycopg
from psycopg.types.json import Jsonb

from app.core import clock
from app.core.config import Settings
from app.core.db import execute, fetch_one
from app.storage.base import Storage

# 1x1 transparent PNG: a valid image placeholder for seeded attachments.
PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082"
)


def uid(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"royal-square-demo/{name}")


ADVISER = uid("adviser-1")
ADVISER_2 = uid("adviser-2")
OWNER = uid("owner-1")
CLIENT_1, CLIENT_2, CLIENT_3, CLIENT_4 = (uid(f"client-{i}") for i in range(1, 5))

USERS: List[Dict[str, Any]] = [
    {"id": OWNER, "role": "owner", "full_name": "Demo Owner", "email": "owner@demo.example", "phone": "+27 82 000 0900"},
    {"id": ADVISER, "role": "advisor", "full_name": "Demo Adviser", "email": "adviser@demo.example", "phone": "+27 82 000 0100"},
    {"id": ADVISER_2, "role": "advisor", "full_name": "Other Adviser", "email": "adviser2@demo.example", "phone": "+27 82 000 0200"},
    {"id": CLIENT_1, "role": "client", "full_name": "Demo Client One", "email": "client1@demo.example", "phone": "+27 82 000 0001"},
    {"id": CLIENT_2, "role": "client", "full_name": "Demo Client Two", "email": "client2@demo.example", "phone": "+27 82 000 0002"},
    {"id": CLIENT_3, "role": "client", "full_name": "Demo Client Three", "email": "client3@demo.example", "phone": "+27 82 000 0003"},
    {"id": CLIENT_4, "role": "client", "full_name": "Other Client", "email": "client4@demo.example", "phone": "+27 82 000 0004"},
]

TABLES = [
    "audit_log", "email_messages", "email_threads", "assistant_messages", "assistant_conversations", "document_chunks", "documents",
    "attachments", "requests", "claim_events", "claims", "reminders", "goal_participants", "goals", "financial_items",
    "policies", "clients", "profiles",
]


def reset_data(conn: psycopg.Connection) -> None:
    """Empty every data table (reference data such as insurers stays). The audit log is append-only; the reset is the one
    place allowed to empty it, for this transaction only (migration 0003)."""
    execute(conn, "set local app.audit_reset = 'on'")
    execute(conn, f"truncate {', '.join(TABLES)} restart identity cascade")
    execute(conn, "alter sequence claim_reference_seq restart with 1")


def _insurer(conn: psycopg.Connection, name: str) -> UUID:
    return fetch_one(conn, "select id from insurers where name = %s", (name,))["id"]


def _ago(**kw) -> datetime:
    return clock.now() - timedelta(**kw)


def _event(conn, claim: UUID, type_: str, title: str, at: datetime, *, message=None, visible=True, frm=None, to=None, actor=None) -> None:
    execute(
        conn,
        "insert into claim_events (claim_id, type, title, message, visible_to_client, from_status, to_status, actor_id, created_at) "
        "values (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (claim, type_, title, message, visible, frm, to, actor, at),
    )


def _attach(conn, settings: Settings, storage: Storage, claim: UUID, uploader: UUID, kind: str, filename: str) -> None:
    att_id = uid(f"att-{claim}-{kind}")
    path = f"claims/{claim}/{att_id}-{filename}"
    execute(
        conn,
        "insert into attachments (id, claim_id, kind, label, storage_path, filename, content_type, size_bytes, uploaded_by) "
        "values (%s,%s,%s,%s,%s,%s,'image/png',%s,%s)",
        (att_id, claim, kind, None, path, filename, len(PNG_1X1), uploader),
    )
    storage.put(settings.attachments_bucket, path, PNG_1X1, "image/png")


def seed_demo(conn: psycopg.Connection, settings: Settings, storage: Storage) -> Dict[str, Any]:
    """Insert the demo dataset. Assumes empty data tables (call reset_data first when re-seeding)."""
    today = clock.today()
    ins = {n: _insurer(conn, n) for n in ("Sanlam", "Old Mutual", "Liberty", "Momentum", "Discovery", "Allan Gray", "Santam", "Other")}
    for name, iid in ins.items():  # synthetic sender domains so the simulated mailbox can recognise insurers
        execute(conn, "update insurers set email_domains = %s where id = %s", ([f"{name.lower().replace(' ', '')}.demo.example"], iid))

    for u in USERS:
        execute(conn, "insert into profiles (id, role, full_name, email, phone) values (%(id)s,%(role)s,%(full_name)s,%(email)s,%(phone)s)", u)

    def add_client(cid: UUID, adviser: UUID, dob: date, since: date, licence: Optional[date], review: Optional[date]) -> None:
        execute(
            conn,
            "insert into clients (id, adviser_id, date_of_birth, client_since, drivers_licence_expiry, last_annual_review_date) values (%s,%s,%s,%s,%s,%s)",
            (cid, adviser, dob, since, licence, review),
        )

    def shift_year(d: date, years: int) -> date:
        try:
            return d.replace(year=d.year + years)
        except ValueError:
            return d.replace(year=d.year + years, day=28)

    add_client(CLIENT_1, ADVISER, shift_year(today + timedelta(days=5), -37), shift_year(today + timedelta(days=3), -5),
               today + timedelta(days=40), shift_year(today + timedelta(days=20), -1))
    add_client(CLIENT_2, ADVISER, date(1986, 7, 22), date(2020, 2, 10), today + timedelta(days=400), None)
    add_client(CLIENT_3, ADVISER, date(1975, 11, 3), date(2018, 8, 1), today - timedelta(days=10), shift_year(today - timedelta(days=100), -1))
    add_client(CLIENT_4, ADVISER_2, date(1990, 1, 15), date(2022, 6, 1), None, None)

    def policy(name: str, client: UUID, insurer: str, category: str, product: str, number: str, **kw) -> UUID:
        pid = uid(f"policy-{name}")
        cols = {"id": pid, "client_id": client, "insurer_id": ins[insurer], "category": category, "product_name": product,
                "policy_number": number, "status": "active", **kw}
        execute(conn, f"insert into policies ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))})", list(cols.values()))
        return pid

    motor1 = policy("c1-motor", CLIENT_1, "Santam", "motor", "Comprehensive vehicle cover", "DEMO-MOT-1001",
                    asset_description="2021 Demo Hatchback (CA 000-101)", cover_amount_cents=28000000, premium_cents=115000, premium_frequency="monthly",
                    start_date=date(2021, 3, 1), renewal_date=today + timedelta(days=120),
                    valuation_certificate_date=shift_year(today + timedelta(days=25), -2))
    policy("c1-life", CLIENT_1, "Sanlam", "life", "Life cover", "DEMO-LIFE-1002", cover_amount_cents=200000000, premium_cents=95000, premium_frequency="monthly")
    policy("c1-invest", CLIENT_1, "Allan Gray", "investment", "Discretionary investment", "DEMO-INV-1003", current_value_cents=25000000)
    policy("c1-retire", CLIENT_1, "Old Mutual", "retirement", "Retirement annuity", "DEMO-RA-1004", current_value_cents=180000000,
           renewal_date=today + timedelta(days=15))
    motor2 = policy("c2-motor", CLIENT_2, "Santam", "motor", "Comprehensive vehicle cover", "DEMO-MOT-2001",
                    asset_description="2019 Demo Sedan (CA 000-202)", cover_amount_cents=21000000, premium_cents=98000, premium_frequency="monthly")
    policy("c2-health", CLIENT_2, "Discovery", "health", "Medical aid", "DEMO-HLT-2002", premium_cents=280000, premium_frequency="monthly")
    policy("c3-funeral", CLIENT_3, "Liberty", "funeral", "Family funeral plan", "DEMO-FUN-3001", cover_amount_cents=5000000)
    policy("c4-motor", CLIENT_4, "Santam", "motor", "Comprehensive vehicle cover", "DEMO-MOT-4001", asset_description="2020 Demo SUV (CA 000-404)")

    def item(client: UUID, kind: str, category: str, label: str, cents: int) -> None:
        execute(conn, "insert into financial_items (client_id, kind, category, label, amount_cents, as_of_date) values (%s,%s,%s,%s,%s,%s)",
                (client, kind, category, label, cents, today))

    item(CLIENT_1, "asset", "property", "Family home", 240000000)
    item(CLIENT_1, "asset", "vehicle", "Vehicle", 22000000)
    item(CLIENT_1, "asset", "cash", "Savings", 8500000)
    item(CLIENT_1, "liability", "home_loan", "Home loan", 165000000)
    item(CLIENT_1, "liability", "vehicle_finance", "Vehicle finance", 11000000)
    item(CLIENT_2, "asset", "cash", "Savings", 4200000)
    item(CLIENT_2, "liability", "credit_card", "Credit card", 1500000)

    def goal(name: str, clients: List[UUID], title: str, category: str, target: int, current: int, target_date: Optional[date]) -> None:
        gid = uid(f"goal-{name}")
        execute(conn, "insert into goals (id, title, category, target_amount_cents, current_amount_cents, target_date, created_by) values (%s,%s,%s,%s,%s,%s,%s)",
                (gid, title, category, target, current, target_date, ADVISER))
        for c in clients:
            execute(conn, "insert into goal_participants (goal_id, client_id) values (%s,%s)", (gid, c))

    goal("retire", [CLIENT_1], "Retire at 60", "retirement", 500000000, 180000000, date(today.year + 20, 6, 30))
    goal("emergency", [CLIENT_1], "Emergency fund", "emergency_fund", 10000000, 6500000, today + timedelta(days=365))
    goal("education", [CLIENT_1, CLIENT_2], "Children's university fund", "education", 60000000, 15000000, date(today.year + 12, 1, 31))
    goal("travel", [CLIENT_3], "Family holiday", "travel", 8000000, 8000000, None)

    execute(conn, "update goals set status = 'achieved' where id = %s", (uid("goal-travel"),))
    execute(
        conn,
        "insert into reminders (client_id, type, title, due_date, audience, source, created_by) values (%s,'custom','Call about fund switch',%s,'advisor','manual',%s)",
        (CLIENT_1, today + timedelta(days=6), ADVISER),
    )

    # ------------------------------------------------------------------------------------------ claims
    def claim(name: str, client: UUID, status: str, insurer: str, policy_id: Optional[UUID], **kw) -> UUID:
        cid = uid(f"claim-{name}")
        cols = {"id": cid, "client_id": client, "policy_id": policy_id, "insurer_id": ins[insurer], "status": status, **kw}
        execute(conn, f"insert into claims ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))})", [Jsonb(v) if isinstance(v, (list, dict)) else v for v in cols.values()])
        return cid

    common = dict(police_reported=True, police_station="Cape Town Central", driver_is_policyholder=True, vehicle_use="personal",
                  witnesses=[{"name": "J. Dlamini", "phone": "+27 82 000 0555", "email": None, "statement": None}],
                  third_parties=[{"name": "A. Other", "phone": "+27 82 000 0666", "drivers_licence_number": None, "vehicle_registration": "CA 000-666",
                                  "vehicle_make_model": "Demo Hatchback", "insurer_name": "Some Insurer", "policy_number": "POL-999"}])

    # 1. Fresh submission waiting for the adviser.
    n1 = fetch_one(conn, "select nextval('claim_reference_seq') as n")["n"]
    c_sub = claim("submitted", CLIENT_1, "submitted", "Santam", motor1, reference=f"CLM-{today.year}-{n1:04d}",
                  incident_occurred_at=_ago(hours=20), incident_location_text="Corner of Buitenkant St and Roeland St, Cape Town",
                  incident_description="Rear-ended by a white hatchback while stopped at a red light.",
                  police_case_number="CAS 123/09/2026", driver_full_name="Demo Client One", submitted_at=_ago(hours=2),
                  status_changed_at=_ago(hours=2), **common)
    _event(conn, c_sub, "created", "Claim started", _ago(hours=3), actor=CLIENT_1)
    _event(conn, c_sub, "submitted", "Claim sent to Royal Square", _ago(hours=2), frm="draft", to="submitted", actor=CLIENT_1)
    _attach(conn, settings, storage, c_sub, CLIENT_1, "vehicle_photo", "rear-bumper.png")
    _attach(conn, settings, storage, c_sub, CLIENT_1, "drivers_licence", "licence.png")

    # 2. Registered with the insurer and in assessment.
    n2 = fetch_one(conn, "select nextval('claim_reference_seq') as n")["n"]
    c_ass = claim("assessment", CLIENT_2, "assessment", "Santam", motor2, reference=f"CLM-{today.year}-{n2:04d}",
                  incident_occurred_at=_ago(days=6), incident_location_text="N2 near Somerset West",
                  incident_description="Hit a pothole and damaged the front left wheel and suspension.",
                  police_case_number="CAS 456/09/2026", driver_full_name="Demo Client Two",
                  insurer_claim_number="SC-778201", insurer_handler_name="Demo Handler", insurer_handler_email="handler@santam.demo.example",
                  submitted_at=_ago(days=5), status_changed_at=_ago(days=2), **common)
    _event(conn, c_ass, "created", "Claim started", _ago(days=5, hours=1), actor=CLIENT_2)
    _event(conn, c_ass, "submitted", "Claim sent to Royal Square", _ago(days=5), frm="draft", to="submitted", actor=CLIENT_2)
    _event(conn, c_ass, "status_changed", "Registered with your insurer", _ago(days=4), message="Claim number SC-778201", frm="submitted", to="registered", actor=ADVISER)
    _event(conn, c_ass, "status_changed", "Vehicle assessment", _ago(days=2), frm="registered", to="assessment", actor=ADVISER)
    _event(conn, c_ass, "note", "Note added", _ago(days=2), message="Client will take the vehicle in on Thursday.", visible=False, actor=ADVISER)
    _attach(conn, settings, storage, c_ass, CLIENT_2, "vehicle_photo", "front-wheel.png")
    _attach(conn, settings, storage, c_ass, CLIENT_2, "drivers_licence", "licence.png")

    # 3. In repair for over a week (shows the "stale claim" alert) with a hire car.
    n3 = fetch_one(conn, "select nextval('claim_reference_seq') as n")["n"]
    c_rep = claim("in-repair", CLIENT_3, "in_repair", "Liberty", None, reference=f"CLM-{today.year}-{n3:04d}",
                  incident_occurred_at=_ago(days=30), incident_location_text="Voortrekker Rd, Parow",
                  incident_description="Side-swiped in a parking area; damage to the left rear door.",
                  police_case_number="CAS 789/08/2026", driver_full_name="Demo Client Three",
                  insurer_claim_number="LB-55012", insurer_handler_name="Demo Handler Two", insurer_handler_email="claims@liberty.demo.example",
                  repair_repairer_name="Demo Panelbeaters", repair_quote_amount_cents=1850000, repair_authorised_amount_cents=1850000,
                  repair_drop_off_date=today - timedelta(days=8), repair_estimated_completion_date=today + timedelta(days=4),
                  hire_car_status="delivered", hire_car_provider="Demo Car Hire", hire_car_delivery_date=today - timedelta(days=8),
                  submitted_at=_ago(days=28), status_changed_at=_ago(days=9), **common)
    _event(conn, c_rep, "submitted", "Claim sent to Royal Square", _ago(days=28), frm="draft", to="submitted", actor=CLIENT_3)
    _event(conn, c_rep, "status_changed", "Being repaired", _ago(days=9), frm="authorised", to="in_repair", actor=ADVISER)
    _event(conn, c_rep, "hire_car_updated", "Hire car delivered to the repairer", _ago(days=8), actor=ADVISER)
    _event(conn, c_rep, "repair_update", "Repair update", _ago(days=2), message="Panel beating complete; spray painting starts Monday.", actor=ADVISER)
    _attach(conn, settings, storage, c_rep, CLIENT_3, "vehicle_photo", "door.png")
    _attach(conn, settings, storage, c_rep, CLIENT_3, "drivers_licence", "licence.png")

    # 4. A draft that only its client can see.
    c_draft = claim("draft", CLIENT_1, "draft", "Santam", motor1)
    _event(conn, c_draft, "created", "Claim started", _ago(minutes=30), actor=CLIENT_1)

    # ------------------------------------------------------------------------------------------ requests
    def request(name: str, client: UUID, type_: str, status: str, payload: Dict[str, Any], **kw) -> None:
        execute(conn, "insert into requests (id, client_id, type, status, payload, client_note, submitted_at) values (%s,%s,%s,%s,%s,%s,%s)",
                (uid(f"request-{name}"), client, type_, status, Jsonb(payload), kw.get("note"), kw.get("at", _ago(hours=5))))

    request("address", CLIENT_1, "address_change", "submitted", {
        "address_line_1": "12 Example Road", "address_line_2": None, "suburb": "Gardens", "city": "Cape Town", "postal_code": "8001", "effective_date": None},
        note="Moved last week.", at=_ago(hours=5))
    request("bank", CLIENT_1, "bank_details_change", "submitted", {
        "account_holder": "Demo Client One", "bank_name": "Demo Bank", "account_type": "savings", "account_number": "1234567890",
        "branch_code": "123456", "effective_date": None}, at=_ago(hours=1))
    request("consult", CLIENT_2, "consultation", "in_progress", {
        "preferred_dates": [(today + timedelta(days=7)).isoformat()], "mode": "video", "topic": "Review my retirement savings"}, at=_ago(days=1))
    request("polydoc", CLIENT_2, "policy_document", "completed", {"policy_id": str(motor2), "document_kind": "policy_schedule"}, at=_ago(days=6))
    execute(conn, "update requests set adviser_response = 'Sent to your email.', handled_by = %s, completed_at = %s where id = %s",
            (ADVISER, _ago(days=5), uid("request-polydoc")))

    # ------------------------------------------------------------------------------------- simulated mailbox
    def thread(name: str, subject: str, unread: bool, messages: List[Dict[str, Any]]) -> None:
        tid = uid(f"thread-{name}")
        execute(conn, "insert into email_threads (id, advisor_id, subject, unread) values (%s,%s,%s,%s)", (tid, ADVISER, subject, unread))
        for i, m in enumerate(messages):
            execute(
                conn,
                "insert into email_messages (id, thread_id, from_name, from_email, to_recipients, cc_recipients, sent_at, body_text, has_attachments) "
                "values (%s,%s,%s,%s,%s,'[]',%s,%s,%s)",
                (uid(f"msg-{name}-{i}"), tid, m["from_name"], m["from_email"], Jsonb(m["to"]), m["at"], m["body"], m.get("attachments", False)),
            )

    me = {"name": "Demo Adviser", "email": "adviser@demo.example"}
    handler = {"name": "Demo Handler", "email": "handler@santam.demo.example"}
    thread("assessment", "Claim SC-778201: assessment appointment", True, [
        {"from_name": "Demo Adviser", "from_email": me["email"], "to": [handler], "at": _ago(days=2, hours=2),
         "body": "Hello Demo Handler,\n\nPlease confirm the assessment centre for the vehicle on claim SC-778201."},
        {"from_name": "Demo Handler", "from_email": handler["email"], "to": [me], "at": _ago(hours=3),
         "body": "Please book the vehicle in for assessment by Friday. This is urgent: the quote deadline is next week."},
    ])
    thread("client-question", "Where is my claim?", True, [
        {"from_name": "Demo Client One", "from_email": "client1@demo.example", "to": [me], "at": _ago(hours=1),
         "body": f"Hi, I sent my claim yesterday (CLM-{today.year}-{n1:04d}). Has the insurer come back yet?"},
    ])
    thread("newsletter", "Industry newsletter", False, [
        {"from_name": "Demo Newsletter", "from_email": "news@publisher.example", "to": [me], "at": _ago(days=3),
         "body": "This month in insurance: nothing that concerns a specific client."},
    ])
    return {"claims": {"submitted": c_sub, "assessment": c_ass, "in_repair": c_rep, "draft": c_draft}, "policies": {"c1_motor": motor1, "c2_motor": motor2}}
