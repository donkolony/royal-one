"""Reference data that is code, not database rows. Mirrors docs/api.md section 3."""
from __future__ import annotations

from typing import Any, Dict, List

# ------------------------------------------------------------------------------------------- claims
CLAIM_STATUSES: List[Dict[str, Any]] = [
    {"value": "draft", "order": 0, "client_label": "Not sent yet", "advisor_label": "Draft (not visible)"},
    {"value": "submitted", "order": 1, "client_label": "Sent to Royal Square", "advisor_label": "Submitted"},
    {"value": "registered", "order": 2, "client_label": "Registered with your insurer", "advisor_label": "Registered (claim no. issued)"},
    {"value": "assessment", "order": 3, "client_label": "Vehicle assessment", "advisor_label": "Assessment"},
    {"value": "quotes", "order": 4, "client_label": "Repair quotes", "advisor_label": "Quotes with insurer"},
    {"value": "authorised", "order": 5, "client_label": "Repairs approved", "advisor_label": "Authorised"},
    {"value": "in_repair", "order": 6, "client_label": "Being repaired", "advisor_label": "In repair"},
    {"value": "completed", "order": 7, "client_label": "Repairs finished", "advisor_label": "Completed, awaiting client sign-off"},
    {"value": "closed", "order": 8, "client_label": "Closed", "advisor_label": "Closed"},
]
STATUS_ORDER: List[str] = [s["value"] for s in CLAIM_STATUSES]
STATUS_BY_VALUE: Dict[str, Dict[str, Any]] = {s["value"]: s for s in CLAIM_STATUSES}
PIPELINE_STATUSES = ["submitted", "registered", "assessment", "quotes", "authorised", "in_repair", "completed"]

FORWARD_LABELS = {
    "registered": "Mark as registered",
    "assessment": "Move to assessment",
    "quotes": "Move to quotes",
    "authorised": "Mark as authorised",
    "in_repair": "Start repair",
    "completed": "Mark repairs completed",
    "closed": "Close claim",
}

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
REQUEST_TYPES: List[Dict[str, Any]] = [
    {
        "type": "address_change", "label": "Change of address", "requires_verification": False, "max_attachments": 3,
        "fields": [
            {"name": "address_line_1", "label": "Street address", "type": "string", "required": True, "max_length": 120},
            {"name": "address_line_2", "label": "Complex / building", "type": "string", "required": False, "max_length": 120},
            {"name": "suburb", "label": "Suburb", "type": "string", "required": True, "max_length": 80},
            {"name": "city", "label": "City", "type": "string", "required": True, "max_length": 80},
            {"name": "postal_code", "label": "Postal code", "type": "string", "required": True, "pattern": r"^[0-9]{4}$"},
            {"name": "effective_date", "label": "Effective from", "type": "date", "required": False},
        ],
    },
    {
        "type": "bank_details_change", "label": "Change of bank details", "requires_verification": True, "max_attachments": 3,
        "fields": [
            {"name": "account_holder", "label": "Account holder", "type": "string", "required": True, "max_length": 120},
            {"name": "bank_name", "label": "Bank", "type": "string", "required": True, "max_length": 80},
            {"name": "account_type", "label": "Account type", "type": "enum", "required": True, "options": ["cheque", "savings", "transmission", "other"]},
            {"name": "account_number", "label": "Account number", "type": "string", "required": True, "pattern": r"^[0-9]{6,16}$"},
            {"name": "branch_code", "label": "Branch code", "type": "string", "required": True, "pattern": r"^[0-9]{6}$"},
            {"name": "effective_date", "label": "Effective from", "type": "date", "required": False},
        ],
    },
    {
        "type": "policy_document", "label": "Request a policy document", "requires_verification": False, "max_attachments": 0,
        "fields": [
            {"name": "policy_id", "label": "Policy", "type": "uuid", "required": True, "ref": "policy"},
            {"name": "document_kind", "label": "Document", "type": "enum", "required": True, "options": ["policy_schedule", "policy_wording", "certificate", "other"]},
        ],
    },
    {
        "type": "border_letter", "label": "Request a border letter", "requires_verification": False, "max_attachments": 0,
        "fields": [
            {"name": "policy_id", "label": "Vehicle policy", "type": "uuid", "required": True, "ref": "motor_policy"},
            {"name": "destination_countries", "label": "Countries you will travel to", "type": "string_list", "required": True, "min_items": 1, "max_items": 10, "max_length": 80},
            {"name": "travel_from", "label": "Travel from", "type": "date", "required": True},
            {"name": "travel_to", "label": "Travel to", "type": "date", "required": True, "not_before": "travel_from"},
        ],
    },
    {
        "type": "irp5", "label": "Request an IRP5", "requires_verification": False, "max_attachments": 0,
        "fields": [
            {"name": "provider_name", "label": "Investment company", "type": "string", "required": True, "max_length": 120},
            {"name": "tax_year", "label": "Tax year", "type": "integer", "required": True, "min": 1990, "max": 2100},
            {"name": "policy_id", "label": "Policy", "type": "uuid", "required": False, "ref": "policy"},
        ],
    },
    {
        "type": "consultation", "label": "Request a consultation", "requires_verification": False, "max_attachments": 0,
        "fields": [
            {"name": "preferred_dates", "label": "Preferred dates", "type": "date_list", "required": True, "min_items": 1, "max_items": 3, "not_in_past": True},
            {"name": "mode", "label": "How would you like to meet?", "type": "enum", "required": True, "options": ["in_person", "phone", "video"]},
            {"name": "topic", "label": "What would you like to discuss?", "type": "string", "required": True, "max_length": 200},
        ],
    },
    {
        "type": "client_information", "label": "Send financial information", "requires_verification": False, "max_attachments": 5,
        "fields": [
            {"name": "statement_type", "label": "Statement", "type": "enum", "required": True, "options": ["balance_sheet", "income_statement"]},
            {
                "name": "items", "label": "Items", "type": "object_list", "required": True, "min_items": 1, "max_items": 50,
                "item_fields": [
                    {"name": "label", "label": "Description", "type": "string", "required": True, "max_length": 120},
                    {"name": "type", "label": "Type", "type": "enum", "required": True, "options": ["asset", "liability", "income", "expense"]},
                    {"name": "amount_cents", "label": "Amount (cents)", "type": "integer", "required": True, "min": 1},
                    {"name": "frequency", "label": "Frequency", "type": "enum", "required": False, "options": ["monthly", "annual", "one_off"]},
                ],
            },
        ],
    },
]
REQUEST_TYPE_BY_NAME = {t["type"]: t for t in REQUEST_TYPES}

# ------------------------------------------------------------------------------------------- email
EMAIL_FLAG_LABELS = {
    "insurer_sender": "From an insurer",
    "client_sender": "From a client",
    "claim_reference_match": "Mentions a claim",
    "deadline_keyword": "Mentions a deadline",
}
