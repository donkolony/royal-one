"""Every number the Opportunity Radar and the owner's views use to turn a fact into rand, in ONE place.

THESE ARE DEMO ESTIMATES. They are placeholder assumptions chosen to make the arithmetic visible; they are not real
commission rates, premiums, fee schedules or market data, and nothing here is financial advice. A licensed adviser must do a
proper needs analysis. The UI shows this dictionary next to every figure ("How is this calculated?").

Change a value here and every estimate, tooltip and test expectation that reads it moves with it.
"""
from __future__ import annotations

from typing import Any, Dict

DEMO_LABEL = "Demo estimate. Assumptions are placeholders, not real commission rates or premiums."

ASSUMPTIONS: Dict[str, Any] = {
    # ---- life cover: need = liabilities + income multiple x annual income (a simple, visible rule, not a needs analysis)
    "life_income_multiple": 5,
    "life_min_gap_cents": 50_000_000,              # ignore gaps smaller than R500 000
    "life_min_gap_ratio": 0.25,                    # ... or smaller than 25% of the estimated need
    "life_premium_per_r1m_annual_cents": 240_000,  # R2 400 a year per R1 million of cover
    # ---- what Royal Square earns on a premium or contribution (fraction of the annual amount)
    "commission_rate": {
        "life": 0.15, "disability": 0.15, "funeral": 0.15, "personal_other": 0.12, "motor": 0.10, "health": 0.05,
        "commercial": 0.10, "investment": 0.01, "retirement": 0.01,
    },
    # ---- annual premium (or contribution) assumed for a product the client does not have yet
    "avg_annual_premium_cents": {
        "motor": 1_800_000, "personal_other": 900_000, "funeral": 480_000, "disability": 1_500_000, "life": 2_400_000,
        "health": 3_600_000, "commercial": 2_400_000, "investment": 3_000_000, "retirement": 6_000_000,
    },
    # ---- detection thresholds
    "goal_behind_tolerance_pct": 10,               # behind schedule when actual progress trails the straight line by > 10 points
    "goal_min_days": 30,
    "retirement_age": 60,
    "retirement_window_years": 5,
    "life_event_window_days": 180,
    "renewal_window_days": 45,
    "document_expiry_window_days": 60,
    "single_product_min_tenure_days": 365,
    "task_due_days": 2,
    # ---- owner views (docs: every derived metric states how it is calculated)
    "proof_of_address_max_age_days": 90,           # a proof of address older than this is stale (an assumption, not a rule)
    "review_interval_days": 365,                   # a review is overdue 12 months after the last one
    "not_contacted_days": 90,
    "at_risk_health_below": 60,
    "stale_claim_days": 7,
    "minutes_per_admin_task": {                    # ILLUSTRATIVE minutes an adviser would otherwise spend by hand
        "identity_reused": 15, "request_via_form": 10, "status_update_propagated": 5, "reminder_auto_created": 3,
    },
    "minutes_per_client_facing_activity": {        # ILLUSTRATIVE minutes per logged client-facing activity
        "advice_record": 45, "outreach_logged": 10, "opportunity_won": 30,
    },
    "minutes_per_manual_admin_activity": {         # ILLUSTRATIVE minutes per manual admin action logged by an adviser
        "claim_update": 8, "request_handled": 8, "goal_or_reminder_edit": 4,
    },
}

SIGNALS: Dict[str, Dict[str, str]] = {
    "under_insured_life": {"label": "Under-insured", "how": "Estimated need (liabilities + income multiple x income) minus existing life cover."},
    "goal_behind": {"label": "Goal behind schedule", "how": "Goal progress trails the straight line from its start to its target date by more than the tolerance."},
    "life_event": {"label": "Life event", "how": "A recorded life event, retirement approaching, or a policy renewal."},
    "missing_cover": {"label": "Missing cover", "how": "Assets or dependants on file with no active policy in the matching category."},
    "single_product": {"label": "Single product", "how": "One active policy after a year or more as a client, with nothing else surfaced."},
    "lapsed_cover": {"label": "Lapsed cover", "how": "A policy with status 'lapsed'."},
    "expiring_document": {"label": "Expiring document", "how": "An identity document or licence that expires soon or has just expired."},
}

# Category shown to a client, and the first thing worth quoting for it.
CATEGORY_LABELS = {
    "life": "life cover", "disability": "disability / income protection", "funeral": "funeral cover",
    "personal_other": "home and household cover", "motor": "motor cover", "health": "medical cover",
    "commercial": "business cover", "investment": "an investment", "retirement": "a retirement annuity",
}


def public_assumptions() -> Dict[str, Any]:
    return {"label": DEMO_LABEL, "values": ASSUMPTIONS, "signals": SIGNALS}
