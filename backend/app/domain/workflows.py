"""Workflow definitions: ONE config that the engine (app/services/workflow.py) and the API read.

A workflow is: steps, the documents it needs, validation rules (the field definitions), status transitions with who may make
them, and who is notified. The motor claim and the client requests are defined here, in the same vocabulary.

Adding a simple request type is ONE entry in `_REQUEST_META` plus its fields in `_REQUEST_FIELDS`. It needs no new page (the
client form is rendered from `fields`), no new endpoint and no migration (the type is validated here, not by a database CHECK).

This module imports nothing from the app, so `domain/constants.py` can derive the older names from it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class Notice:
    """Someone to tell when a transition happens. Placeholders: {reference} {client} {status_label}."""
    to: str          # "client" | "advisor"
    title: str
    body: str = ""


@dataclass(frozen=True)
class Transition:
    from_status: str
    to_status: str
    actor: str       # "client" | "advisor" (the simulated insurer uses the advisor's transitions, as the system)
    label: str
    direction: str = "forward"
    requires: Tuple[str, ...] = ()       # fields that must be filled first ("missing_fields" = the draft's required fields)
    notify: Tuple[Notice, ...] = ()


# ==================================================================================================== motor claim
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
STATUS_BY_VALUE: Dict[str, Dict[str, Any]] = {s["value"]: s for s in CLAIM_STATUSES}

_TELL_CLIENT = lambda to: (Notice("client", "{status_label}", "Claim {reference} moved to: {status_label}."),)  # noqa: E731

MOTOR_CLAIM_TRANSITIONS: Tuple[Transition, ...] = (
    Transition("draft", "submitted", "client", "Send to Royal Square", requires=("missing_fields",),
               notify=(Notice("advisor", "New claim submitted: {reference}", "{client} sent a motor claim."),)),
    Transition("submitted", "registered", "advisor", "Mark as registered", requires=("insurer_details.claim_number",), notify=_TELL_CLIENT("registered")),
    Transition("registered", "assessment", "advisor", "Move to assessment", notify=_TELL_CLIENT("assessment")),
    Transition("assessment", "quotes", "advisor", "Move to quotes", notify=_TELL_CLIENT("quotes")),
    Transition("quotes", "authorised", "advisor", "Mark as authorised", notify=_TELL_CLIENT("authorised")),
    Transition("authorised", "in_repair", "advisor", "Start repair", notify=_TELL_CLIENT("in_repair")),
    Transition("in_repair", "completed", "advisor", "Mark repairs completed", notify=_TELL_CLIENT("completed")),
    Transition("completed", "closed", "advisor", "Close claim", notify=_TELL_CLIENT("closed")),
    Transition("completed", "closed", "client", "Sign off and close"),
    # One step back is allowed for advisers, never into or out of draft and never out of closed (docs/ARCHITECT.md 7.1).
    Transition("registered", "submitted", "advisor", "Move back to {label}", "back"),
    Transition("assessment", "registered", "advisor", "Move back to {label}", "back"),
    Transition("quotes", "assessment", "advisor", "Move back to {label}", "back"),
    Transition("authorised", "quotes", "advisor", "Move back to {label}", "back"),
    Transition("in_repair", "authorised", "advisor", "Move back to {label}", "back"),
    Transition("completed", "in_repair", "advisor", "Move back to {label}", "back"),
)

MOTOR_CLAIM: Dict[str, Any] = {
    "key": "motor_claim", "kind": "claim", "label": "Motor accident claim",
    "description": "From the scene checklist to the closed claim: the client and the adviser see the same live timeline.",
    "steps": [
        {"key": "checklist", "label": "Scene checklist", "description": "What to gather at the scene."},
        {"key": "incident", "label": "What happened", "description": "Date, place and description."},
        {"key": "people", "label": "Police, driver and others", "description": "Police case, driver, witnesses, third parties."},
        {"key": "documents", "label": "Photos and documents", "description": "Photos and the driver's licence (reused from the identity vault when valid)."},
        {"key": "send", "label": "Check and send", "description": "Send to Royal Square."},
    ],
    "documents": [
        {"kind": "photo", "label": "At least one photo", "required": True, "reuse_from_vault": None},
        {"kind": "drivers_licence", "label": "Driver's licence", "required": True, "reuse_from_vault": "drivers_licence"},
    ],
    "requires_identity": True,
    "insurer": "simulated",
}


# ================================================================================================ client requests
REQUEST_STATUSES: List[Dict[str, Any]] = [
    {"value": "submitted", "order": 1, "client_label": "Received", "advisor_label": "New"},
    {"value": "in_progress", "order": 2, "client_label": "In progress", "advisor_label": "In progress"},
    {"value": "completed", "order": 3, "client_label": "Completed", "advisor_label": "Completed"},
    {"value": "declined", "order": 3, "client_label": "Declined", "advisor_label": "Declined"},
]
REQUEST_TRANSITIONS: Tuple[Transition, ...] = (
    Transition("submitted", "in_progress", "advisor", "Start work", notify=(Notice("client", "Your request is being worked on", "{label} is now in progress."),)),
    Transition("submitted", "completed", "advisor", "Mark completed", notify=(Notice("client", "Your request is complete", "{label} is done."),)),
    Transition("submitted", "declined", "advisor", "Decline", notify=(Notice("client", "Your request was declined", "{label} could not be completed."),)),
    Transition("in_progress", "completed", "advisor", "Mark completed", notify=(Notice("client", "Your request is complete", "{label} is done."),)),
    Transition("in_progress", "declined", "advisor", "Decline", notify=(Notice("client", "Your request was declined", "{label} could not be completed."),)),
)
REQUEST_TERMINAL = ("completed", "declined")
REQUEST_NOTIFY_ON_CREATE = (Notice("advisor", "New request: {label}", "{client} submitted a request."),)

_REQUEST_FIELDS: List[Dict[str, Any]] = [
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


# What each request type adds to its fields: a description, its steps, the documents it can reuse from the identity vault, and
# whether it needs a verified identity. `insurer_forward` = the simulated provider handles it (labelled Demo in the UI).
_REQUEST_META: Dict[str, Dict[str, Any]] = {
    "address_change": {
        "description": "Tell us where you live now and we update every policy.", "requires_identity": False, "insurer_forward": True, "sla_days": 2,
        "steps": [("details", "Your new address"), ("documents", "Proof of address"), ("review", "Check and send")],
        "documents": [{"kind": "proof_of_address", "label": "Proof of address", "required": False, "reuse_from_vault": "proof_of_address"}],
    },
    "bank_details_change": {
        "description": "Change the account that premiums are paid from or benefits are paid to.", "requires_identity": True, "insurer_forward": True, "sla_days": 3,
        "steps": [("details", "Bank details"), ("review", "Check and send")],
        "documents": [{"kind": "id_document", "label": "Verified ID", "required": True, "reuse_from_vault": "id_document"}],
    },
    "policy_document": {
        "description": "Get a copy of a policy schedule, wording or certificate.", "requires_identity": False, "insurer_forward": True, "sla_days": 1,
        "steps": [("details", "Which document"), ("review", "Check and send")], "documents": [],
    },
    "border_letter": {
        "description": "A letter for taking your vehicle across a border.", "requires_identity": False, "insurer_forward": True, "sla_days": 2,
        "steps": [("details", "Trip details"), ("review", "Check and send")], "documents": [],
    },
    "irp5": {
        "description": "Ask for your IRP5 tax certificate.", "requires_identity": False, "insurer_forward": True, "sla_days": 3,
        "steps": [("details", "Which certificate"), ("review", "Check and send")], "documents": [],
    },
    "consultation": {
        "description": "Book time with your adviser.", "requires_identity": False, "insurer_forward": False, "sla_days": 2,
        "steps": [("details", "When and why"), ("review", "Check and send")], "documents": [],
    },
    "client_information": {
        "description": "Send your balance sheet or income statement.", "requires_identity": False, "insurer_forward": False, "sla_days": 5,
        "steps": [("details", "Your figures"), ("review", "Check and send")], "documents": [],
    },
}


def request_types() -> List[Dict[str, Any]]:
    """The request workflows in the shape GET /requests/types serves (the older keys are kept, new ones added)."""
    out = []
    for t in _REQUEST_FIELDS:
        m = _REQUEST_META[t["type"]]
        out.append({
            **t, "requires_verification": t["requires_verification"] or m["requires_identity"],
            "description": m["description"], "requires_identity": m["requires_identity"], "insurer_forward": m["insurer_forward"],
            "sla_days": m["sla_days"], "steps": [{"key": k, "label": lab} for k, lab in m["steps"]], "documents": m["documents"],
        })
    return out


def public_definitions() -> List[Dict[str, Any]]:
    """GET /workflows: every workflow, its steps and documents, in one list the UI can render from."""
    claim = {**MOTOR_CLAIM, "statuses": CLAIM_STATUSES,
             "transitions": [{"from": t.from_status, "to": t.to_status, "actor": t.actor, "direction": t.direction, "requires": list(t.requires),
                              "notifies": [n.to for n in t.notify]} for t in MOTOR_CLAIM_TRANSITIONS]}
    reqs = [{"key": t["type"], "kind": "request", "label": t["label"], "description": t["description"], "steps": t["steps"], "documents": t["documents"],
             "requires_identity": t["requires_identity"], "insurer": "simulated" if t["insurer_forward"] else None, "sla_days": t["sla_days"],
             "fields": t["fields"], "statuses": REQUEST_STATUSES} for t in request_types()]
    return [claim] + reqs
