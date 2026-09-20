"""Request bodies (docs/api.md section 5). Unknown fields are rejected (`extra_forbidden`).

Response bodies are plain dicts built by the services; their shapes are documented in api.md section 4 and
asserted by the test suite.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator

from app.core import clock
from app.domain import constants as C


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _email_or_none(v: Optional[str]) -> Optional[str]:
    if v is not None and not _EMAIL.match(v):
        raise ValueError("Enter a valid email address.")
    return v


# ------------------------------------------------------------------------------------- identity
class ProfilePatch(Body):
    phone: Optional[str] = Field(default=None, max_length=30)
    drivers_licence_expiry: Optional[date] = None


class ClientPatch(Body):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=30)
    date_of_birth: Optional[date] = None
    drivers_licence_expiry: Optional[date] = None
    client_since: Optional[date] = None
    last_annual_review_date: Optional[date] = None
    # Optional, adviser-entered. The under-insurance rule needs them; without them it does not run (docs/AUDIT.md assumptions).
    dependants: Optional[StrictInt] = Field(default=None, ge=0, le=20)
    annual_income_cents: Optional[StrictInt] = Field(default=None, ge=0)


# ------------------------------------------------------------------------------------- policies
class PolicyCreate(Body):
    client_id: UUID
    insurer_id: UUID
    category: Literal[tuple(C.POLICY_CATEGORIES)]  # type: ignore[valid-type]
    product_name: str = Field(min_length=1, max_length=120)
    policy_number: str = Field(min_length=1, max_length=60)
    status: Literal[tuple(C.POLICY_STATUSES)] = "active"  # type: ignore[valid-type]
    asset_description: Optional[str] = Field(default=None, max_length=200)
    cover_amount_cents: Optional[StrictInt] = Field(default=None, ge=0)
    current_value_cents: Optional[StrictInt] = Field(default=None, ge=0)
    premium_cents: Optional[StrictInt] = Field(default=None, ge=0)
    premium_frequency: Optional[Literal["monthly", "annual"]] = None
    start_date: Optional[date] = None
    renewal_date: Optional[date] = None
    valuation_certificate_date: Optional[date] = None


class PolicyPatch(Body):
    insurer_id: Optional[UUID] = None
    category: Optional[Literal[tuple(C.POLICY_CATEGORIES)]] = None  # type: ignore[valid-type]
    product_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    policy_number: Optional[str] = Field(default=None, min_length=1, max_length=60)
    status: Optional[Literal[tuple(C.POLICY_STATUSES)]] = None  # type: ignore[valid-type]
    asset_description: Optional[str] = Field(default=None, max_length=200)
    cover_amount_cents: Optional[StrictInt] = Field(default=None, ge=0)
    current_value_cents: Optional[StrictInt] = Field(default=None, ge=0)
    premium_cents: Optional[StrictInt] = Field(default=None, ge=0)
    premium_frequency: Optional[Literal["monthly", "annual"]] = None
    start_date: Optional[date] = None
    renewal_date: Optional[date] = None
    valuation_certificate_date: Optional[date] = None


# ------------------------------------------------------------------------------ financial items
class FinancialItemCreate(Body):
    client_id: UUID
    kind: Literal["asset", "liability"]
    category: Literal[tuple(C.ASSET_CATEGORIES + C.LIABILITY_CATEGORIES)]  # type: ignore[valid-type]
    label: str = Field(min_length=1, max_length=120)
    amount_cents: StrictInt = Field(gt=0)
    as_of_date: date


class FinancialItemPatch(Body):
    category: Optional[Literal[tuple(C.ASSET_CATEGORIES + C.LIABILITY_CATEGORIES)]] = None  # type: ignore[valid-type]
    label: Optional[str] = Field(default=None, min_length=1, max_length=120)
    amount_cents: Optional[StrictInt] = Field(default=None, gt=0)
    as_of_date: Optional[date] = None


# ------------------------------------------------------------------------------------- goals
class GoalCreate(Body):
    client_ids: List[UUID] = Field(min_length=1, max_length=5)
    title: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    category: Literal[tuple(C.GOAL_CATEGORIES)]  # type: ignore[valid-type]
    target_amount_cents: StrictInt = Field(gt=0)
    current_amount_cents: StrictInt = Field(default=0, ge=0)
    target_date: Optional[date] = None

    @field_validator("client_ids")
    @classmethod
    def _distinct(cls, v: List[UUID]) -> List[UUID]:
        if len(set(v)) != len(v):
            raise ValueError("client_ids must be distinct.")
        return v

    @field_validator("target_date")
    @classmethod
    def _not_past(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v < clock.today():
            raise ValueError("target_date must be today or later.")
        return v


class GoalPatch(Body):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    category: Optional[Literal[tuple(C.GOAL_CATEGORIES)]] = None  # type: ignore[valid-type]
    target_amount_cents: Optional[StrictInt] = Field(default=None, gt=0)
    current_amount_cents: Optional[StrictInt] = Field(default=None, ge=0)
    target_date: Optional[date] = None
    status: Optional[Literal["active", "archived"]] = None
    client_ids: Optional[List[UUID]] = Field(default=None, min_length=1, max_length=5)


# --------------------------------------------------------------------------------- reminders
class ReminderCreate(Body):
    client_id: UUID
    type: str = Field(default="custom", min_length=1, max_length=60)
    title: str = Field(min_length=1, max_length=160)
    description: Optional[str] = Field(default=None, max_length=1000)
    due_date: date
    audience: Literal["client", "advisor", "both"]

    @field_validator("type")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in C.REMINDER_TYPE_BY_NAME:
            raise ValueError("Unknown reminder type.")
        return v


class ReminderPatch(Body):
    title: Optional[str] = Field(default=None, min_length=1, max_length=160)
    description: Optional[str] = Field(default=None, max_length=1000)
    due_date: Optional[date] = None
    audience: Optional[Literal["client", "advisor", "both"]] = None
    status: Optional[Literal["pending", "dismissed"]] = None


# ----------------------------------------------------------------------------------- claims
class ClaimCreate(Body):
    policy_id: Optional[UUID] = None
    insurer_id: Optional[UUID] = None


class IncidentPatch(Body):
    occurred_at: Optional[AwareDatetime] = None
    location_text: Optional[str] = Field(default=None, min_length=3, max_length=300)
    location_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    location_lng: Optional[float] = Field(default=None, ge=-180, le=180)
    description: Optional[str] = Field(default=None, min_length=10, max_length=4000)

    @field_validator("occurred_at")
    @classmethod
    def _not_future(cls, v: Optional[AwareDatetime]) -> Optional[AwareDatetime]:
        if v is not None and v > clock.now():
            raise ValueError("The incident cannot be in the future.")
        return v


class PolicePatch(Body):
    reported: Optional[StrictBool] = None
    case_number: Optional[str] = Field(default=None, max_length=60)
    station: Optional[str] = Field(default=None, max_length=120)
    reported_at: Optional[AwareDatetime] = None


class DriverPatch(Body):
    is_policyholder: Optional[StrictBool] = None
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    relationship_to_policyholder: Optional[str] = Field(default=None, max_length=80)


class Witness(Body):
    name: str = Field(min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=160)
    statement: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: Optional[str]) -> Optional[str]:
        return _email_or_none(v)


class ThirdParty(Body):
    name: str = Field(min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=30)
    drivers_licence_number: Optional[str] = Field(default=None, max_length=40)
    vehicle_registration: Optional[str] = Field(default=None, max_length=20)
    vehicle_make_model: Optional[str] = Field(default=None, max_length=80)
    insurer_name: Optional[str] = Field(default=None, max_length=80)
    policy_number: Optional[str] = Field(default=None, max_length=60)


class ClaimPatch(Body):
    insurer_id: Optional[UUID] = None
    incident: Optional[IncidentPatch] = None
    police: Optional[PolicePatch] = None
    driver: Optional[DriverPatch] = None
    vehicle_use: Optional[Literal["personal", "business"]] = None
    witnesses: Optional[List[Witness]] = Field(default=None, max_length=10)
    third_parties: Optional[List[ThirdParty]] = Field(default=None, max_length=10)


class InsurerDetailsPatch(Body):
    claim_number: Optional[str] = Field(default=None, max_length=60)
    handler_name: Optional[str] = Field(default=None, max_length=120)
    handler_email: Optional[str] = Field(default=None, max_length=160)
    handler_phone: Optional[str] = Field(default=None, max_length=30)

    @field_validator("handler_email")
    @classmethod
    def _check_email(cls, v: Optional[str]) -> Optional[str]:
        return _email_or_none(v)


class TransitionBody(Body):
    to_status: Literal[tuple(C.STATUS_ORDER)]  # type: ignore[valid-type]
    note: Optional[str] = Field(default=None, max_length=1000)
    visible_to_client: StrictBool = True


class RepairDetailsPatch(Body):
    repairer_name: Optional[str] = Field(default=None, max_length=120)
    repairer_phone: Optional[str] = Field(default=None, max_length=30)
    quote_amount_cents: Optional[StrictInt] = Field(default=None, ge=0)
    authorised_amount_cents: Optional[StrictInt] = Field(default=None, ge=0)
    estimated_completion_date: Optional[date] = None
    completed_at: Optional[AwareDatetime] = None


class RepairDateBody(Body):
    drop_off_date: date

    @field_validator("drop_off_date")
    @classmethod
    def _not_past(cls, v: date) -> date:
        if v < clock.today():
            raise ValueError("The drop-off date must be today or later.")
        return v


class HireCarPatch(Body):
    status: Optional[Literal[tuple(C.HIRE_CAR_STATUSES)]] = None  # type: ignore[valid-type]
    provider: Optional[str] = Field(default=None, max_length=120)
    delivery_date: Optional[date] = None
    return_date: Optional[date] = None


class UpdateBody(Body):
    type: Literal["note", "repair_update"] = "note"
    message: str = Field(min_length=1, max_length=2000)
    visible_to_client: Optional[StrictBool] = None


class ReviewBody(Body):
    rating: StrictInt = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=1000)


# --------------------------------------------------------------------------------- requests
class RequestCreate(Body):
    type: str = Field(min_length=1, max_length=60)      # validated against the workflow config, so a new type needs no code change
    payload: Dict[str, Any]

    @field_validator("type")
    @classmethod
    def _known_type(cls, v: str) -> str:
        if v not in C.REQUEST_TYPE_BY_NAME:
            raise ValueError("Unknown request type.")
        return v

    client_note: Optional[str] = Field(default=None, max_length=1000)


class RequestPatch(Body):
    status: Optional[Literal["in_progress", "completed", "declined"]] = None
    adviser_response: Optional[str] = Field(default=None, max_length=2000)


# ---------------------------------------------------------------------------------------- identity vault
class IdentityVerifyBody(Body):
    expiry_date: Optional[date] = None
    issued_date: Optional[date] = None


class IdentityRejectBody(Body):
    reason: str = Field(min_length=3, max_length=300)


# ---------------------------------------------------------------------------------- opportunities
class SnoozeBody(Body):
    days: StrictInt = Field(ge=1, le=90)


class OutcomeBody(Body):
    outcome: Literal["won", "lost"]
    reason: str = Field(min_length=3, max_length=300)
    actual_annual_value_cents: Optional[StrictInt] = Field(default=None, ge=0)


class OutreachBody(Body):
    channel: Literal["email", "whatsapp", "call", "meeting"]
    note: Optional[str] = Field(default=None, max_length=300)


class OutreachDraftBody(Body):
    channel: Literal["email", "whatsapp"]


class LifeEventBody(Body):
    kind: Literal["new_baby", "marriage", "new_vehicle", "property_purchase", "divorce", "job_change"]
    occurred_on: date
    note: Optional[str] = Field(default=None, max_length=300)


# ------------------------------------------------------------------------------ assistant/email
class AssistantFilters(Body):
    category: List[Literal[tuple(C.DOCUMENT_CATEGORIES)]] = Field(default_factory=list)  # type: ignore[valid-type]
    insurer_id: Optional[UUID] = None
    document_ids: List[UUID] = Field(default_factory=list, max_length=50)


class AssistantQuery(Body):
    question: str = Field(min_length=3, max_length=1000)
    conversation_id: Optional[UUID] = None
    filters: Optional[AssistantFilters] = None


class EmailLinkBody(Body):
    claim_id: Optional[UUID] = None
    client_id: Optional[UUID] = None


class DraftRequest(Body):
    claim_id: UUID
    thread_id: Optional[UUID] = None
    purpose: Literal["initial_notification", "follow_up", "reply", "status_query"]
    instructions: Optional[str] = Field(default=None, max_length=500)
