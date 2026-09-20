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
from app.core.auth import Principal
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
CLIENT_5, CLIENT_6, CLIENT_7, CLIENT_8, CLIENT_9, CLIENT_10, CLIENT_11, CLIENT_12 = (uid(f"client-{i}") for i in range(5, 13))

USERS: List[Dict[str, Any]] = [
    {"id": OWNER, "role": "owner", "full_name": "Nomsa Dube", "email": "owner@demo.example", "phone": "+27 82 000 0900"},
    {"id": ADVISER, "role": "advisor", "full_name": "Sarah van der Merwe", "email": "adviser@demo.example", "phone": "+27 82 000 0100"},
    {"id": ADVISER_2, "role": "advisor", "full_name": "Priya Naidoo", "email": "adviser2@demo.example", "phone": "+27 82 000 0200"},
    {"id": CLIENT_1, "role": "client", "full_name": "Thabo Mokoena", "email": "client1@demo.example", "phone": "+27 82 000 0001"},
    {"id": CLIENT_2, "role": "client", "full_name": "Lerato Dlamini", "email": "client2@demo.example", "phone": "+27 82 000 0002"},
    {"id": CLIENT_3, "role": "client", "full_name": "Johan Smit", "email": "client3@demo.example", "phone": "+27 82 000 0003"},
    {"id": CLIENT_4, "role": "client", "full_name": "Ayanda Khumalo", "email": "client4@demo.example", "phone": "+27 82 000 0004"},
]

TABLES = [
    "notifications", "request_events", "opportunity_events", "opportunities", "life_events", "identity_reuse_log", "identity_documents",
    "consents", "advice_records", "audit_log", "email_messages", "email_threads", "assistant_messages", "assistant_conversations", "document_chunks", "documents",
    "attachments", "requests", "claim_events", "claims", "reminders", "goal_participants", "goals", "financial_items",
    "policies", "clients", "profiles",
]


def reset_data(conn: psycopg.Connection, keep_documents: bool = False) -> None:
    """Empty every data table (reference data such as insurers stays). The audit log is append-only; the reset is the one
    place allowed to empty it, for this transaction only (migration 0003)."""
    execute(conn, "set local app.audit_reset = 'on'")
    tables = [t for t in TABLES if not (keep_documents and t in ("documents", "document_chunks"))]
    execute(conn, f"truncate {', '.join(tables)} restart identity cascade")
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
                  police_case_number="CAS 123/09/2026", driver_full_name="Thabo Mokoena", submitted_at=_ago(hours=2),
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
                  police_case_number="CAS 456/09/2026", driver_full_name="Lerato Dlamini",
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
                  police_case_number="CAS 789/08/2026", driver_full_name="Johan Smit",
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
        "account_holder": "Thabo Mokoena", "bank_name": "Demo Bank", "account_type": "savings", "account_number": "1234567890",
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

    me = {"name": "Sarah van der Merwe", "email": "adviser@demo.example"}
    handler = {"name": "Demo Handler", "email": "handler@santam.demo.example"}
    thread("assessment", "Claim SC-778201: assessment appointment", True, [
        {"from_name": "Sarah van der Merwe", "from_email": me["email"], "to": [handler], "at": _ago(days=2, hours=2),
         "body": "Hello Demo Handler,\n\nPlease confirm the assessment centre for the vehicle on claim SC-778201."},
        {"from_name": "Demo Handler", "from_email": handler["email"], "to": [me], "at": _ago(hours=3),
         "body": "Please book the vehicle in for assessment by Friday. This is urgent: the quote deadline is next week."},
    ])
    thread("client-question", "Where is my claim?", True, [
        {"from_name": "Thabo Mokoena", "from_email": "client1@demo.example", "to": [me], "at": _ago(hours=1),
         "body": f"Hi, I sent my claim yesterday (CLM-{today.year}-{n1:04d}). Has the insurer come back yet?"},
    ])
    thread("newsletter", "Industry newsletter", False, [
        {"from_name": "Demo Newsletter", "from_email": "news@publisher.example", "to": [me], "at": _ago(days=3),
         "body": "This month in insurance: nothing that concerns a specific client."},
    ])
    return {"claims": {"submitted": c_sub, "assessment": c_ass, "in_repair": c_rep, "draft": c_draft}, "policies": {"c1_motor": motor1, "c2_motor": motor2}}


# ================================================================================================== extended demo dataset
# The base dataset above is small and stable: the original test-suite asserts on it. The extended dataset is layered on top
# of it by `seed_all` (scripts/seed.py, the demo reset and the tests that need it). It gives the Opportunity Radar, the
# owner's Business Health view and the compliance work realistic material: rand amounts, South African names, a mix of
# clients who need attention and one who is fully covered. Everyone is fictional; emails use the reserved .example domain.
EXTENDED_USERS: List[Dict[str, Any]] = [
    {"id": CLIENT_5, "role": "client", "full_name": "Sipho Nkosi", "email": "client5@demo.example", "phone": "+27 82 000 0005"},
    {"id": CLIENT_6, "role": "client", "full_name": "Fatima Patel", "email": "client6@demo.example", "phone": "+27 82 000 0006"},
    {"id": CLIENT_7, "role": "client", "full_name": "Pieter Botha", "email": "client7@demo.example", "phone": "+27 82 000 0007"},
    {"id": CLIENT_8, "role": "client", "full_name": "Zanele Mthembu", "email": "client8@demo.example", "phone": "+27 82 000 0008"},
    {"id": CLIENT_9, "role": "client", "full_name": "Kagiso Molefe", "email": "client9@demo.example", "phone": "+27 82 000 0009"},
    {"id": CLIENT_10, "role": "client", "full_name": "Michelle Jacobs", "email": "client10@demo.example", "phone": "+27 82 000 0010"},
    {"id": CLIENT_11, "role": "client", "full_name": "Ruan Pretorius", "email": "client11@demo.example", "phone": "+27 82 000 0011"},
    {"id": CLIENT_12, "role": "client", "full_name": "Nomvula Zulu", "email": "client12@demo.example", "phone": "+27 82 000 0012"},
]
ALL_USERS: List[Dict[str, Any]] = USERS + EXTENDED_USERS


def _years_ago(today: date, years: int, days: int = 0) -> date:
    d = today - timedelta(days=days)
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        return d.replace(year=d.year - years, day=28)


def seed_extended(conn: psycopg.Connection, settings: Settings, storage: Storage) -> None:
    """Layer the richer demo data over `seed_demo`. Call `seed_demo` first."""
    today = clock.today()
    ins = {r["name"]: r["id"] for r in conn.execute("select id, name from insurers").fetchall()}

    for u in EXTENDED_USERS:
        execute(conn, "insert into profiles (id, role, full_name, email, phone) values (%(id)s,%(role)s,%(full_name)s,%(email)s,%(phone)s)", u)

    def client(cid: UUID, adviser: UUID, dob: date, since: date, licence: Optional[date], review: Optional[date],
               dependants: Optional[int], income_rand: Optional[int]) -> None:
        execute(conn, "insert into clients (id, adviser_id, date_of_birth, client_since, drivers_licence_expiry, last_annual_review_date, "
                      "dependants, annual_income_cents) values (%s,%s,%s,%s,%s,%s,%s,%s)",
                (cid, adviser, dob, since, licence, review, dependants, income_rand * 100 if income_rand else None))

    def policy(key: str, cid: UUID, insurer: str, category: str, product: str, number: str, **kw) -> UUID:
        pid = uid(f"policy-{key}")
        cols = {"id": pid, "client_id": cid, "insurer_id": ins[insurer], "category": category, "product_name": product,
                "policy_number": number, "status": "active", **kw}
        execute(conn, f"insert into policies ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))})", list(cols.values()))
        return pid

    def item(cid: UUID, kind: str, category: str, label: str, rand_amount: int) -> None:
        execute(conn, "insert into financial_items (client_id, kind, category, label, amount_cents, as_of_date) values (%s,%s,%s,%s,%s,%s)",
                (cid, kind, category, label, rand_amount * 100, today))

    def goal(key: str, cids: List[UUID], title: str, category: str, target: int, current: int, target_date: Optional[date], created_days_ago: int) -> None:
        gid = uid(f"goal-{key}")
        execute(conn, "insert into goals (id, title, category, target_amount_cents, current_amount_cents, target_date, created_by, created_at) "
                      "values (%s,%s,%s,%s,%s,%s,%s,%s)", (gid, title, category, target * 100, current * 100, target_date, ADVISER, clock.now() - timedelta(days=created_days_ago)))
        for c in cids:
            execute(conn, "insert into goal_participants (goal_id, client_id) values (%s,%s)", (gid, c))

    def event(cid: UUID, kind: str, days_ago: int, note: Optional[str] = None) -> None:
        execute(conn, "insert into life_events (client_id, kind, occurred_on, note, recorded_by) values (%s,%s,%s,%s,%s)",
                (cid, kind, today - timedelta(days=days_ago), note, ADVISER))

    # ---- the base clients gain the two fields the under-insurance rule needs, and a home for Thabo's life-cover story
    for cid, deps, income in ((CLIENT_1, 2, 850_000), (CLIENT_2, 0, 420_000)):
        execute(conn, "update clients set dependants = %s, annual_income_cents = %s where id = %s", (deps, income * 100, cid))
    execute(conn, "update goals set created_at = %s where id = %s", (clock.now() - timedelta(days=200), uid("goal-emergency")))

    # ---- Sarah van der Merwe's additional clients
    client(CLIENT_5, ADVISER, _years_ago(today, 38, 120), _years_ago(today, 3, 20), today + timedelta(days=300), today - timedelta(days=150), 2, 720_000)
    policy("c5-life", CLIENT_5, "Old Mutual", "life", "Life cover", "DEMO-LIFE-5001", cover_amount_cents=100_000_000, premium_cents=65_000, premium_frequency="monthly")
    policy("c5-fun", CLIENT_5, "Liberty", "funeral", "Family funeral plan", "DEMO-FUN-5002", cover_amount_cents=5_000_000, premium_cents=18_000, premium_frequency="monthly")
    policy("c5-motor", CLIENT_5, "Santam", "motor", "Comprehensive vehicle cover", "DEMO-MOT-5003", cover_amount_cents=28_000_000,
           premium_cents=115_000, premium_frequency="monthly", renewal_date=today + timedelta(days=200))
    item(CLIENT_5, "asset", "property", "Family home in Centurion", 2_100_000)
    item(CLIENT_5, "asset", "vehicle", "Vehicle", 280_000)
    item(CLIENT_5, "liability", "home_loan", "Home loan", 1_600_000)
    item(CLIENT_5, "liability", "vehicle_finance", "Vehicle finance", 180_000)

    client(CLIENT_6, ADVISER, _years_ago(today, 34, 200), _years_ago(today, 2, 40), today + timedelta(days=500), today - timedelta(days=80), 1, None)
    policy("c6-life", CLIENT_6, "Discovery", "life", "Life cover", "DEMO-LIFE-6001", cover_amount_cents=50_000_000, premium_cents=42_000, premium_frequency="monthly")
    policy("c6-health", CLIENT_6, "Discovery", "health", "Medical aid", "DEMO-HLT-6002", premium_cents=265_000, premium_frequency="monthly")
    item(CLIENT_6, "asset", "cash", "Savings", 60_000)
    goal("c6-deposit", [CLIENT_6], "Home deposit", "property", 300_000, 60_000, today + timedelta(days=550), 365)
    event(CLIENT_6, "new_baby", 25, "A daughter, born in Johannesburg")

    client(CLIENT_7, ADVISER, _years_ago(today, 59, 40), _years_ago(today, 9), today + timedelta(days=700), today - timedelta(days=120), 0, 1_100_000)
    policy("c7-ra", CLIENT_7, "Old Mutual", "retirement", "Retirement annuity", "DEMO-RA-7001", current_value_cents=310_000_000,
           renewal_date=today + timedelta(days=20))
    policy("c7-life", CLIENT_7, "Sanlam", "life", "Life cover", "DEMO-LIFE-7002", cover_amount_cents=500_000_000, premium_cents=180_000, premium_frequency="monthly")
    policy("c7-home", CLIENT_7, "Santam", "personal_other", "Homeowners cover", "DEMO-HOM-7003", cover_amount_cents=350_000_000, premium_cents=95_000, premium_frequency="monthly")
    policy("c7-dis", CLIENT_7, "Momentum", "disability", "Income protection", "DEMO-DIS-7004", cover_amount_cents=80_000_000, premium_cents=120_000, premium_frequency="monthly")
    item(CLIENT_7, "asset", "property", "Home in Somerset West", 3_500_000)
    goal("c7-retire", [CLIENT_7], "Retire at 60", "retirement", 6_000_000, 3_100_000, today + timedelta(days=250), 1825)

    client(CLIENT_8, ADVISER, _years_ago(today, 31), _years_ago(today, 4, 30), today + timedelta(days=900), today - timedelta(days=200), None, None)
    policy("c8-health", CLIENT_8, "Momentum", "health", "Medical aid", "DEMO-HLT-8001", premium_cents=190_000, premium_frequency="monthly")

    client(CLIENT_9, ADVISER, _years_ago(today, 44), _years_ago(today, 5), today + timedelta(days=25), today - timedelta(days=100), None, None)
    policy("c9-motor", CLIENT_9, "Santam", "motor", "Comprehensive vehicle cover", "DEMO-MOT-9001", status="lapsed", cover_amount_cents=21_000_000,
           premium_cents=98_000, premium_frequency="monthly")
    policy("c9-life", CLIENT_9, "Sanlam", "life", "Life cover", "DEMO-LIFE-9002", cover_amount_cents=80_000_000, premium_cents=38_000, premium_frequency="monthly")
    item(CLIENT_9, "asset", "vehicle", "Vehicle", 210_000)

    client(CLIENT_10, ADVISER, _years_ago(today, 47, 90), _years_ago(today, 7), today + timedelta(days=800), today - timedelta(days=90), 1, 600_000)
    policy("c10-life", CLIENT_10, "Discovery", "life", "Life cover", "DEMO-LIFE-10001", cover_amount_cents=300_000_000, premium_cents=210_000, premium_frequency="monthly")
    policy("c10-motor", CLIENT_10, "Santam", "motor", "Comprehensive vehicle cover", "DEMO-MOT-10002", cover_amount_cents=24_000_000,
           premium_cents=105_000, premium_frequency="monthly", renewal_date=today + timedelta(days=260))
    policy("c10-home", CLIENT_10, "Santam", "personal_other", "Homeowners cover", "DEMO-HOM-10003", cover_amount_cents=180_000_000, premium_cents=80_000, premium_frequency="monthly")
    policy("c10-fun", CLIENT_10, "Liberty", "funeral", "Family funeral plan", "DEMO-FUN-10004", cover_amount_cents=6_000_000, premium_cents=25_000, premium_frequency="monthly")
    policy("c10-dis", CLIENT_10, "Momentum", "disability", "Income protection", "DEMO-DIS-10005", cover_amount_cents=60_000_000, premium_cents=90_000, premium_frequency="monthly")
    policy("c10-ra", CLIENT_10, "Allan Gray", "retirement", "Retirement annuity", "DEMO-RA-10006", current_value_cents=95_000_000, renewal_date=today + timedelta(days=200))
    item(CLIENT_10, "asset", "property", "Townhouse in Bryanston", 1_800_000)
    item(CLIENT_10, "asset", "vehicle", "Vehicle", 240_000)
    goal("c10-emerg", [CLIENT_10], "Emergency fund", "emergency_fund", 120_000, 108_000, today + timedelta(days=165), 200)

    # ---- Priya Naidoo's additional clients (Ayanda Khumalo, above, is hers too)
    client(CLIENT_11, ADVISER_2, _years_ago(today, 41, 15), _years_ago(today, 2, 200), today + timedelta(days=350), today - timedelta(days=60), 3, 900_000)
    policy("c11-life", CLIENT_11, "Sanlam", "life", "Life cover", "DEMO-LIFE-11001", cover_amount_cents=100_000_000, premium_cents=70_000, premium_frequency="monthly")
    policy("c11-motor", CLIENT_11, "Santam", "motor", "Comprehensive vehicle cover", "DEMO-MOT-11002", cover_amount_cents=32_000_000,
           premium_cents=140_000, premium_frequency="monthly", renewal_date=today + timedelta(days=150))
    item(CLIENT_11, "asset", "vehicle", "Vehicle", 320_000)
    item(CLIENT_11, "liability", "vehicle_finance", "Vehicle finance", 240_000)

    client(CLIENT_12, ADVISER_2, _years_ago(today, 51, 30), _years_ago(today, 6), today + timedelta(days=600), today - timedelta(days=470), None, None)
    policy("c12-life", CLIENT_12, "Old Mutual", "life", "Life cover", "DEMO-LIFE-12001", status="lapsed", cover_amount_cents=75_000_000,
           premium_cents=85_000, premium_frequency="monthly")
    policy("c12-fun", CLIENT_12, "Liberty", "funeral", "Family funeral plan", "DEMO-FUN-12002", cover_amount_cents=5_000_000, premium_cents=20_000, premium_frequency="monthly")
    event(CLIENT_12, "job_change", 10, "Moved to a new employer")

    # Records older than the retention period (RETENTION_YEARS, default 5): flagged in the owner's retention review, never deleted.
    old = clock.now() - timedelta(days=365 * 6 + 40)
    execute(conn, "insert into requests (id, client_id, type, status, payload, submitted_at, updated_at, completed_at, handled_by) values (%s,%s,'policy_document','completed',%s,%s,%s,%s,%s)",
            (uid("request-old"), CLIENT_3, Jsonb({"document_kind": "policy_schedule"}), old, old, old, ADVISER))
    execute(conn, "insert into identity_documents (id, client_id, doc_type, filename, content_type, size_bytes, storage_path, status, verification_source, verifier, "
                  "verified_by, verified_at, expiry_date, uploaded_by, uploaded_at) values (%s,%s,'id_document','old-id.png','image/png',%s,%s,'superseded','simulated_verification','demo_simulated',%s,%s,%s,%s,%s)",
            (uid("idoc-old"), CLIENT_3, len(PNG_1X1), f"identity/{CLIENT_3}/{uid('idoc-old')}-old-id.png", ADVISER, old, today - timedelta(days=200), CLIENT_3, old))

    _seed_compliance(conn, settings, storage, today)


def _seed_compliance(conn: psycopg.Connection, settings: Settings, storage: Storage, today: date) -> None:
    """Identity documents, consents and advice records: a realistic mix, with real gaps for the owner to find."""
    adviser_of = {c: ADVISER for c in (CLIENT_1, CLIENT_2, CLIENT_3, CLIENT_5, CLIENT_6, CLIENT_7, CLIENT_8, CLIENT_9, CLIENT_10)}
    adviser_of.update({c: ADVISER_2 for c in (CLIENT_4, CLIENT_11, CLIENT_12)})
    # (client, doc_type, status, expiry in days from today, verified this many days ago)
    docs = [
        (CLIENT_1, "id_document", "verified", 2900, 200), (CLIENT_1, "drivers_licence", "verified", 40, 200),
        (CLIENT_2, "id_document", "verified", 2000, 300), (CLIENT_2, "drivers_licence", "verified", 400, 300),
        (CLIENT_3, "id_document", "verified", 1500, 400), (CLIENT_3, "drivers_licence", "verified", -10, 400),
        (CLIENT_5, "id_document", "verified", 20, 500),                   # expires in 20 days: a reminder and a compliance flag
        (CLIENT_6, "id_document", "verified", 3000, 120), (CLIENT_7, "id_document", "verified", 2500, 700),
        (CLIENT_9, "id_document", "verified", 1800, 300), (CLIENT_9, "drivers_licence", "verified", 25, 300),
        (CLIENT_10, "id_document", "verified", 3100, 900),
        (CLIENT_11, "id_document", "pending", None, None),                # uploaded, not yet verified
        (CLIENT_12, "id_document", "verified", -30, 800),                 # expired a month ago
    ]
    for cid, dtype, status, expiry_in, verified_ago in docs:
        did = uid(f"idoc-{cid}-{dtype}")
        path = f"identity/{cid}/{did}-{dtype}.png"
        storage.put(settings.attachments_bucket, path, PNG_1X1, "image/png")
        verified = status == "verified"
        execute(conn, "insert into identity_documents (id, client_id, doc_type, filename, content_type, size_bytes, storage_path, status, verification_source, "
                      "verifier, verified_by, verified_at, expiry_date, uploaded_by, uploaded_at) values (%s,%s,%s,%s,'image/png',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (did, cid, dtype, f"{dtype}.png", len(PNG_1X1), path, status, "simulated_verification" if verified else "uploaded",
                 "demo_simulated" if verified else None, adviser_of[cid] if verified else None,
                 clock.now() - timedelta(days=verified_ago) if verified else None,
                 today + timedelta(days=expiry_in) if expiry_in is not None else None, cid, clock.now() - timedelta(days=(verified_ago or 3) + 1)))
    # (client, purpose, status, days ago, method)
    consents = [(c, "data_processing", "granted", 300, "in_person") for c in (CLIENT_1, CLIENT_2, CLIENT_3, CLIENT_5, CLIENT_6, CLIENT_7, CLIENT_9, CLIENT_10, CLIENT_11)]
    consents += [(CLIENT_12, "data_processing", "granted", 500, "in_person"), (CLIENT_12, "data_processing", "withdrawn", 10, "written"),
                 (CLIENT_1, "marketing", "granted", 250, "in_app"), (CLIENT_9, "marketing", "granted", 200, "in_app"),
                 (CLIENT_9, "marketing", "withdrawn", 20, "in_app"), (CLIENT_5, "insurer_sharing", "granted", 300, "in_person")]
    for cid, purpose, status, ago, method in consents:
        execute(conn, "insert into consents (client_id, purpose, status, notice_version, method, recorded_by, recorded_at) values (%s,%s,%s,'v1-demo',%s,%s,%s)",
                (cid, purpose, status, method, adviser_of[cid] if method != "in_app" else None, clock.now() - timedelta(days=ago)))
    # (client, type, days ago, acknowledged, goals, products, recommendation)
    advice = [
        (CLIENT_1, "advice", 28, True, ["Protect the family", "Retire at 60"], [("Life cover top-up", "life")], "Increase life cover once the income review is done."),
        (CLIENT_3, "advice", 400, True, ["Funeral cover for the family"], [("Family funeral plan", "funeral")], "Keep the funeral plan and review in a year."),
        (CLIENT_5, "review", 100, True, ["Protect the bond", "Children's education"], [("Homeowners cover", "personal_other")], "Add homeowners cover and raise life cover."),
        (CLIENT_6, "advice", 12, False, ["Prepare for the baby"], [("Life cover", "life")], "Review cover after the birth."),
        (CLIENT_7, "review", 120, True, ["Retire at 60"], [("Retirement annuity", "retirement")], "Increase the retirement contribution."),
        (CLIENT_9, "consultation", 100, True, ["Keep the car insured"], [("Comprehensive vehicle cover", "motor")], "Reinstate the motor policy."),
        (CLIENT_10, "review", 60, True, ["Emergency fund", "Retirement"], [("Retirement annuity", "retirement")], "No changes; on track."),
        (CLIENT_11, "advice", 20, True, ["Cover for three dependants"], [("Life cover", "life"), ("Funeral plan", "funeral")], "Add funeral cover; raise life cover."),
    ]
    for cid, kind, ago, ack, goals_, prods, rec in advice:
        when = clock.now() - timedelta(days=ago)
        summary_text = f"{kind.capitalize()} meeting. Discussed: {'; '.join(goals_)}. Recommendation: {rec}"
        execute(conn, "insert into advice_records (client_id, adviser_id, interaction_type, needs_goals, products_considered, recommendation, ai_draft, draft_source, "
                      "final_summary, edited_from_draft, client_acknowledged, acknowledged_at, acknowledgement_method, approved_by, approved_at, created_at) "
                      "values (%s,%s,%s,%s,%s,%s,%s,'template',%s,false,%s,%s,%s,%s,%s,%s)",
                (cid, adviser_of[cid], kind, Jsonb(goals_), Jsonb([{"product": p, "category": c} for p, c in prods]), rec, summary_text, summary_text, ack,
                 when if ack else None, "in_meeting" if ack else None, adviser_of[cid], when, when))


_ACTIONS = {"created": "claim.created", "submitted": "claim.submitted", "status_changed": "claim.status_changed",
            "insurer_details_updated": "claim.insurer_details_updated", "note": "claim.note_added", "repair_update": "claim.repair_update_posted",
            "hire_car_updated": "claim.hire_car_updated", "repair_date_chosen": "claim.repair_date_chosen", "attachment_added": "document.uploaded",
            "review_submitted": "claim.reviewed"}


def seed_history(conn: psycopg.Connection) -> None:
    """Write the audit trail the seeded records would have produced, with their real timestamps, so the trail, the owner's
    productivity figures and the compliance packs are populated from the first minute. Chronological, so ids follow time."""
    from app.services import audit

    roles = {r["id"]: r["role"] for r in conn.execute("select id, role from profiles").fetchall()}
    P = lambda uid_: Principal(id=uid_, role=roles[uid_], full_name="", email="") if uid_ else None
    events = []
    for e in conn.execute("select e.*, c.client_id, c.reference from claim_events e join claims c on c.id = e.claim_id").fetchall():
        events.append((e["created_at"], e["actor_id"], _ACTIONS[e["type"]], "claim", e["claim_id"], e["client_id"], f"{e['title']} (claim {e['reference'] or 'draft'})",
                       {"from": e["from_status"], "to": e["to_status"]} if e["to_status"] else {}))
    for r in conn.execute("select * from requests").fetchall():
        events.append((r["submitted_at"], r["client_id"], "request.created", "request", r["id"], r["client_id"], "Submitted a request", {"type": r["type"]}))
        if r["handled_by"]:
            events.append((r["completed_at"] or r["updated_at"], r["handled_by"], "request.updated", "request", r["id"], r["client_id"], f"Set a request to {r['status']}", {"to": r["status"]}))
    for a in conn.execute("select * from advice_records").fetchall():
        events.append((a["created_at"], a["adviser_id"], "advice.recorded", "advice_record", a["id"], a["client_id"], f"Recorded {a['interaction_type']} advice", {"acknowledged": a["client_acknowledged"]}))
    for c in conn.execute("select * from consents").fetchall():
        events.append((c["recorded_at"], c["recorded_by"], "consent.changed", "consent", c["id"], c["client_id"], f"Consent for {c['purpose']} {c['status']}", {"purpose": c["purpose"], "status": c["status"]}))
    for d in conn.execute("select * from identity_documents").fetchall():
        events.append((d["uploaded_at"], d["uploaded_by"], "identity.uploaded", "identity_document", d["id"], d["client_id"], f"Uploaded an {d['doc_type']}", {"doc_type": d["doc_type"]}))
        if d["verified_at"]:
            events.append((d["verified_at"], d["verified_by"], "identity.verified", "identity_document", d["id"], d["client_id"], f"Verified an {d['doc_type']} (demo verification)", {"doc_type": d["doc_type"], "verifier": d["verifier"]}))
    for g in conn.execute("select g.id, g.title, g.created_at, g.created_by, gp.client_id from goals g join goal_participants gp on gp.goal_id = g.id").fetchall():
        events.append((g["created_at"], g["created_by"], "goal.created", "goal", g["id"], g["client_id"], f"Created the goal '{g['title']}'", {}))
    for l in conn.execute("select * from life_events").fetchall():
        events.append((l["created_at"], l["recorded_by"], "life_event.recorded", "life_event", l["id"], l["client_id"], "Recorded a life event", {"kind": l["kind"]}))
    for at, actor, action, etype, eid, cid, summary_text, details in sorted(events, key=lambda x: x[0]):
        audit.record(conn, P(actor), action, etype, eid, client_id=cid, summary=summary_text, details=details, at=at)


def seed_all(conn: psycopg.Connection, settings: Settings, storage: Storage) -> Dict[str, Any]:
    """The whole demo: the base dataset plus the extended one, plus the audit history those records would have produced.
    What `scripts/seed.py` and the demo reset load."""
    refs = seed_demo(conn, settings, storage)
    seed_extended(conn, settings, storage)
    seed_history(conn)
    return refs
