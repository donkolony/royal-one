/**
 * Offline mock backend for UI work (VITE_API_URL empty or "mock").
 *
 * It answers the same paths with the SAME shapes as the real API (docs/api.md): list endpoints return a
 * Page envelope, money is integer cents, timestamps end in Z, errors are the { error: {...} } envelope.
 * State lives in memory, so create/update flows behave until the page is reloaded.
 * There are no tokens here: mock mode never talks to Supabase or the network.
 */
import { ApiError } from "./errors";
import { FALLBACK_CLAIM_STATUSES, claimStatusLabel } from "./enums";
import { humanize } from "./utils";
import type {
  AdvisorDashboard, AllowedTransition, AssistantAnswer, Attachment, AttachmentKind, Claim, ClaimChecklistItem,
  ClaimEvent, ClaimStatus, ClaimSummary, ClientDashboard, ClientDetail, ClientRequest, ClientRequestDetail, DocumentRecord, EmailMessage,
  EmailThread, FinancialItem, Goal, Insurer, Meta, NetWorth, Page, Policy, Profile, Reminder, RequestTypeDefinition,
  Role, UUID,
} from "./types";

// ---------------------------------------------------------------------------
// Who is "signed in" in mock mode (picked in the dev panel, kept per browser tab)
// ---------------------------------------------------------------------------
const ROLE_KEY = "rs_mock_role";

export function getMockRole(): Role | null {
  try {
    const saved = sessionStorage.getItem(ROLE_KEY);
    return saved === "client" || saved === "advisor" ? saved : null;
  } catch {
    return null;
  }
}

export function setMockRole(role: Role | null): void {
  try {
    if (role) sessionStorage.setItem(ROLE_KEY, role);
    else sessionStorage.removeItem(ROLE_KEY);
  } catch {
    // storage blocked: the role then only lives in React state
  }
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------
const id = (group: number, n: number): UUID =>
  `${group.toString(16).padStart(8, "0")}-0000-4000-8000-${n.toString(16).padStart(12, "0")}`;

const C1 = "0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01"; // Thabo Mokoena: the client you get in mock mode
const C2 = "1c8f4b63-2d5f-4d4a-8f55-3b5a7f2c9b02";
const C3 = "2d9a5c74-3e6a-4e5b-9a66-4c6b8a3d0c03";
const A1 = "c1d2e3f4-0000-4000-8000-000000000001"; // Sarah van der Merwe: the adviser you get in mock mode

const NOW = () => new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
const TODAY = () => NOW().slice(0, 10);
const daysFromNow = (days: number) => new Date(Date.now() + days * 86_400_000).toISOString().slice(0, 10);
const hoursAgo = (hours: number) => new Date(Date.now() - hours * 3_600_000).toISOString().replace(/\.\d{3}Z$/, "Z");

const ADVISER_REF = { id: A1, full_name: "Sarah van der Merwe", email: "adviser@demo.example", phone: "+27 82 987 6543" };

const CLIENTS: Record<UUID, { full_name: string; email: string; phone: string; dob: string; licence: string; since: string; review: string | null }> = {
  [C1]: { full_name: "Thabo Mokoena", email: "client1@demo.example", phone: "+27 82 123 4567", dob: "1985-06-22", licence: daysFromNow(200), since: "2020-03-01", review: "2025-10-15" },
  [C2]: { full_name: "Lerato Dlamini", email: "client2@demo.example", phone: "+27 83 456 7890", dob: "1990-02-14", licence: daysFromNow(20), since: "2022-07-20", review: "2026-01-10" },
  [C3]: { full_name: "Johan Smit", email: "client3@demo.example", phone: "+27 72 345 6789", dob: "1975-11-05", licence: daysFromNow(700), since: "2015-11-01", review: null },
};

const INSURERS: Insurer[] = ["Sanlam", "Old Mutual", "Liberty", "Momentum", "Discovery", "Allan Gray", "Santam", "Other"].map(
  (name, i) => ({ id: id(1, i + 1), name }),
);
const insurer = (name: string): Insurer => INSURERS.find((i) => i.name === name) ?? INSURERS[7];

function policy(n: number, clientId: UUID, ins: string, p: Partial<Policy>): Policy {
  return {
    id: id(2, n), client_id: clientId, insurer: insurer(ins), category: "motor", product_name: "Comprehensive vehicle cover",
    policy_number: `POL-${1000 + n}`, status: "active", asset_description: null, cover_amount_cents: null,
    current_value_cents: null, premium_cents: null, premium_frequency: "monthly", start_date: "2022-04-01",
    renewal_date: daysFromNow(120), valuation_certificate_date: null, ...p,
  };
}

const POLICIES: Policy[] = [
  policy(1, C1, "Santam", { asset_description: "2022 Toyota Hilux 2.8 GD-6, CA 123-456", cover_amount_cents: 65_000_000, premium_cents: 145_000, valuation_certificate_date: "2024-03-15" }),
  policy(2, C1, "Discovery", { category: "health", product_name: "Executive medical aid", cover_amount_cents: null, premium_cents: 420_000, start_date: "2020-01-01", renewal_date: daysFromNow(90) }),
  policy(3, C1, "Allan Gray", { category: "retirement", product_name: "Retirement annuity fund", current_value_cents: 125_000_000, premium_cents: 500_000, start_date: "2015-06-01", renewal_date: daysFromNow(400) }),
  policy(4, C1, "Old Mutual", { category: "life", product_name: "Life cover plus", cover_amount_cents: 500_000_000, premium_cents: 85_000, start_date: "2018-09-01", renewal_date: daysFromNow(300) }),
  policy(5, C2, "Sanlam", { asset_description: "2020 VW Polo, CA 555-666", cover_amount_cents: 24_000_000, premium_cents: 98_000 }),
  policy(6, C3, "Liberty", { category: "investment", product_name: "Tax-free savings", current_value_cents: 48_000_000, premium_cents: 300_000, renewal_date: null }),
];

let FINANCIAL_ITEMS: FinancialItem[] = [
  { id: id(3, 1), client_id: C1, kind: "asset", category: "property", label: "Family home", amount_cents: 320_000_000, as_of_date: "2026-09-01", updated_at: hoursAgo(72) },
  { id: id(3, 2), client_id: C1, kind: "asset", category: "cash", label: "Savings account", amount_cents: 35_000_000, as_of_date: "2026-09-01", updated_at: hoursAgo(72) },
  { id: id(3, 3), client_id: C1, kind: "liability", category: "home_loan", label: "Home loan", amount_cents: 165_000_000, as_of_date: "2026-09-01", updated_at: hoursAgo(72) },
  { id: id(3, 4), client_id: C2, kind: "asset", category: "vehicle", label: "VW Polo", amount_cents: 21_000_000, as_of_date: "2026-08-15", updated_at: hoursAgo(300) },
  { id: id(3, 5), client_id: C3, kind: "liability", category: "credit_card", label: "Credit card", amount_cents: 4_500_000, as_of_date: "2026-08-20", updated_at: hoursAgo(200) },
];

let GOALS: Goal[] = [
  {
    id: id(4, 1), title: "Children's university fund", description: "Shared goal for the household", category: "education", type: "shared",
    status: "active", target_amount_cents: 60_000_000, current_amount_cents: 15_000_000, progress_percent: 25, target_date: "2036-01-31",
    participants: [{ client_id: C1, full_name: CLIENTS[C1].full_name }, { client_id: C2, full_name: CLIENTS[C2].full_name }],
    created_by: A1, created_at: "2025-01-15T10:00:00Z", updated_at: hoursAgo(400),
  },
  {
    id: id(4, 2), title: "Deposit for a new house", description: "In Sandton", category: "property", type: "individual", status: "active",
    target_amount_cents: 35_000_000, current_amount_cents: 30_000_000, progress_percent: 85.7, target_date: "2027-06-30",
    participants: [{ client_id: C1, full_name: CLIENTS[C1].full_name }], created_by: A1, created_at: "2025-05-10T09:15:00Z", updated_at: hoursAgo(120),
  },
  {
    id: id(4, 3), title: "Emergency fund", description: "Six months of expenses", category: "emergency_fund", type: "individual", status: "active",
    target_amount_cents: 12_000_000, current_amount_cents: 7_200_000, progress_percent: 60, target_date: "2026-12-31",
    participants: [{ client_id: C3, full_name: CLIENTS[C3].full_name }], created_by: A1, created_at: "2025-11-20T16:20:00Z", updated_at: hoursAgo(50),
  },
];

let REMINDERS: Reminder[] = [
  {
    id: id(5, 1), type: "licence_expiry", title: `Your driving licence expires on ${CLIENTS[C1].licence}`, description: "Renew it before it expires to stay covered while driving.",
    due_date: CLIENTS[C1].licence, audience: "client", status: "pending", urgency: "upcoming", source: "rule", client: { id: C1, full_name: CLIENTS[C1].full_name },
    related: { resource: "client", id: C1 }, completed_at: null, created_at: hoursAgo(24),
  },
  {
    id: id(5, 2), type: "annual_review", title: "Annual review due", description: "Schedule the yearly portfolio review.", due_date: daysFromNow(15),
    audience: "advisor", status: "pending", urgency: "upcoming", source: "rule", client: { id: C1, full_name: CLIENTS[C1].full_name },
    related: { resource: "client", id: C1 }, completed_at: null, created_at: hoursAgo(48),
  },
  {
    id: id(5, 3), type: "custom", title: "Call about fund switch", description: "Client wants to discuss a lower-risk fund.", due_date: daysFromNow(-2),
    audience: "advisor", status: "pending", urgency: "overdue", source: "manual", client: { id: C3, full_name: CLIENTS[C3].full_name },
    related: null, completed_at: null, created_at: hoursAgo(240),
  },
  {
    id: id(5, 4), type: "valuation_certificate", title: "Vehicle valuation certificate due", description: "Book a new valuation for your vehicle.", due_date: daysFromNow(5),
    audience: "both", status: "pending", urgency: "due_soon", source: "rule", client: { id: C1, full_name: CLIENTS[C1].full_name },
    related: { resource: "policy", id: id(2, 1) }, completed_at: null, created_at: hoursAgo(30),
  },
  {
    id: id(5, 5), type: "licence_expiry", title: `Your driving licence expires on ${CLIENTS[C2].licence}`, description: null, due_date: CLIENTS[C2].licence,
    audience: "client", status: "pending", urgency: "upcoming", source: "rule", client: { id: C2, full_name: CLIENTS[C2].full_name },
    related: { resource: "client", id: C2 }, completed_at: null, created_at: hoursAgo(20),
  },
];

const CHECKLIST: ClaimChecklistItem[] = [
  { id: "road_surface", order: 1, title: "Photograph the road", description: "Photos of the road surface and the direction each vehicle was travelling.", upload_kind: "road_photo" },
  { id: "location", order: 2, title: "Note where you are", description: "The address, or the nearest cross streets.", upload_kind: null },
  { id: "vehicles_people", order: 3, title: "Photograph everything involved", description: "All vehicles and all people involved.", upload_kind: "vehicle_photo" },
  { id: "plates_discs", order: 4, title: "Licence plates and registration discs", description: "A clear photo of each.", upload_kind: "plate_or_disc_photo" },
  { id: "id_documents", order: 5, title: "ID documents", description: "Of everyone involved.", upload_kind: "id_document" },
  { id: "witnesses", order: 6, title: "Witnesses", description: "Names and contact details. You can add a voice note if it is easier.", upload_kind: "witness_voice_note" },
  { id: "other_insurance", order: 7, title: "Other parties' insurance", description: "Their insurer and policy number.", upload_kind: null },
  { id: "police", order: 8, title: "Report it to the police", description: "Do this within 48 hours and keep the case number.", upload_kind: null },
];

const str = (name: string, label: string, required: boolean, extra: Record<string, unknown> = {}) => ({ name, label, type: "string", required, ...extra });
const REQUEST_TYPES = [
  {
    type: "address_change", label: "Change of address", requires_verification: false, max_attachments: 3,
    fields: [
      str("address_line_1", "Street address", true, { max_length: 120 }), str("address_line_2", "Complex / building", false, { max_length: 120 }),
      str("suburb", "Suburb", true, { max_length: 80 }), str("city", "City", true, { max_length: 80 }),
      str("postal_code", "Postal code", true, { pattern: "^[0-9]{4}$" }), { name: "effective_date", label: "Effective from", type: "date", required: false },
    ],
  },
  {
    type: "bank_details_change", label: "Change of bank details", requires_verification: true, max_attachments: 3,
    fields: [
      str("account_holder", "Account holder", true, { max_length: 120 }), str("bank_name", "Bank", true, { max_length: 80 }),
      { name: "account_type", label: "Account type", type: "enum", required: true, options: ["cheque", "savings", "transmission", "other"] },
      str("account_number", "Account number", true, { pattern: "^[0-9]{6,16}$" }), str("branch_code", "Branch code", true, { pattern: "^[0-9]{6}$" }),
      { name: "effective_date", label: "Effective from", type: "date", required: false },
    ],
  },
  {
    type: "policy_document", label: "Request a policy document", requires_verification: false, max_attachments: 0,
    fields: [
      { name: "policy_id", label: "Policy", type: "uuid", required: true, ref: "policy" },
      { name: "document_kind", label: "Document", type: "enum", required: true, options: ["policy_schedule", "policy_wording", "certificate", "other"] },
    ],
  },
  {
    type: "border_letter", label: "Request a border letter", requires_verification: false, max_attachments: 0,
    fields: [
      { name: "policy_id", label: "Vehicle policy", type: "uuid", required: true, ref: "motor_policy" },
      { name: "destination_countries", label: "Countries you will travel to", type: "string_list", required: true, min_items: 1, max_items: 10, max_length: 80 },
      { name: "travel_from", label: "Travel from", type: "date", required: true }, { name: "travel_to", label: "Travel to", type: "date", required: true, not_before: "travel_from" },
    ],
  },
  {
    type: "irp5", label: "Request an IRP5", requires_verification: false, max_attachments: 0,
    fields: [
      str("provider_name", "Investment company", true, { max_length: 120 }), { name: "tax_year", label: "Tax year", type: "integer", required: true, min: 1990, max: 2100 },
      { name: "policy_id", label: "Policy", type: "uuid", required: false, ref: "policy" },
    ],
  },
  {
    type: "consultation", label: "Request a consultation", requires_verification: false, max_attachments: 0,
    fields: [
      { name: "preferred_dates", label: "Preferred dates", type: "date_list", required: true, min_items: 1, max_items: 3, not_in_past: true },
      { name: "mode", label: "How would you like to meet?", type: "enum", required: true, options: ["in_person", "phone", "video"] },
      str("topic", "What would you like to discuss?", true, { max_length: 200 }),
    ],
  },
  {
    type: "client_information", label: "Send financial information", requires_verification: false, max_attachments: 5,
    fields: [
      { name: "statement_type", label: "Statement", type: "enum", required: true, options: ["balance_sheet", "income_statement"] },
      {
        name: "items", label: "Items", type: "object_list", required: true, min_items: 1, max_items: 50,
        item_fields: [
          str("label", "Description", true, { max_length: 120 }),
          { name: "type", label: "Type", type: "enum", required: true, options: ["asset", "liability", "income", "expense"] },
          { name: "amount_cents", label: "Amount (cents)", type: "integer", required: true, min: 1 },
          { name: "frequency", label: "Frequency", type: "enum", required: false, options: ["monthly", "annual", "one_off"] },
        ],
      },
    ],
  },
] as RequestTypeDefinition[];

let REQUESTS: ClientRequestDetail[] = [
  {
    id: id(6, 1), type: "address_change", type_label: "Change of address", status: "submitted", client: { id: C1, full_name: CLIENTS[C1].full_name },
    payload: { address_line_1: "12 Example Road", address_line_2: null, suburb: "Gardens", city: "Cape Town", postal_code: "8001", effective_date: null },
    client_note: "Moved last week.", adviser_response: null, requires_verification: false, attachments: [], submitted_at: hoursAgo(30), updated_at: hoursAgo(30), completed_at: null,
  },
  {
    id: id(6, 2), type: "bank_details_change", type_label: "Change of bank details", status: "completed", client: { id: C2, full_name: CLIENTS[C2].full_name },
    payload: { account_holder: "L Dlamini", bank_name: "FNB", account_type: "cheque", account_number: "******1234", branch_code: "250655", effective_date: null },
    client_note: null, adviser_response: "Updated on all active policies.", requires_verification: true, attachments: [], submitted_at: hoursAgo(700), updated_at: hoursAgo(600), completed_at: hoursAgo(600),
  },
  {
    id: id(6, 3), type: "consultation", type_label: "Request a consultation", status: "in_progress", client: { id: C3, full_name: CLIENTS[C3].full_name },
    payload: { preferred_dates: [daysFromNow(5)], mode: "phone", topic: "Retirement planning" }, client_note: null, adviser_response: null,
    requires_verification: false, attachments: [], submitted_at: hoursAgo(100), updated_at: hoursAgo(90), completed_at: null,
  },
];

const DOCUMENTS: DocumentRecord[] = [
  { id: id(7, 1), title: "Demo Motor Policy Wording (Synthetic)", category: "policy_wording", insurer: insurer("Santam"), page_count: 45, version_label: "v1.2", is_synthetic: true, source_note: "Synthetic demo document", status: "indexed", indexed_at: "2026-09-10T12:00:00Z" },
  { id: id(7, 2), title: "Demo Claims Handling Process (Synthetic)", category: "internal_process", insurer: null, page_count: 12, version_label: "v3.0", is_synthetic: true, source_note: "Synthetic demo document", status: "indexed", indexed_at: "2026-09-10T12:05:00Z" },
  { id: id(7, 3), title: "Demo Compliance Notes (Synthetic)", category: "regulation", insurer: null, page_count: 38, version_label: "2026", is_synthetic: true, source_note: "Synthetic demo document", status: "indexed", indexed_at: "2026-09-10T12:10:00Z" },
  { id: id(7, 4), title: "Demo Data Handling Policy (Synthetic)", category: "company_policy", insurer: null, page_count: 9, version_label: null, is_synthetic: true, source_note: "Synthetic demo document", status: "indexed", indexed_at: "2026-09-10T12:15:00Z" },
];

const person = (name: string, email: string, role: "client" | "insurer" | "other") => ({ name, email, role });
const HANDLER = person("Demo Handler", "handler@insurer.example", "insurer");
const ME_ADVISER = person(ADVISER_REF.full_name, ADVISER_REF.email, "other");

function thread(n: number, p: Partial<EmailThread>): EmailThread {
  return {
    id: id(8, n), subject: "", snippet: "", participants: [], message_count: 1, last_message_at: hoursAgo(5), unread: false, importance: "normal",
    flags: [], link: { client_id: null, claim_id: null, linked_by: null }, is_simulated: true, ...p,
  };
}

const CL_ASSESSMENT = id(9, 2);
const THREADS: EmailThread[] = [
  thread(1, {
    subject: "Claim SC-778201: assessment appointment", snippet: "Please book the vehicle in for assessment at…", participants: [HANDLER, ME_ADVISER],
    message_count: 2, last_message_at: hoursAgo(4), unread: true, importance: "high",
    flags: [{ code: "insurer_sender", label: "From an insurer" }, { code: "claim_reference_match", label: "Mentions claim SC-778201" }],
    link: { client_id: C1, claim_id: CL_ASSESSMENT, linked_by: "auto" },
  }),
  thread(2, {
    subject: "Where is my claim?", snippet: "Hi Sarah, any news on my claim?", participants: [person(CLIENTS[C1].full_name, CLIENTS[C1].email, "client"), ME_ADVISER],
    message_count: 1, last_message_at: hoursAgo(20), unread: true, importance: "high", flags: [{ code: "client_sender", label: "From a client" }],
    link: { client_id: C1, claim_id: null, linked_by: "auto" },
  }),
  thread(3, {
    subject: "Industry newsletter", snippet: "This month in short-term insurance…", participants: [person("Newsletter", "news@industry.example", "other"), ME_ADVISER],
    last_message_at: hoursAgo(90),
  }),
];
const MESSAGES: Record<UUID, EmailMessage[]> = {
  [THREADS[0].id]: [
    { id: id(10, 1), from: ME_ADVISER, to: [HANDLER], cc: [], sent_at: hoursAgo(30), body_text: "Good day,\n\nPlease confirm receipt of the claim for Thabo Mokoena.\n\nKind regards,\nSarah", has_attachments: false },
    { id: id(10, 2), from: HANDLER, to: [ME_ADVISER], cc: [], sent_at: hoursAgo(4), body_text: "Please book the vehicle in for assessment at the Cape Town branch. Our reference is SC-778201.", has_attachments: false },
  ],
  [THREADS[1].id]: [{ id: id(10, 3), from: person(CLIENTS[C1].full_name, CLIENTS[C1].email, "client"), to: [ME_ADVISER], cc: [], sent_at: hoursAgo(20), body_text: "Hi Sarah, any news on my claim?", has_attachments: false }],
  [THREADS[2].id]: [{ id: id(10, 4), from: person("Newsletter", "news@industry.example", "other"), to: [ME_ADVISER], cc: [], sent_at: hoursAgo(90), body_text: "This month in short-term insurance: ...", has_attachments: false }],
};

// ---- claims ----
const STATUS_ORDER: ClaimStatus[] = FALLBACK_CLAIM_STATUSES.map((s) => s.value);

function claimEvent(n: number, type: ClaimEvent["type"], title: string, hours: number, extra: Partial<ClaimEvent> = {}): ClaimEvent {
  return {
    id: id(11, n), type, title, message: null, visible_to_client: true, from_status: null, to_status: null,
    actor: { id: C1, full_name: CLIENTS[C1].full_name, role: "client" }, created_at: hoursAgo(hours), ...extra,
  };
}

function newClaim(n: number, clientId: UUID, status: ClaimStatus, p: Partial<Claim> = {}): Claim {
  const c = CLIENTS[clientId];
  const submitted = status !== "draft";
  return {
    id: id(9, n), reference: submitted ? `CLM-2026-${String(40 + n).padStart(4, "0")}` : null, client: { id: clientId, full_name: c.full_name },
    insurer: insurer("Santam"), status, status_label: "", claim_number: null, incident_occurred_at: submitted ? hoursAgo(50) : null,
    incident_location_text: submitted ? "Corner of Buitenkant St and Roeland St, Cape Town" : null, hire_car_status: "not_required", days_in_status: submitted ? 2 : 0,
    submitted_at: submitted ? hoursAgo(48) : null, updated_at: hoursAgo(3), policy_id: id(2, 1),
    incident: {
      occurred_at: submitted ? hoursAgo(50) : null, location_text: submitted ? "Corner of Buitenkant St and Roeland St, Cape Town" : null,
      location_lat: null, location_lng: null, description: submitted ? "Rear-ended at a red light by a white hatchback." : null,
    },
    police: { reported: submitted ? true : null, case_number: submitted ? "CAS 123/09/2026" : null, station: submitted ? "Cape Town Central" : null, reported_at: null, report_deadline_at: hoursAgo(-48), deadline_status: submitted ? "met" : "pending" },
    driver: { is_policyholder: submitted ? true : null, full_name: submitted ? c.full_name : null, relationship_to_policyholder: null },
    vehicle_use: submitted ? "personal" : null, witnesses: [], third_parties: [],
    insurer_details: { claim_number: null, handler_name: null, handler_email: null, handler_phone: null },
    repair: { repairer_name: null, repairer_phone: null, quote_amount_cents: null, authorised_amount_cents: null, drop_off_date: null, estimated_completion_date: null, completed_at: null },
    hire_car: { status: "not_required", provider: null, delivery_date: null, return_date: null }, review: null,
    missing_fields: [], allowed_transitions: [], attachments: [], timeline: [], created_at: hoursAgo(60), closed_at: null, ...p,
  };
}

let CLAIMS: Claim[] = [
  newClaim(1, C1, "draft", { created_at: hoursAgo(5), updated_at: hoursAgo(5), missing_fields: ["incident.occurred_at", "incident.location_text", "incident.description", "police.reported", "driver.is_policyholder", "driver.full_name", "vehicle_use", "attachments.photo", "attachments.drivers_licence"], timeline: [claimEvent(1, "created", "Claim started", 5)] }),
  newClaim(2, C1, "assessment", {
    claim_number: "SC-778201", insurer_details: { claim_number: "SC-778201", handler_name: "Demo Handler", handler_email: "handler@insurer.example", handler_phone: null },
    witnesses: [{ name: "J. Dlamini", phone: "+27 82 000 0555", email: null, statement: null }],
    third_parties: [{ name: "A. Other", phone: "+27 82 000 0666", drivers_licence_number: null, vehicle_registration: "CA 555-666", vehicle_make_model: "Toyota Yaris", insurer_name: "Some Insurer", policy_number: "POL-999" }],
    timeline: [
      claimEvent(2, "created", "Claim started", 60), claimEvent(3, "submitted", "Claim sent to Royal Square", 48, { from_status: "draft", to_status: "submitted" }),
      claimEvent(4, "status_changed", "Registered with your insurer", 26, { message: "Claim number SC-778201", from_status: "submitted", to_status: "registered", actor: { id: A1, full_name: ADVISER_REF.full_name, role: "advisor" } }),
      claimEvent(5, "status_changed", "Vehicle assessment", 3, { from_status: "registered", to_status: "assessment", actor: { id: A1, full_name: ADVISER_REF.full_name, role: "advisor" } }),
    ],
  }),
  newClaim(3, C3, "in_repair", {
    days_in_status: 9, claim_number: "SL-993412", hire_car_status: "delivered", insurer: insurer("Sanlam"),
    insurer_details: { claim_number: "SL-993412", handler_name: "Pieter Nel", handler_email: "pieter@insurer.example", handler_phone: null },
    repair: { repairer_name: "Bay Panel Beaters", repairer_phone: "+27 21 555 0100", quote_amount_cents: 4_850_000, authorised_amount_cents: 4_850_000, drop_off_date: daysFromNow(-9), estimated_completion_date: daysFromNow(4), completed_at: null },
    hire_car: { status: "delivered", provider: "Demo Car Hire", delivery_date: daysFromNow(-9), return_date: null },
    timeline: [claimEvent(6, "submitted", "Claim sent to Royal Square", 400, { actor: { id: C3, full_name: CLIENTS[C3].full_name, role: "client" } }), claimEvent(7, "repair_update", "Repair update", 20, { message: "Panel beating complete, spray painting starts Monday.", actor: { id: A1, full_name: ADVISER_REF.full_name, role: "advisor" } })],
  }),
  newClaim(4, C2, "submitted", { days_in_status: 1, submitted_at: hoursAgo(20), timeline: [claimEvent(8, "submitted", "Claim sent to Royal Square", 20, { actor: { id: C2, full_name: CLIENTS[C2].full_name, role: "client" } })] }),
];

let ID_SEQ = 1000;
const nextId = (group: number) => id(group, ID_SEQ++);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
type Query = URLSearchParams;
interface Ctx { params: string[]; query: Query; body: any; role: Role } // eslint-disable-line @typescript-eslint/no-explicit-any

const currentRole = (): Role => getMockRole() ?? "client";
const ownClientIds = (role: Role): UUID[] => (role === "advisor" ? [C1, C2, C3] : [C1]);

function notFound(what = "That item"): never {
  throw new ApiError(404, { error: { code: "not_found", message: `${what} was not found.`, request_id: "mock" } });
}
function forbidden(message: string): never {
  throw new ApiError(403, { error: { code: "forbidden", message, request_id: "mock" } });
}
function conflict(message: string): never {
  throw new ApiError(409, { error: { code: "invalid_state_transition", message, request_id: "mock" } });
}
function invalid(field: string, message: string, code = "required"): never {
  throw new ApiError(422, { error: { code: "validation_error", message: "One or more fields are invalid.", details: [{ field, code, message }], request_id: "mock" } });
}
const requireRole = (role: Role, wanted: Role) => {
  if (role !== wanted) forbidden(wanted === "advisor" ? "This action is only available to advisers." : "This action is only available to clients.");
};

function paginate<T>(items: T[], q: Query): Page<T> {
  const limit = Math.min(Math.max(Number(q.get("limit")) || 25, 1), 100);
  const offset = Math.max(Number(q.get("offset")) || 0, 0);
  return { items: items.slice(offset, offset + limit), total: items.length, limit, offset };
}

function clientScope(role: Role, q: Query): UUID[] {
  const wanted = q.get("client_id");
  const own = ownClientIds(role);
  if (!wanted) return own;
  if (!own.includes(wanted)) notFound("That client");
  return [wanted];
}

function profileFor(role: Role): Profile {
  if (role === "advisor") {
    return { id: A1, email: ADVISER_REF.email, full_name: ADVISER_REF.full_name, role: "advisor", phone: ADVISER_REF.phone, created_at: "2019-01-10T08:00:00Z", client: null, advisor: { id: A1 } };
  }
  const c = CLIENTS[C1];
  return {
    id: C1, email: c.email, full_name: c.full_name, role: "client", phone: c.phone, created_at: "2026-01-15T08:00:00Z", advisor: null,
    client: { id: C1, adviser: ADVISER_REF, date_of_birth: c.dob, drivers_licence_expiry: c.licence, client_since: c.since, last_annual_review_date: c.review },
  };
}

export function getMockProfile(role: Role): Profile {
  return profileFor(role);
}

function clientDetail(clientId: UUID): ClientDetail {
  const c = CLIENTS[clientId];
  return {
    id: clientId, full_name: c.full_name, email: c.email, phone: c.phone, date_of_birth: c.dob, drivers_licence_expiry: c.licence, client_since: c.since,
    last_annual_review_date: c.review,
    counts: {
      policies: POLICIES.filter((p) => p.client_id === clientId).length,
      open_claims: CLAIMS.filter((x) => x.client.id === clientId && x.status !== "draft" && x.status !== "closed").length,
      active_goals: GOALS.filter((g) => g.status === "active" && g.participants.some((p) => p.client_id === clientId)).length,
      pending_requests: REQUESTS.filter((r) => r.client.id === clientId && (r.status === "submitted" || r.status === "in_progress")).length,
      pending_reminders: REMINDERS.filter((r) => r.client.id === clientId && r.status === "pending").length,
    },
    created_at: "2026-01-15T08:00:00Z",
  };
}

/** List endpoints and dashboards return requests WITHOUT attachments (only GET /requests/{id} and POST include them). */
function listShape(r: ClientRequestDetail): ClientRequest {
  const copy: Partial<ClientRequestDetail> = { ...r };
  delete copy.attachments;
  return copy as ClientRequest;
}

function urgencyOf(dueDate: string): Reminder["urgency"] {
  const today = TODAY();
  if (dueDate < today) return "overdue";
  return dueDate <= daysFromNow(7) ? "due_soon" : "upcoming";
}
const refreshReminders = () => {
  REMINDERS = REMINDERS.map((r) => (r.status === "pending" ? { ...r, urgency: urgencyOf(r.due_date) } : r));
};
function remindersFor(role: Role, q: Query): Reminder[] {
  refreshReminders();
  const scope = clientScope(role, q);
  const status = q.get("status") ?? "pending";
  return REMINDERS.filter((r) => scope.includes(r.client.id))
    .filter((r) => (role === "client" ? r.audience !== "advisor" : true))
    .filter((r) => (status === "all" ? true : r.status === status))
    .filter((r) => (q.get("type") ? r.type === q.get("type") : true))
    .filter((r) => (q.get("urgency") ? r.urgency === q.get("urgency") : true))
    .filter((r) => (q.get("audience") && role === "advisor" ? r.audience === q.get("audience") : true))
    .sort((a, b) => (q.get("sort") === "-due_date" ? b.due_date.localeCompare(a.due_date) : a.due_date.localeCompare(b.due_date)));
}

function netWorthFor(clientId: UUID): NetWorth {
  const items = FINANCIAL_ITEMS.filter((f) => f.client_id === clientId);
  const breakdown: NetWorth["breakdown"] = [];
  for (const kind of ["asset", "liability"] as const) {
    const byCategory = new Map<string, number>();
    for (const f of items.filter((x) => x.kind === kind)) byCategory.set(f.category, (byCategory.get(f.category) ?? 0) + f.amount_cents);
    byCategory.forEach((total, category) => breakdown.push({ kind, category: category as FinancialItem["category"], source: "balance_sheet", total_cents: total }));
  }
  for (const p of POLICIES.filter((x) => x.client_id === clientId && x.status === "active" && (x.category === "investment" || x.category === "retirement") && x.current_value_cents)) {
    breakdown.push({ kind: "asset", category: p.category === "retirement" ? "retirement" : "investments", source: "policy", total_cents: p.current_value_cents ?? 0 });
  }
  const assets = breakdown.filter((b) => b.kind === "asset").reduce((s, b) => s + b.total_cents, 0);
  const liabilities = breakdown.filter((b) => b.kind === "liability").reduce((s, b) => s + b.total_cents, 0);
  return { currency: "ZAR", total_assets_cents: assets, total_liabilities_cents: liabilities, net_worth_cents: assets - liabilities, as_of: TODAY(), breakdown };
}

function transitionsFor(claim: Claim, role: Role): AllowedTransition[] {
  if (role !== "advisor" || claim.status === "draft" || claim.status === "closed") return [];
  const i = STATUS_ORDER.indexOf(claim.status);
  const out: AllowedTransition[] = [];
  const next = STATUS_ORDER[i + 1];
  if (next) {
    out.push({
      to_status: next, direction: "forward", label: `Move to ${humanize(next).toLowerCase()}`, actor: "advisor",
      requires: next === "registered" && !claim.insurer_details.claim_number ? ["insurer_details.claim_number"] : [],
    });
  }
  const prev = STATUS_ORDER[i - 1];
  if (prev && prev !== "draft") out.push({ to_status: prev, direction: "back", label: `Move back to ${humanize(prev).toLowerCase()}`, requires: [], actor: "advisor" });
  return out;
}

function claimView(claim: Claim, role: Role): Claim {
  return {
    ...claim, status_label: claimStatusLabel(claim.status, role), allowed_transitions: transitionsFor(claim, role),
    timeline: role === "client" ? claim.timeline.filter((e) => e.visible_to_client) : claim.timeline,
  };
}

function summaryOf(claim: Claim, role: Role): ClaimSummary {
  return {
    id: claim.id, reference: claim.reference, client: claim.client, insurer: claim.insurer, status: claim.status, status_label: claimStatusLabel(claim.status, role),
    claim_number: claim.insurer_details.claim_number, incident_occurred_at: claim.incident.occurred_at, incident_location_text: claim.incident.location_text,
    hire_car_status: claim.hire_car.status, days_in_status: claim.days_in_status, submitted_at: claim.submitted_at, updated_at: claim.updated_at,
  };
}

function visibleClaims(role: Role, q?: Query): Claim[] {
  const scope = q ? clientScope(role, q) : ownClientIds(role);
  return CLAIMS.filter((c) => scope.includes(c.client.id) && (role === "advisor" ? c.status !== "draft" : true));
}

function findClaim(role: Role, claimId: string): Claim {
  const claim = visibleClaims(role).find((c) => c.id === claimId);
  return claim ?? notFound("That claim");
}

function touch(claim: Claim, event?: ClaimEvent): Claim {
  claim.updated_at = NOW();
  if (event) claim.timeline = [...claim.timeline, event];
  return claim;
}

function missingFields(c: Claim): string[] {
  const missing: string[] = [];
  if (!c.insurer) missing.push("insurer_id");
  if (!c.incident.occurred_at) missing.push("incident.occurred_at");
  if (!c.incident.location_text) missing.push("incident.location_text");
  if (!c.incident.description) missing.push("incident.description");
  if (c.police.reported === null) missing.push("police.reported");
  if (c.police.reported && !c.police.case_number) missing.push("police.case_number");
  if (c.driver.is_policyholder === null) missing.push("driver.is_policyholder");
  if (!c.driver.full_name) missing.push("driver.full_name");
  if (c.driver.is_policyholder === false && !c.driver.relationship_to_policyholder) missing.push("driver.relationship_to_policyholder");
  if (!c.vehicle_use) missing.push("vehicle_use");
  const photoKinds: AttachmentKind[] = ["road_photo", "vehicle_photo", "people_photo", "plate_or_disc_photo"];
  if (!c.attachments.some((a) => photoKinds.includes(a.kind))) missing.push("attachments.photo");
  if (!c.attachments.some((a) => a.kind === "drivers_licence")) missing.push("attachments.drivers_licence");
  return missing;
}

function metaResponse(): Meta {
  return {
    api_version: "v1", currency: "ZAR", claim_statuses: FALLBACK_CLAIM_STATUSES,
    hire_car_statuses: ["not_required", "requested", "arranged", "delivered", "return_arranged", "returned"],
    reminder_types: [
      { type: "valuation_certificate", label: "Valuation certificate due", default_audience: "both", lead_days: 30 },
      { type: "licence_expiry", label: "Driving licence expiring", default_audience: "client", lead_days: 60 },
      { type: "annual_review", label: "Annual financial review", default_audience: "advisor", lead_days: 30 },
      { type: "retirement_fee_renewal", label: "Retirement fee renewal", default_audience: "advisor", lead_days: 30 },
      { type: "birthday", label: "Client birthday", default_audience: "advisor", lead_days: 7 },
      { type: "anniversary", label: "Client anniversary", default_audience: "advisor", lead_days: 7 },
      { type: "claim_police_report", label: "Report to police within 48 hours", default_audience: "client", lead_days: 2 },
      { type: "custom", label: "Custom reminder", default_audience: "advisor", lead_days: null },
    ],
    request_types: REQUEST_TYPES.map((t) => ({ type: t.type, label: t.label, requires_verification: t.requires_verification })),
    policy_categories: ["motor", "life", "health", "funeral", "personal_other", "commercial", "investment", "retirement"],
    policy_statuses: ["active", "pending", "lapsed", "cancelled"],
    financial_item_categories: {
      asset: ["property", "vehicle", "cash", "investments", "retirement", "business", "other_asset"],
      liability: ["home_loan", "vehicle_finance", "credit_card", "personal_loan", "other_liability"],
    },
    goal_categories: ["retirement", "education", "property", "emergency_fund", "travel", "debt_repayment", "other"],
    document_categories: ["policy_wording", "internal_process", "company_policy", "regulation"],
    attachment_rules: {
      max_bytes: 10_485_760, max_per_claim: 40, max_per_request: 5,
      content_types: { image: ["image/jpeg", "image/png", "image/webp"], document: ["application/pdf"], audio: ["audio/webm", "audio/mp4", "audio/mpeg", "audio/ogg", "audio/wav"] },
      kinds: [
        { kind: "road_photo", accepts: ["image"] }, { kind: "vehicle_photo", accepts: ["image"] }, { kind: "people_photo", accepts: ["image"] },
        { kind: "plate_or_disc_photo", accepts: ["image"] }, { kind: "id_document", accepts: ["image", "document"] }, { kind: "witness_voice_note", accepts: ["audio"] },
        { kind: "drivers_licence", accepts: ["image", "document"] }, { kind: "accident_sketch", accepts: ["image"] }, { kind: "other", accepts: ["image", "document"] },
      ],
    },
  };
}

function clientDashboard(role: Role, clientId: UUID): ClientDashboard {
  const isAdvisorView = role === "advisor";
  refreshReminders();
  const claims = CLAIMS.filter((c) => c.client.id === clientId && c.status !== "closed" && (isAdvisorView ? c.status !== "draft" : true));
  const reminders = REMINDERS.filter((r) => r.client.id === clientId && r.status === "pending" && (isAdvisorView ? true : r.audience !== "advisor"));
  const pending = REQUESTS.filter((r) => r.client.id === clientId && (r.status === "submitted" || r.status === "in_progress"));
  const c = CLIENTS[clientId];
  const policies = POLICIES.filter((p) => p.client_id === clientId);
  return {
    generated_at: NOW(), client: { id: clientId, full_name: c.full_name, email: c.email, phone: c.phone }, adviser: ADVISER_REF, net_worth: netWorthFor(clientId),
    policies: { count: policies.length, items: policies }, open_claims: { count: claims.length, items: claims.map((x) => summaryOf(x, role)) },
    goals: { items: GOALS.filter((g) => g.status === "active" && g.participants.some((p) => p.client_id === clientId)) },
    reminders: { overdue_count: reminders.filter((r) => r.urgency === "overdue").length, upcoming: reminders.slice(0, 5) },
    pending_requests: { count: pending.length, items: pending.slice(0, 5).map(listShape) },
  };
}

function advisorDashboard(): AdvisorDashboard {
  const role: Role = "advisor";
  refreshReminders();
  const claims = visibleClaims(role).filter((c) => c.status !== "closed");
  const pendingReminders = REMINDERS.filter((r) => r.status === "pending");
  const needs: AdvisorDashboard["needs_attention"] = [];
  for (const r of pendingReminders.filter((x) => x.urgency === "overdue")) {
    needs.push({ kind: "reminder", id: r.id, title: r.title, subtitle: `${r.client.full_name} · overdue`, client: r.client, due_at: new Date(`${r.due_date}T00:00:00+02:00`).toISOString().replace(/\.\d{3}Z$/, "Z"), link: { resource: "reminder", id: r.id } });
  }
  for (const c of claims.filter((x) => x.status === "submitted")) {
    needs.push({ kind: "claim", id: c.id, title: `New claim submitted: ${c.reference}`, subtitle: `${c.client.full_name} · ${c.insurer?.name ?? "No insurer"}`, client: c.client, due_at: null, link: { resource: "claim", id: c.id } });
  }
  for (const r of REQUESTS.filter((x) => x.status === "submitted")) {
    needs.push({ kind: "request", id: r.id, title: `New request: ${r.type_label}`, subtitle: r.client.full_name, client: r.client, due_at: null, link: { resource: "request", id: r.id } });
  }
  return {
    generated_at: NOW(),
    counts: {
      clients: 3, open_claims: claims.length, pending_requests: REQUESTS.filter((r) => r.status === "submitted" || r.status === "in_progress").length,
      reminders_due_7d: pendingReminders.filter((r) => r.due_date <= daysFromNow(7)).length, overdue_reminders: pendingReminders.filter((r) => r.urgency === "overdue").length,
    },
    claims_by_status: STATUS_ORDER.filter((s) => s !== "draft" && s !== "closed")
      .map((status) => ({ status, label: claimStatusLabel(status, role), count: claims.filter((c) => c.status === status).length }))
      .filter((s) => s.count > 0),
    needs_attention: needs.slice(0, 10),
    upcoming_reminders: pendingReminders.filter((r) => r.due_date <= daysFromNow(14)).slice(0, 10),
  };
}

function assistantAnswer(question: string): AssistantAnswer {
  const grounded = /notif|claim|report|police|deadline/i.test(question);
  return grounded
    ? {
        conversation_id: nextId(12), message_id: nextId(13), grounded: true,
        answer: "The demo policy wording asks the insured to notify the insurer within 30 days of the event [1]. The internal claims process also requires the adviser to log the claim the same day [2].",
        citations: [
          { index: 1, document_id: DOCUMENTS[0].id, document_title: DOCUMENTS[0].title, category: "policy_wording", is_synthetic: true, page: 12, quote: "The insured must notify the insurer of any event likely to give rise to a claim within 30 days…" },
          { index: 2, document_id: DOCUMENTS[1].id, document_title: DOCUMENTS[1].title, category: "internal_process", is_synthetic: true, page: 3, quote: "Log every new claim in the register on the day it is received…" },
        ],
        model: { provider: "none", name: "mock" }, latency_ms: 420,
      }
    : {
        conversation_id: nextId(12), message_id: nextId(13), grounded: false, citations: [],
        answer: "I couldn't find this in the approved documents. Try rephrasing, or check the document library.", model: { provider: "none", name: "" }, latency_ms: 12,
      };
}

// ---------------------------------------------------------------------------
// Route table
// ---------------------------------------------------------------------------
type Handler = (ctx: Ctx) => unknown;
const routes: [string, RegExp, Handler][] = [];
const on = (method: string, pattern: string, handler: Handler) => {
  routes.push([method, new RegExp(`^${pattern.replace(/:id/g, "([^/]+)")}$`), handler]);
};

// system + identity
on("GET", "/meta", () => metaResponse());
on("GET", "/me", ({ role }) => profileFor(role));
on("PATCH", "/me", ({ role, body }) => {
  if (body && "phone" in body) {
    if (role === "client") CLIENTS[C1].phone = String(body.phone ?? "");
    else ADVISER_REF.phone = String(body.phone ?? "");
  }
  if (body && role === "client" && "drivers_licence_expiry" in body) CLIENTS[C1].licence = body.drivers_licence_expiry;
  return profileFor(role);
});
on("GET", "/me/dashboard", ({ role }) => (requireRole(role, "client"), clientDashboard("client", C1)));
on("GET", "/advisor/dashboard", ({ role }) => (requireRole(role, "advisor"), advisorDashboard()));

// clients
on("GET", "/clients", ({ role, query }) => {
  requireRole(role, "advisor");
  const search = (query.get("search") ?? "").toLowerCase();
  let list = [C1, C2, C3].map(clientDetail).filter((c) => !search || c.full_name.toLowerCase().includes(search) || c.email.toLowerCase().includes(search));
  if (query.get("sort") === "-full_name") list = list.reverse();
  return paginate(list, query);
});
on("GET", "/clients/:id", ({ role, params }) => (requireRole(role, "advisor"), CLIENTS[params[0]] ? clientDetail(params[0]) : notFound("That client")));
on("PATCH", "/clients/:id", ({ role, params, body }) => {
  requireRole(role, "advisor");
  const c = CLIENTS[params[0]] ?? notFound("That client");
  if (body?.full_name) c.full_name = body.full_name;
  if ("phone" in (body ?? {})) c.phone = body.phone ?? "";
  if (body?.drivers_licence_expiry) c.licence = body.drivers_licence_expiry;
  return clientDetail(params[0]);
});
on("GET", "/clients/:id/dashboard", ({ role, params }) => (requireRole(role, "advisor"), CLIENTS[params[0]] ? clientDashboard("advisor", params[0]) : notFound("That client")));

// reference + money
on("GET", "/insurers", () => ({ items: INSURERS }));
on("GET", "/policies", ({ role, query }) => {
  const scope = clientScope(role, query);
  const list = POLICIES.filter((p) => scope.includes(p.client_id))
    .filter((p) => (query.get("category") ? p.category === query.get("category") : true))
    .filter((p) => (query.get("status") ? p.status === query.get("status") : true));
  return paginate(list, query);
});
on("GET", "/policies/:id", ({ role, params }) => POLICIES.find((p) => p.id === params[0] && ownClientIds(role).includes(p.client_id)) ?? notFound("That policy"));
on("GET", "/net-worth", ({ role, query }) => {
  const scope = clientScope(role, query);
  if (role === "advisor" && !query.get("client_id")) invalid("client_id", "client_id is required.");
  return netWorthFor(scope[0]);
});
on("GET", "/financial-items", ({ role, query }) => {
  const scope = clientScope(role, query);
  if (role === "advisor" && !query.get("client_id")) invalid("client_id", "client_id is required.");
  return paginate(FINANCIAL_ITEMS.filter((f) => scope.includes(f.client_id) && (query.get("kind") ? f.kind === query.get("kind") : true)), query);
});
on("POST", "/financial-items", ({ role, body }) => {
  requireRole(role, "advisor");
  if (!ownClientIds(role).includes(body?.client_id)) notFound("That client");
  if (!(Number.isInteger(body?.amount_cents) && body.amount_cents > 0)) invalid("amount_cents", "Enter an amount greater than 0.", "too_small");
  const item: FinancialItem = { id: nextId(3), client_id: body.client_id, kind: body.kind, category: body.category, label: body.label, amount_cents: body.amount_cents, as_of_date: body.as_of_date, updated_at: NOW() };
  FINANCIAL_ITEMS = [...FINANCIAL_ITEMS, item];
  return item;
});

// goals
const goalProgress = (g: Goal) => Math.min(100, Math.round((g.current_amount_cents / g.target_amount_cents) * 1000) / 10);
on("GET", "/goals", ({ role, query }) => {
  const scope = clientScope(role, query);
  const status = query.get("status") ?? "active";
  return paginate(GOALS.filter((g) => g.participants.some((p) => scope.includes(p.client_id))).filter((g) => (status === "all" ? true : g.status === status)), query);
});
on("GET", "/goals/:id", ({ role, params }) => GOALS.find((g) => g.id === params[0] && g.participants.some((p) => ownClientIds(role).includes(p.client_id))) ?? notFound("That goal"));
on("POST", "/goals", ({ role, body }) => {
  requireRole(role, "advisor");
  const ids: UUID[] = Array.isArray(body?.client_ids) ? body.client_ids : [];
  if (!ids.length) invalid("client_ids", "Choose at least one client.", "too_short");
  if (!body.title) invalid("title", "Enter a title.", "too_short");
  if (!(body.target_amount_cents > 0)) invalid("target_amount_cents", "Enter a target greater than 0.", "too_small");
  const goal: Goal = {
    id: nextId(4), title: body.title, description: body.description ?? null, category: body.category ?? "other", type: ids.length > 1 ? "shared" : "individual", status: "active",
    target_amount_cents: body.target_amount_cents, current_amount_cents: body.current_amount_cents ?? 0, progress_percent: 0, target_date: body.target_date ?? null,
    participants: ids.filter((c) => CLIENTS[c]).map((c) => ({ client_id: c, full_name: CLIENTS[c].full_name })), created_by: A1, created_at: NOW(), updated_at: NOW(),
  };
  goal.progress_percent = goalProgress(goal);
  GOALS = [...GOALS, goal];
  return goal;
});
on("PATCH", "/goals/:id", ({ role, params, body }) => {
  requireRole(role, "advisor");
  const goal = GOALS.find((g) => g.id === params[0]) ?? notFound("That goal");
  for (const key of ["title", "description", "category", "target_amount_cents", "current_amount_cents", "target_date", "status"] as const) {
    if (body && key in body) (goal as unknown as Record<string, unknown>)[key] = body[key];
  }
  goal.progress_percent = goalProgress(goal);
  if (goal.status === "active" && goal.current_amount_cents >= goal.target_amount_cents) goal.status = "achieved";
  goal.updated_at = NOW();
  return goal;
});
on("DELETE", "/goals/:id", ({ role, params }) => {
  requireRole(role, "advisor");
  const goal = GOALS.find((g) => g.id === params[0]) ?? notFound("That goal");
  goal.status = "archived";
  return undefined;
});

// reminders
on("GET", "/reminders", ({ role, query }) => paginate(remindersFor(role, query), query));
on("POST", "/reminders", ({ role, body }) => {
  requireRole(role, "advisor");
  const c = CLIENTS[body?.client_id] ?? notFound("That client");
  if (!body.title) invalid("title", "Enter a title.", "too_short");
  const reminder: Reminder = {
    id: nextId(5), type: body.type ?? "custom", title: body.title, description: body.description ?? null, due_date: body.due_date, audience: body.audience ?? "advisor",
    status: "pending", urgency: urgencyOf(body.due_date), source: "manual", client: { id: body.client_id, full_name: c.full_name }, related: null, completed_at: null, created_at: NOW(),
  };
  REMINDERS = [...REMINDERS, reminder];
  return reminder;
});
on("PATCH", "/reminders/:id", ({ role, params, body }) => {
  requireRole(role, "advisor");
  const r = REMINDERS.find((x) => x.id === params[0]) ?? notFound("That reminder");
  for (const key of ["title", "description", "due_date", "audience", "status"] as const) if (body && key in body) (r as unknown as Record<string, unknown>)[key] = body[key];
  r.urgency = urgencyOf(r.due_date);
  return r;
});
on("POST", "/reminders/run-check", ({ role }) => (requireRole(role, "advisor"), { evaluated_clients: 3, created: 0, already_existing: REMINDERS.filter((r) => r.source === "rule").length }));
on("POST", "/reminders/:id/complete", ({ role, params }) => {
  const r = remindersFor(role, new URLSearchParams("status=all")).find((x) => x.id === params[0]) ?? notFound("That reminder");
  if (r.status === "done") conflict("This reminder is already done.");
  r.status = "done";
  r.completed_at = NOW();
  return r;
});
on("DELETE", "/reminders/:id", ({ role, params }) => {
  requireRole(role, "advisor");
  const r = REMINDERS.find((x) => x.id === params[0]) ?? notFound("That reminder");
  if (r.source === "rule") throw new ApiError(409, { error: { code: "conflict", message: "Automatic reminders can be dismissed but not deleted.", request_id: "mock" } });
  REMINDERS = REMINDERS.filter((x) => x.id !== r.id);
  return undefined;
});

// claims
on("GET", "/claims/checklist", () => ({ items: CHECKLIST }));
on("GET", "/claims/pipeline", ({ role, query }) => {
  requireRole(role, "advisor");
  const includeClosed = query.get("include_closed") === "true";
  const claims = visibleClaims(role, query);
  const statuses = STATUS_ORDER.filter((s) => s !== "draft" && (includeClosed || s !== "closed"));
  return {
    columns: statuses.map((status) => {
      const inColumn = claims.filter((c) => c.status === status).sort((a, b) => (a.submitted_at ?? "").localeCompare(b.submitted_at ?? ""));
      return { status, label: claimStatusLabel(status, role), count: inColumn.length, claims: inColumn.slice(0, 50).map((c) => summaryOf(c, role)) };
    }),
  };
});
on("GET", "/claims", ({ role, query }) => {
  const statuses = query.getAll("status");
  const search = (query.get("search") ?? "").toLowerCase();
  const list = visibleClaims(role, query)
    .filter((c) => (statuses.length ? statuses.includes(c.status) : true))
    .filter((c) => (query.get("open") === "true" ? c.status !== "closed" : true))
    .filter((c) => !search || [c.reference, c.insurer_details.claim_number, c.client.full_name].some((v) => v?.toLowerCase().includes(search)))
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  return paginate(list.map((c) => summaryOf(c, role)), query);
});
on("POST", "/claims", ({ role, body }) => {
  requireRole(role, "client");
  const claim = newClaim(ID_SEQ++, C1, "draft", {
    id: nextId(9), created_at: NOW(), updated_at: NOW(), policy_id: body?.policy_id ?? null,
    insurer: INSURERS.find((i) => i.id === body?.insurer_id) ?? (body?.policy_id ? POLICIES.find((p) => p.id === body.policy_id)?.insurer ?? null : null),
    timeline: [claimEvent(ID_SEQ++, "created", "Claim started", 0)],
  });
  claim.missing_fields = missingFields(claim);
  CLAIMS = [claim, ...CLAIMS];
  return claimView(claim, role);
});
on("GET", "/claims/:id", ({ role, params }) => claimView(findClaim(role, params[0]), role));
on("PATCH", "/claims/:id", ({ role, params, body }) => {
  requireRole(role, "client");
  const claim = findClaim(role, params[0]);
  if (claim.status !== "draft") conflict("This claim has already been sent and can no longer be edited.");
  if (body?.insurer_id) claim.insurer = INSURERS.find((i) => i.id === body.insurer_id) ?? claim.insurer;
  for (const group of ["incident", "police", "driver"] as const) if (body?.[group]) Object.assign(claim[group], body[group]);
  for (const key of ["vehicle_use", "witnesses", "third_parties"] as const) if (body && key in body) (claim as unknown as Record<string, unknown>)[key] = body[key];
  claim.incident_occurred_at = claim.incident.occurred_at;
  claim.incident_location_text = claim.incident.location_text;
  claim.missing_fields = missingFields(claim);
  return claimView(touch(claim), role);
});
on("POST", "/claims/:id/attachments", ({ role, params, body }) => {
  requireRole(role, "client");
  const claim = findClaim(role, params[0]);
  if (claim.status === "closed") conflict("This claim is closed.");
  const form = body as FormData;
  const file = form instanceof FormData ? (form.get("file") as File | null) : null;
  if (!file) invalid("file", "Choose a file to upload.");
  const attachment: Attachment = {
    id: nextId(14), kind: (form.get("kind") as AttachmentKind) ?? "other", label: (form.get("label") as string) || null, filename: file.name, content_type: file.type || "application/octet-stream",
    size_bytes: file.size, uploaded_by: C1, uploaded_at: NOW(), url: URL.createObjectURL(file), url_expires_at: hoursAgo(-1),
  };
  claim.attachments = [...claim.attachments, attachment];
  claim.missing_fields = claim.status === "draft" ? missingFields(claim) : [];
  touch(claim, claim.status === "draft" ? undefined : claimEvent(ID_SEQ++, "attachment_added", "A document was added", 0));
  return attachment;
});
on("DELETE", "/claims/:id/attachments/:id", ({ role, params }) => {
  requireRole(role, "client");
  const claim = findClaim(role, params[0]);
  if (claim.status !== "draft") conflict("Documents can't be removed once a claim has been sent.");
  claim.attachments = claim.attachments.filter((a) => a.id !== params[1]);
  claim.missing_fields = missingFields(claim);
  return undefined;
});
on("POST", "/claims/:id/submit", ({ role, params }) => {
  requireRole(role, "client");
  const claim = findClaim(role, params[0]);
  if (claim.status !== "draft") conflict("This claim has already been sent.");
  const missing = missingFields(claim);
  if (missing.length) throw new ApiError(422, { error: { code: "validation_error", message: "One or more fields are invalid.", details: missing.map((field) => ({ field, code: "required", message: "This is required to send your claim." })), request_id: "mock" } });
  claim.status = "submitted";
  claim.reference = `CLM-2026-${String(41 + CLAIMS.filter((c) => c.reference).length).padStart(4, "0")}`;
  claim.submitted_at = NOW();
  claim.days_in_status = 0;
  claim.missing_fields = [];
  return claimView(touch(claim, claimEvent(ID_SEQ++, "submitted", "Claim sent to Royal Square", 0, { from_status: "draft", to_status: "submitted" })), role);
});
on("PATCH", "/claims/:id/insurer-details", ({ role, params, body }) => {
  requireRole(role, "advisor");
  const claim = findClaim(role, params[0]);
  Object.assign(claim.insurer_details, body);
  claim.claim_number = claim.insurer_details.claim_number;
  return claimView(touch(claim, claimEvent(ID_SEQ++, "insurer_details_updated", "Insurer details updated", 0, { actor: { id: A1, full_name: ADVISER_REF.full_name, role: "advisor" } })), role);
});
on("POST", "/claims/:id/transitions", ({ role, params, body }) => {
  requireRole(role, "advisor");
  const claim = findClaim(role, params[0]);
  const allowed = transitionsFor(claim, role).find((t) => t.to_status === body?.to_status);
  if (!allowed) conflict("That status change is not allowed from here.");
  if (allowed.requires.length) invalid(allowed.requires[0], "Add the insurer's claim number first.");
  const from = claim.status;
  claim.status = allowed.to_status;
  claim.days_in_status = 0;
  if (claim.status === "closed") claim.closed_at = NOW();
  return claimView(touch(claim, claimEvent(ID_SEQ++, "status_changed", claimStatusLabel(claim.status, "client"), 0, { message: body?.note ?? null, visible_to_client: body?.visible_to_client ?? true, from_status: from, to_status: claim.status, actor: { id: A1, full_name: ADVISER_REF.full_name, role: "advisor" } })), role);
});
on("PATCH", "/claims/:id/repair-details", ({ role, params, body }) => {
  requireRole(role, "advisor");
  const claim = findClaim(role, params[0]);
  Object.assign(claim.repair, body);
  return claimView(touch(claim), role);
});
on("POST", "/claims/:id/repair-date", ({ role, params, body }) => {
  requireRole(role, "client");
  const claim = findClaim(role, params[0]);
  if (claim.status !== "authorised") conflict("You can choose a drop-off date once the repairs are approved.");
  claim.repair.drop_off_date = body?.drop_off_date ?? null;
  return claimView(touch(claim, claimEvent(ID_SEQ++, "repair_date_chosen", "Drop-off date chosen", 0)), role);
});
on("PATCH", "/claims/:id/hire-car", ({ role, params, body }) => {
  requireRole(role, "advisor");
  const claim = findClaim(role, params[0]);
  Object.assign(claim.hire_car, body);
  claim.hire_car_status = claim.hire_car.status;
  return claimView(touch(claim, claimEvent(ID_SEQ++, "hire_car_updated", "Hire car updated", 0, { actor: { id: A1, full_name: ADVISER_REF.full_name, role: "advisor" } })), role);
});
on("POST", "/claims/:id/updates", ({ role, params, body }) => {
  requireRole(role, "advisor");
  const claim = findClaim(role, params[0]);
  if (!body?.message) invalid("message", "Write a message.", "too_short");
  const type = body.type === "repair_update" ? "repair_update" : "note";
  const event = claimEvent(ID_SEQ++, type, type === "note" ? "Note added" : "Repair update", 0, { message: body.message, visible_to_client: body.visible_to_client ?? type === "repair_update", actor: { id: A1, full_name: ADVISER_REF.full_name, role: "advisor" } });
  touch(claim, event);
  return event;
});
on("POST", "/claims/:id/review", ({ role, params, body }) => {
  requireRole(role, "client");
  const claim = findClaim(role, params[0]);
  if (claim.status !== "completed") conflict("You can leave a review once the repairs are finished.");
  claim.review = { rating: body?.rating ?? 5, comment: body?.comment ?? null, submitted_at: NOW() };
  claim.status = "closed";
  claim.closed_at = NOW();
  return claimView(touch(claim, claimEvent(ID_SEQ++, "review_submitted", "Review submitted", 0)), role);
});

// requests
on("GET", "/requests/types", () => ({ items: REQUEST_TYPES }));
on("GET", "/requests", ({ role, query }) => {
  const scope = clientScope(role, query);
  const statuses = query.getAll("status");
  const list = REQUESTS.filter((r) => scope.includes(r.client.id))
    .filter((r) => (query.get("type") ? r.type === query.get("type") : true))
    .filter((r) => (statuses.length ? statuses.includes(r.status) : true))
    .filter((r) => (query.get("open") === "true" ? r.status === "submitted" || r.status === "in_progress" : true))
    .sort((a, b) => b.submitted_at.localeCompare(a.submitted_at))
    .map(listShape);
  return paginate(list, query);
});
on("GET", "/requests/:id", ({ role, params }) => REQUESTS.find((r) => r.id === params[0] && ownClientIds(role).includes(r.client.id)) ?? notFound("That request"));
on("POST", "/requests", ({ role, body }) => {
  requireRole(role, "client");
  const def = REQUEST_TYPES.find((t) => t.type === body?.type);
  if (!def) invalid("type", "Choose a request type.", "invalid");
  for (const f of def.fields) if (f.required && (body.payload?.[f.name] === undefined || body.payload?.[f.name] === null || body.payload?.[f.name] === "")) invalid(`payload.${f.name}`, `${f.label} is required.`);
  const req: ClientRequestDetail = {
    id: nextId(6), type: def.type, type_label: def.label, status: "submitted", client: { id: C1, full_name: CLIENTS[C1].full_name }, payload: body.payload ?? {}, client_note: body.client_note ?? null,
    adviser_response: null, requires_verification: def.requires_verification, attachments: [], submitted_at: NOW(), updated_at: NOW(), completed_at: null,
  };
  REQUESTS = [req, ...REQUESTS];
  return req;
});
on("PATCH", "/requests/:id", ({ role, params, body }) => {
  requireRole(role, "advisor");
  const req = REQUESTS.find((r) => r.id === params[0]) ?? notFound("That request");
  if (req.status === "completed" || req.status === "declined") conflict("This request is already finished.");
  if (body?.status === "declined" && !body?.adviser_response) invalid("adviser_response", "Explain why the request was declined.");
  if (body?.status) req.status = body.status;
  if (body && "adviser_response" in body) req.adviser_response = body.adviser_response;
  req.updated_at = NOW();
  if (req.status === "completed" || req.status === "declined") req.completed_at = NOW();
  return req;
});
on("POST", "/requests/:id/attachments", ({ role, params, body }) => {
  requireRole(role, "client");
  const req = REQUESTS.find((r) => r.id === params[0]) ?? notFound("That request");
  const form = body as FormData;
  const file = form instanceof FormData ? (form.get("file") as File | null) : null;
  if (!file) invalid("file", "Choose a file to upload.");
  const attachment: Attachment = { id: nextId(14), kind: (form.get("kind") as AttachmentKind) ?? "other", label: (form.get("label") as string) || null, filename: file.name, content_type: file.type, size_bytes: file.size, uploaded_by: C1, uploaded_at: NOW(), url: URL.createObjectURL(file), url_expires_at: hoursAgo(-1) };
  req.attachments = [...req.attachments, attachment];
  return attachment;
});

// documents, assistant, email (adviser only)
on("GET", "/documents", ({ role, query }) => {
  requireRole(role, "advisor");
  const search = (query.get("search") ?? "").toLowerCase();
  return paginate(DOCUMENTS.filter((d) => (query.get("category") ? d.category === query.get("category") : true)).filter((d) => !search || d.title.toLowerCase().includes(search)), query);
});
on("GET", "/documents/:id", ({ role, params }) => (requireRole(role, "advisor"), DOCUMENTS.find((d) => d.id === params[0]) ?? notFound("That document")));
on("GET", "/documents/:id/url", ({ role, params }) => {
  requireRole(role, "advisor");
  if (!DOCUMENTS.some((d) => d.id === params[0])) notFound("That document");
  return { url: "about:blank", expires_at: hoursAgo(-1), content_type: "application/pdf" };
});
on("POST", "/assistant/query", ({ role, body }) => {
  requireRole(role, "advisor");
  if (typeof body?.question !== "string" || body.question.trim().length < 3) invalid("question", "Ask a question of at least 3 characters.", "too_short");
  return assistantAnswer(body.question);
});
on("GET", "/email/status", ({ role }) => (requireRole(role, "advisor"), { provider: "mock", is_simulated: true, connected: true, account: ADVISER_REF.email }));
on("GET", "/email/threads", ({ role, query }) => {
  requireRole(role, "advisor");
  const search = (query.get("search") ?? "").toLowerCase();
  const list = THREADS.filter((t) => (query.get("client_id") ? t.link.client_id === query.get("client_id") : true))
    .filter((t) => (query.get("claim_id") ? t.link.claim_id === query.get("claim_id") : true))
    .filter((t) => (query.get("flagged") === "true" ? t.flags.length > 0 : true))
    .filter((t) => (query.get("unread") === "true" ? t.unread : true))
    .filter((t) => !search || t.subject.toLowerCase().includes(search) || t.snippet.toLowerCase().includes(search))
    .sort((a, b) => b.last_message_at.localeCompare(a.last_message_at));
  return paginate(list, query);
});
on("GET", "/email/threads/:id", ({ role, params }) => {
  requireRole(role, "advisor");
  const thread = THREADS.find((t) => t.id === params[0]) ?? notFound("That thread");
  return { thread, messages: MESSAGES[thread.id] ?? [] };
});
on("PUT", "/email/threads/:id/link", ({ role, params, body }) => {
  requireRole(role, "advisor");
  const thread = THREADS.find((t) => t.id === params[0]) ?? notFound("That thread");
  const claim = body?.claim_id ? CLAIMS.find((c) => c.id === body.claim_id) ?? notFound("That claim") : null;
  thread.link = { client_id: claim ? claim.client.id : body?.client_id ?? null, claim_id: claim?.id ?? null, linked_by: "manual" };
  return thread;
});
on("DELETE", "/email/threads/:id/link", ({ role, params }) => {
  requireRole(role, "advisor");
  const thread = THREADS.find((t) => t.id === params[0]) ?? notFound("That thread");
  thread.link = { client_id: null, claim_id: null, linked_by: null };
  return undefined;
});
on("POST", "/email/drafts/generate", ({ role, body }) => {
  requireRole(role, "advisor");
  const claim = CLAIMS.find((c) => c.id === body?.claim_id && c.status !== "draft") ?? notFound("That claim");
  return {
    draft: {
      to: claim.insurer_details.handler_email ? [{ name: claim.insurer_details.handler_name, email: claim.insurer_details.handler_email }] : [], cc: [],
      subject: `Motor claim ${claim.insurer_details.claim_number ?? claim.reference}: ${claim.client.full_name}`,
      body_text: `Dear ${claim.insurer_details.handler_name ?? "Claims team"},\n\nWe are following up on the motor claim for our client ${claim.client.full_name}.\n\nKind regards,\n${ADVISER_REF.full_name}`,
    },
    context_used: { claim_fields: ["incident.occurred_at", "incident.location_text"], thread_message_ids: [] },
    warnings: claim.insurer_details.claim_number ? [] : ["The insurer's claim number has not been recorded yet, so none is quoted."],
    requires_human_review: true, generated_by: { provider: "none", name: "mock" },
  };
});

// ---------------------------------------------------------------------------
// Entry point used by lib/api.ts
// ---------------------------------------------------------------------------
export async function mockRequest<T>(method: string, path: string, body?: unknown): Promise<T> {
  await new Promise((resolve) => setTimeout(resolve, 150));
  const [pathname, search = ""] = path.split("?");
  const query = new URLSearchParams(search);
  const role = currentRole();

  for (const [routeMethod, pattern, handler] of routes) {
    if (routeMethod !== method) continue;
    const match = pattern.exec(pathname);
    if (!match) continue;
    return structuredClone(handler({ params: match.slice(1), query, body, role })) as T;
  }
  throw new ApiError(404, { error: { code: "not_found", message: "This endpoint is not available in mock mode.", request_id: "mock" } });
}
