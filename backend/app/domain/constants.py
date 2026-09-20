"""Reference data that is code, not database rows. Mirrors docs/api.md section 3."""
from __future__ import annotations

from typing import Any, Dict, List

from app.domain import workflows as W

# ------------------------------------------------------------------------------------------- claims
# The status list, labels and transitions live in domain/workflows.py (the workflow engine's single config).
CLAIM_STATUSES: List[Dict[str, Any]] = W.CLAIM_STATUSES
STATUS_ORDER: List[str] = [s["value"] for s in CLAIM_STATUSES]
STATUS_BY_VALUE: Dict[str, Dict[str, Any]] = W.STATUS_BY_VALUE
PIPELINE_STATUSES = ["submitted", "registered", "assessment", "quotes", "authorised", "in_repair", "completed"]
FORWARD_LABELS = {t.to_status: t.label for t in W.MOTOR_CLAIM_TRANSITIONS if t.actor == "advisor" and t.direction == "forward"}

HIRE_CAR_STATUSES = ["not_required", "requested", "arranged", "delivered", "return_arranged", "returned"]
HIRE_CAR_LABELS = {
    "not_required": "No hire car needed",
    "requested": "Hire car requested",
    "arranged": "Hire car arranged",
    "delivered": "Hire car delivered to the repairer",
    "return_arranged": "Hire car return arranged",
    "returned": "Hire car returned",
}

POLICE_REPORT_WINDOW_HOURS = 48  # PRD 4.4 A checklist; legal basis not verified.

CHECKLIST: List[Dict[str, Any]] = [
    {"id": "road_surface", "order": 1, "title": "Photograph the road", "description": "Photos of the road surface and the direction each vehicle was travelling.", "upload_kind": "road_photo"},
    {"id": "location", "order": 2, "title": "Note where you are", "description": "The address, or the nearest cross streets.", "upload_kind": None},
    {"id": "vehicles_people", "order": 3, "title": "Photograph everything involved", "description": "All vehicles and all people involved.", "upload_kind": "vehicle_photo"},
    {"id": "plates_discs", "order": 4, "title": "Licence plates and registration discs", "description": "A clear photo of each.", "upload_kind": "plate_or_disc_photo"},
    {"id": "id_documents", "order": 5, "title": "ID documents", "description": "Of everyone involved.", "upload_kind": "id_document"},
    {"id": "witnesses", "order": 6, "title": "Witnesses", "description": "Names and contact details. You can add a voice note if it is easier.", "upload_kind": "witness_voice_note"},
    {"id": "other_insurance", "order": 7, "title": "Other parties' insurance", "description": "Their insurer and policy number.", "upload_kind": None},
    {"id": "police", "order": 8, "title": "Report it to the police", "description": "Do this within 48 hours and keep the case number.", "upload_kind": None},
]

# ------------------------------------------------------------------------------------- attachments
IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
DOCUMENT_TYPES = ["application/pdf"]
AUDIO_TYPES = ["audio/webm", "audio/mp4", "audio/mpeg", "audio/ogg", "audio/wav"]

ATTACHMENT_KINDS: Dict[str, List[str]] = {
    "road_photo": ["image"],
    "vehicle_photo": ["image"],
    "people_photo": ["image"],
    "plate_or_disc_photo": ["image"],
    "id_document": ["image", "document"],
    "witness_voice_note": ["audio"],
    "drivers_licence": ["image", "document"],
    "accident_sketch": ["image"],
    "other": ["image", "document"],
}
_FAMILIES = {"image": IMAGE_TYPES, "document": DOCUMENT_TYPES, "audio": AUDIO_TYPES}
PHOTO_KINDS = {"road_photo", "vehicle_photo", "people_photo", "plate_or_disc_photo"}


def allowed_content_types(kind: str) -> List[str]:
    out: List[str] = []
    for fam in ATTACHMENT_KINDS[kind]:
        out.extend(_FAMILIES[fam])
    return out


# ---------------------------------------------------------------------------------------- reminders
REMINDER_TYPES: List[Dict[str, Any]] = [
    {"type": "valuation_certificate", "label": "Valuation certificate due", "default_audience": "both", "lead_days": 30},
    {"type": "licence_expiry", "label": "Driving licence expiring", "default_audience": "client", "lead_days": 60},
    {"type": "annual_review", "label": "Annual financial review", "default_audience": "advisor", "lead_days": 30},
    {"type": "retirement_fee_renewal", "label": "Retirement fee renewal", "default_audience": "advisor", "lead_days": 30},
    {"type": "birthday", "label": "Client birthday", "default_audience": "advisor", "lead_days": 7},
    {"type": "anniversary", "label": "Client anniversary", "default_audience": "advisor", "lead_days": 7},
    {"type": "claim_police_report", "label": "Report to police within 48 hours", "default_audience": "client", "lead_days": 2},  # due = 48h after the incident, so it must show at once
    {"type": "custom", "label": "Custom reminder", "default_audience": "advisor", "lead_days": None},
]
REMINDER_TYPE_BY_NAME = {t["type"]: t for t in REMINDER_TYPES}
DUE_SOON_DAYS = 7
MAX_OVERDUE_DAYS = 90  # rule-generated reminders older than this are not created (proposal)

# ------------------------------------------------------------------------------------------ policies
POLICY_CATEGORIES = ["motor", "life", "health", "funeral", "personal_other", "commercial", "investment", "retirement", "disability"]
POLICY_STATUSES = ["active", "pending", "lapsed", "cancelled"]

ASSET_CATEGORIES = ["property", "vehicle", "cash", "investments", "retirement", "business", "other_asset"]
LIABILITY_CATEGORIES = ["home_loan", "vehicle_finance", "credit_card", "personal_loan", "other_liability"]
GOAL_CATEGORIES = ["retirement", "education", "property", "emergency_fund", "travel", "debt_repayment", "other"]

DOCUMENT_CATEGORIES = ["policy_wording", "internal_process", "company_policy", "regulation"]

# ---------------------------------------------------------------------------------------- requests
# Field types: string, text, date, integer, boolean, enum, uuid, string_list, date_list, object_list.
# The definitions are in domain/workflows.py; this is the same list, with its extra keys (steps, documents, ...).
REQUEST_TYPES: List[Dict[str, Any]] = W.request_types()
REQUEST_TYPE_BY_NAME = {t["type"]: t for t in REQUEST_TYPES}

# ------------------------------------------------------------------------------------------- email
EMAIL_FLAG_LABELS = {
    "insurer_sender": "From an insurer",
    "client_sender": "From a client",
    "claim_reference_match": "Mentions a claim",
    "deadline_keyword": "Mentions a deadline",
}
