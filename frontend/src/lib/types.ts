export type UUID = string;
export type ISODate = string;
export type ISODateTime = string;
export type Role = 'client' | 'advisor';

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface FieldError {
  field: string;
  code: string;
  message: string;
}

export interface ApiErrorType {
  code: string;
  message: string;
  details?: FieldError[];
  request_id: string;
  retry_after_seconds?: number | null;
}

export interface ApiErrorResponse {
  error: ApiErrorType;
}

export interface PersonRef {
  id: UUID;
  full_name: string;
  email: string;
  phone: string | null;
}

export interface ClientProfile {
  id: UUID;
  adviser: PersonRef | null;
  date_of_birth: ISODate | null;
  drivers_licence_expiry: ISODate | null;
  client_since: ISODate | null;
  last_annual_review_date: ISODate | null;
}

export interface Profile {
  id: UUID;
  email: string;
  full_name: string;
  role: Role;
  phone: string | null;
  created_at: ISODateTime;
  client: ClientProfile | null;
  advisor: { id: UUID } | null;
}

export interface ClientSummary {
  id: UUID;
  full_name: string;
  email: string;
  phone: string | null;
}

export interface ClientDetail extends ClientSummary {
  date_of_birth: ISODate | null;
  drivers_licence_expiry: ISODate | null;
  client_since: ISODate | null;
  last_annual_review_date: ISODate | null;
  counts: {
    policies: number;
    open_claims: number;
    active_goals: number;
    pending_requests: number;
    pending_reminders: number;
  };
  created_at: ISODateTime;
}

export interface Insurer {
  id: UUID;
  name: string;
}

export type PolicyCategory = 'motor' | 'life' | 'health' | 'funeral' | 'personal_other' | 'commercial' | 'investment' | 'retirement';
export type PolicyStatus = 'active' | 'pending' | 'lapsed' | 'cancelled';

export interface Policy {
  id: UUID;
  client_id: UUID;
  insurer: Insurer;
  category: PolicyCategory;
  product_name: string;
  policy_number: string;
  status: PolicyStatus;
  asset_description: string | null;
  cover_amount_cents: number | null;
  current_value_cents: number | null;
  premium_cents: number | null;
  premium_frequency: 'monthly' | 'annual' | null;
  start_date: ISODate | null;
  renewal_date: ISODate | null;
  valuation_certificate_date: ISODate | null;
}

export type FinancialItemKind = 'asset' | 'liability';
export type FinancialItemCategory =
  | 'property' | 'vehicle' | 'cash' | 'investments' | 'retirement' | 'business' | 'other_asset'
  | 'home_loan' | 'vehicle_finance' | 'credit_card' | 'personal_loan' | 'other_liability';

export interface FinancialItem {
  id: UUID;
  client_id: UUID;
  kind: FinancialItemKind;
  category: FinancialItemCategory;
  label: string;
  amount_cents: number;
  as_of_date: ISODate;
  updated_at: ISODateTime;
}

export interface NetWorth {
  currency: 'ZAR';
  total_assets_cents: number;
  total_liabilities_cents: number;
  net_worth_cents: number;
  as_of: ISODate;
  breakdown: {
    kind: FinancialItemKind;
    category: FinancialItemCategory;
    source: 'balance_sheet' | 'policy';
    total_cents: number;
  }[];
}

export type GoalCategory = 'retirement' | 'education' | 'property' | 'emergency_fund' | 'travel' | 'debt_repayment' | 'other';
export type GoalStatus = 'active' | 'achieved' | 'archived';
export type GoalType = 'individual' | 'shared';

export interface Goal {
  id: UUID;
  title: string;
  description: string | null;
  category: GoalCategory;
  type: GoalType;
  status: GoalStatus;
  target_amount_cents: number;
  current_amount_cents: number;
  progress_percent: number;
  target_date: ISODate | null;
  participants: { client_id: UUID; full_name: string }[];
  created_by: UUID;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export type ReminderType = 'valuation_certificate' | 'licence_expiry' | 'annual_review' | 'retirement_fee_renewal' | 'birthday' | 'anniversary' | 'claim_police_report' | 'custom' | string;
export type ReminderStatus = 'pending' | 'done' | 'dismissed';
export type ReminderUrgency = 'overdue' | 'due_soon' | 'upcoming';

export interface Reminder {
  id: UUID;
  type: ReminderType;
  title: string;
  description: string | null;
  due_date: ISODate;
  audience: 'client' | 'advisor' | 'both';
  status: ReminderStatus;
  urgency: ReminderUrgency;
  source: 'rule' | 'manual';
  client: { id: UUID; full_name: string };
  related: { resource: 'policy' | 'claim' | 'client'; id: UUID } | null;
  completed_at: ISODateTime | null;
  created_at: ISODateTime;
}

export interface Witness {
  name: string;
  phone: string | null;
  email: string | null;
  statement: string | null;
}

export interface ThirdParty {
  name: string;
  phone: string | null;
  drivers_licence_number: string | null;
  vehicle_registration: string | null;
  vehicle_make_model: string | null;
  insurer_name: string | null;
  policy_number: string | null;
}

export type AttachmentKind = 'road_photo' | 'vehicle_photo' | 'people_photo' | 'plate_or_disc_photo' | 'id_document' | 'witness_voice_note' | 'drivers_licence' | 'accident_sketch' | 'other';

export interface Attachment {
  id: UUID;
  kind: AttachmentKind;
  label: string | null;
  filename: string;
  content_type: string;
  size_bytes: number;
  uploaded_by: UUID;
  uploaded_at: ISODateTime;
  url: string;
  url_expires_at: ISODateTime;
}

export type ClaimStatus = 'draft' | 'submitted' | 'registered' | 'assessment' | 'quotes' | 'authorised' | 'in_repair' | 'completed' | 'closed';
export type HireCarStatus = 'not_required' | 'requested' | 'arranged' | 'delivered' | 'return_arranged' | 'returned';

export interface ClaimEvent {
  id: UUID;
  type: 'created' | 'submitted' | 'status_changed' | 'insurer_details_updated' | 'note' | 'repair_update' | 'hire_car_updated' | 'repair_date_chosen' | 'attachment_added' | 'review_submitted';
  title: string;
  message: string | null;
  visible_to_client: boolean;
  from_status: ClaimStatus | null;
  to_status: ClaimStatus | null;
  actor: { id: UUID; full_name: string; role: Role } | null;
  created_at: ISODateTime;
}

export interface AllowedTransition {
  to_status: ClaimStatus;
  direction: 'forward' | 'back';
  label: string;
  requires: string[];
  actor: Role;
}

export interface ClaimSummary {
  id: UUID;
  reference: string | null;
  client: { id: UUID; full_name: string };
  insurer: Insurer | null;
  status: ClaimStatus;
  status_label: string;
  claim_number: string | null;
  incident_occurred_at: ISODateTime | null;
  incident_location_text: string | null;
  hire_car_status: HireCarStatus;
  days_in_status: number;
  submitted_at: ISODateTime | null;
  updated_at: ISODateTime;
}

export interface Claim extends ClaimSummary {
  policy_id: UUID | null;
  incident: {
    occurred_at: ISODateTime | null;
    location_text: string | null;
    location_lat: number | null;
    location_lng: number | null;
    description: string | null;
  };
  police: {
    reported: boolean | null;
    case_number: string | null;
    station: string | null;
    reported_at: ISODateTime | null;
    report_deadline_at: ISODateTime | null;
    deadline_status: 'not_applicable' | 'pending' | 'overdue' | 'met';
  };
  driver: {
    is_policyholder: boolean | null;
    full_name: string | null;
    relationship_to_policyholder: string | null;
  };
  vehicle_use: 'personal' | 'business' | null;
  witnesses: Witness[];
  third_parties: ThirdParty[];
  insurer_details: {
    claim_number: string | null;
    handler_name: string | null;
    handler_email: string | null;
    handler_phone: string | null;
  };
  repair: {
    repairer_name: string | null;
    repairer_phone: string | null;
    quote_amount_cents: number | null;
    authorised_amount_cents: number | null;
    drop_off_date: ISODate | null;
    estimated_completion_date: ISODate | null;
    completed_at: ISODateTime | null;
  };
  hire_car: {
    status: HireCarStatus;
    provider: string | null;
    delivery_date: ISODate | null;
    return_date: ISODate | null;
  };
  review: {
    rating: 1 | 2 | 3 | 4 | 5;
    comment: string | null;
    submitted_at: ISODateTime;
  } | null;
  missing_fields: string[];
  allowed_transitions: AllowedTransition[];
  attachments: Attachment[];
  timeline: ClaimEvent[];
  created_at: ISODateTime;
  closed_at: ISODateTime | null;
}

export type RequestType = 'address_change' | 'bank_details_change' | 'policy_document' | 'border_letter' | 'irp5' | 'consultation' | 'client_information';
export type RequestStatus = 'submitted' | 'in_progress' | 'completed' | 'declined';

export interface RequestTypeDefinition {
  type: RequestType;
  label: string;
  requires_verification: boolean;
  max_attachments: number;
  fields: {
    name: string;
    label: string;
    type: string;
    required: boolean;
    max_length?: number;
    pattern?: string;
    options?: string[];
  }[];
}

export interface ClientRequest {
  id: UUID;
  type: RequestType;
  type_label: string;
  status: RequestStatus;
  client: { id: UUID; full_name: string };
  payload: Record<string, unknown>;
  client_note: string | null;
  adviser_response: string | null;
  requires_verification: boolean;
  attachments: Attachment[];
  submitted_at: ISODateTime;
  updated_at: ISODateTime;
  completed_at: ISODateTime | null;
}

export type DocumentCategory = 'policy_wording' | 'internal_process' | 'company_policy' | 'regulation';
export type DocumentStatus = 'indexed' | 'processing' | 'failed';

export interface DocumentRecord {
  id: UUID;
  title: string;
  category: DocumentCategory;
  insurer: Insurer | null;
  page_count: number;
  version_label: string | null;
  is_synthetic: boolean;
  source_note: string | null;
  status: DocumentStatus;
  indexed_at: ISODateTime | null;
}

export interface Citation {
  index: number;
  document_id: UUID;
  document_title: string;
  category: DocumentCategory;
  is_synthetic: boolean;
  page: number;
  quote: string;
}

export interface AssistantAnswer {
  conversation_id: UUID;
  message_id: UUID;
  answer: string;
  grounded: boolean;
  citations: Citation[];
  model: { provider: 'groq' | 'gemini'; name: string };
  latency_ms: number;
}

export type EmailFlagCode = 'insurer_sender' | 'client_sender' | 'claim_reference_match' | 'deadline_keyword';

export interface EmailParticipant {
  name: string | null;
  email: string;
  role: 'client' | 'insurer' | 'other';
}

export interface EmailThread {
  id: UUID;
  subject: string;
  snippet: string;
  participants: EmailParticipant[];
  message_count: number;
  last_message_at: ISODateTime;
  unread: boolean;
  importance: 'high' | 'normal';
  flags: { code: EmailFlagCode; label: string }[];
  link: { client_id: UUID | null; claim_id: UUID | null; linked_by: 'auto' | 'manual' | null };
  is_simulated: boolean;
}

export interface EmailMessage {
  id: UUID;
  from: EmailParticipant;
  to: EmailParticipant[];
  cc: EmailParticipant[];
  sent_at: ISODateTime;
  body_text: string;
  has_attachments: boolean;
}

export interface NeedsAttentionItem {
  kind: 'claim' | 'request' | 'reminder' | 'email';
  id: UUID;
  title: string;
  subtitle: string;
  client: { id: UUID; full_name: string };
  due_at: ISODateTime | null;
  link: { resource: string; id: UUID };
}

export interface ClientDashboard {
  generated_at: ISODateTime;
  client: ClientSummary;
  adviser: PersonRef | null;
  net_worth: NetWorth;
  policies: { count: number; items: Policy[] };
  open_claims: { count: number; items: ClaimSummary[] };
  goals: { items: Goal[] };
  reminders: { overdue_count: number; upcoming: Reminder[] };
  pending_requests: { count: number; items: ClientRequest[] };
}

export interface AdvisorDashboard {
  generated_at: ISODateTime;
  counts: {
    clients: number;
    open_claims: number;
    pending_requests: number;
    reminders_due_7d: number;
    overdue_reminders: number;
  };
  claims_by_status: { status: ClaimStatus; label: string; count: number }[];
  needs_attention: NeedsAttentionItem[];
  upcoming_reminders: Reminder[];
}

export interface ClaimChecklistItem {
  id: string;
  order: number;
  title: string;
  description: string;
  upload_kind: AttachmentKind | null;
}
