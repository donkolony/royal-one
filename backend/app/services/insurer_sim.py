"""A SIMULATED insurer (docs/AUDIT.md build step 4). DEMO ONLY: it exists so the claim demo can show the client and the adviser
watching the same status change without a real insurer integration, and it says "simulated" everywhere it speaks.

It sits behind an interface (`InsurerAdapter`): a real integration would implement `next_step` from the insurer's API. Nothing here
contacts any external system, and the routes that reach it are refused unless DEMO_MODE is on.

A step goes through the SAME code path as an adviser's status change (`claims.move`), so the timeline event, the audit entry and the
notifications are produced by the engine, not faked by the simulator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, Optional, Protocol
from uuid import UUID

import psycopg

from app.core import clock
from app.core.auth import Principal
from app.core.config import Settings
from app.core.db import Row
from app.core.errors import bad_state
from app.domain import constants as C
from app.services import claims
from app.services.common import update_row
from app.storage.base import Storage


@dataclass
class Step:
    to_status: str
    message: str
    fields: Dict[str, Any] = field(default_factory=dict)


class InsurerAdapter(Protocol):
    name: str

    def next_step(self, claim: Row, today: date) -> Optional[Step]:
        """What the insurer would do next for this claim, or None when it is waiting for someone else."""


def _slug(name: Optional[str]) -> str:
    return "".join(ch for ch in (name or "insurer").lower() if ch.isalnum()) or "insurer"


class DemoInsurerSimulator:
    name = "demo_simulated"

    def next_step(self, claim: Row, today: date) -> Optional[Step]:
        st = claim["status"]
        if st == "submitted":
            number = f"SIM-{100000 + claim['id'].int % 900000}"
            return Step("registered", f"Claim number {number} issued by the simulated insurer.", {
                "insurer_claim_number": number, "insurer_handler_name": "Claims handler (simulated)",
                "insurer_handler_email": f"claims@{_slug(claim.get('insurer_name'))}.demo.example"})
        if st == "registered":
            return Step("assessment", "Assessment booked with the insurer's assessor.")
        if st == "assessment":
            return Step("quotes", "Repair quote received: R18 500.", {"repair_repairer_name": "Demo Panelbeaters (simulated)", "repair_quote_amount_cents": 1_850_000})
        if st == "quotes":
            return Step("authorised", "Repairs authorised for the quoted amount.", {"repair_authorised_amount_cents": claim["repair_quote_amount_cents"] or 1_850_000})
        if st == "authorised":
            return Step("in_repair", "The vehicle is with the repairer.", {
                "repair_drop_off_date": claim["repair_drop_off_date"] or today, "repair_estimated_completion_date": today + timedelta(days=7)})
        if st == "in_repair":
            return Step("completed", "Repairs are finished. Waiting for the client's sign-off.", {"repair_completed_at": clock.now()})
        return None


def step_claim(conn: psycopg.Connection, settings: Settings, storage: Storage, p: Principal, claim_id: UUID,
               adapter: InsurerAdapter = DemoInsurerSimulator()) -> Dict[str, Any]:
    row = claims.load_claim(conn, p, claim_id, lock=True)      # scope: an adviser's own claims, the owner's every claim
    step = adapter.next_step(row, clock.today())
    if step is None:
        raise bad_state(f"The simulated insurer has nothing to do for a claim that is '{row['status']}'.")
    if step.fields:
        update_row(conn, "claims", claim_id, step.fields)
    claims.move(conn, row, step.to_status, title=C.STATUS_BY_VALUE[step.to_status]["client_label"], message=f"Demo insurer (simulated): {step.message}",
                visible=True, actor=None, simulated=True)
    return claims.get_claim(conn, settings, storage, p, claim_id)
