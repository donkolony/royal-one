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

export type RequestFieldType =
  | 'string' | 'text' | 'date' | 'integer' | 'boolean' | 'enum' | 'uuid'
  | 'string_list' | 'date_list' | 'object_list';

/** One payload field of a request type (GET /requests/types). Constraint keys are only present when they apply. */
export interface RequestFieldDefinition {
  name: string;
  label: string;
  type: RequestFieldType;
  required: boolean;
  max_length?: number;
  pattern?: string;
  options?: string[];
  min?: number;
  max?: number;
  min_items?: number;
  max_items?: number;
  /** Name of another date field this date may not precede (e.g. travel_to not before travel_from). */
  not_before?: string;
  not_in_past?: boolean;
  /** uuid fields: the id must be one of the client's policies ('motor_policy' = motor policies only). */
  ref?: 'policy' | 'motor_policy';
  /** object_list fields: the fields of each list item. */
  item_fields?: RequestFieldDefinition[];
}

export interface RequestTypeDefinition {
  type: RequestType;
  label: string;
  requires_verification: boolean;
  max_attachments: number;
  fields: RequestFieldDefinition[];
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
  submitted_at: ISODateTime;
  updated_at: ISODateTime;
  completed_at: ISODateTime | null;
}

/** GET /requests/{id} and the POST /requests response: a ClientRequest plus its attachments. List endpoints and dashboards do NOT include `attachments`. */
export interface ClientRequestDetail extends ClientRequest {
  attachments: Attachment[];
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
  /** provider is 'none' when no LLM is configured and the question had no relevant passage. */
  model: { provider: 'groq' | 'gemini' | 'none'; name: string };
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
  /** NOT a route: turn it into one with advisorLinkFor() from lib/utils. */
  link: { resource: 'claim' | 'request' | 'reminder' | 'email_thread'; id: UUID };
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

// ---------------------------------------------------------------------------
// Small static lists: { items } only, no paging fields (insurers, checklist, request types)
// ---------------------------------------------------------------------------
export interface Items<T> {
  items: T[];
}

// ---------------------------------------------------------------------------
// Reference data: GET /meta (no login needed, cache it; see lib/meta.ts -> useMeta())
// ---------------------------------------------------------------------------
export interface ClaimStatusMeta {
  value: ClaimStatus;
  order: number;
  /** Plain, reassuring wording for the client app. */
  client_label: string;
  /** Efficient wording for the adviser portal. */
  advisor_label: string;
}

export interface ReminderTypeMeta {
  type: ReminderType;
  label: string;
  default_audience: 'client' | 'advisor' | 'both';
  /** null for 'custom' reminders. */
  lead_days: number | null;
}

export interface RequestTypeMeta {
  type: RequestType;
  label: string;
  requires_verification: boolean;
}

export type AttachmentContentGroup = 'image' | 'document' | 'audio';

export interface AttachmentRules {
  max_bytes: number;
  max_per_claim: number;
  max_per_request: number;
  content_types: Record<AttachmentContentGroup, string[]>;
  kinds: { kind: AttachmentKind; accepts: AttachmentContentGroup[] }[];
}

export interface Meta {
  api_version: string;
  currency: 'ZAR';
  claim_statuses: ClaimStatusMeta[];
  hire_car_statuses: HireCarStatus[];
  reminder_types: ReminderTypeMeta[];
  request_types: RequestTypeMeta[];
  policy_categories: PolicyCategory[];
  policy_statuses: PolicyStatus[];
  financial_item_categories: Record<FinancialItemKind, FinancialItemCategory[]>;
  goal_categories: GoalCategory[];
  document_categories: DocumentCategory[];
  attachment_rules: AttachmentRules;
}

// ---------------------------------------------------------------------------
// Response wrappers that are not Page<T>
// ---------------------------------------------------------------------------
/** GET /claims/pipeline (adviser). Columns always come in status order, even when empty. */
export interface ClaimsPipelineColumn {
  status: ClaimStatus;
  label: string;
  count: number;
  /** Max 50, oldest submission first. */
  claims: ClaimSummary[];
}

export interface ClaimsPipeline {
  columns: ClaimsPipelineColumn[];
}

/** POST /reminders/run-check */
export interface ReminderRunCheckResult {
  evaluated_clients: number;
  created: number;
  already_existing: number;
}

/** GET /documents/{id}/url. Append `#page=<n>` to open at a citation's page. */
export interface DocumentUrl {
  url: string;
  expires_at: ISODateTime;
  content_type: string;
}

// ---------------------------------------------------------------------------
// Assistant (adviser)
// ---------------------------------------------------------------------------
export interface AssistantFilters {
  category?: DocumentCategory[];
  insurer_id?: UUID | null;
  document_ids?: UUID[];
}

export interface AssistantQuery {
  /** 3 to 1000 chars. */
  question: string;
  /** null starts a new conversation. */
  conversation_id?: UUID | null;
  filters?: AssistantFilters;
}

export interface AssistantConversationSummary {
  id: UUID;
  title: string;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  message_count: number;
}

export interface AssistantMessage {
  id: UUID;
  role: 'user' | 'assistant';
  content: string;
  grounded: boolean | null;
  citations: Citation[];
  created_at: ISODateTime;
}

export interface AssistantConversation {
  id: UUID;
  title: string;
  messages: AssistantMessage[];
}

// ---------------------------------------------------------------------------
// Email (adviser, simulated in the hackathon build)
// ---------------------------------------------------------------------------
export interface EmailStatus {
  provider: 'mock' | 'gmail';
  is_simulated: boolean;
  connected: boolean;
  account: string | null;
}

/** GET /email/threads/{id}. Message body_text is UNTRUSTED: render as plain text. */
export interface EmailThreadDetail {
  thread: EmailThread;
  /** Oldest first. */
  messages: EmailMessage[];
}

export type EmailDraftPurpose = 'initial_notification' | 'follow_up' | 'reply' | 'status_query';

export interface EmailDraftRequest {
  claim_id: UUID;
  /** Required when purpose = 'reply'. */
  thread_id?: UUID | null;
  purpose: EmailDraftPurpose;
  /** Max 500 chars. */
  instructions?: string | null;
}

export interface EmailDraftRecipient {
  name: string | null;
  email: string;
}

export interface EmailDraft {
  to: EmailDraftRecipient[];
  cc: EmailDraftRecipient[];
  subject: string;
  body_text: string;
}

export interface EmailDraftResponse {
  draft: EmailDraft;
  context_used: { claim_fields: string[]; thread_message_ids: UUID[] };
  /** Facts that were missing and were left out instead of guessed. */
  warnings: string[];
  /** Always true. */
  requires_human_review: boolean;
  generated_by: { provider: string; name: string };
}

export interface EmailLinkRequest {
  claim_id?: UUID | null;
  client_id?: UUID | null;
}

// ---------------------------------------------------------------------------
// Request bodies (only documented fields; unknown fields are rejected with 422)
// ---------------------------------------------------------------------------
export interface ProfilePatch {
  phone?: string | null;
  /** Clients only. */
  drivers_licence_expiry?: ISODate | null;
}

export interface ClientPatch {
  full_name?: string;
  phone?: string | null;
  date_of_birth?: ISODate | null;
  drivers_licence_expiry?: ISODate | null;
  client_since?: ISODate | null;
  last_annual_review_date?: ISODate | null;
}

export interface ClaimCreate {
  policy_id?: UUID | null;
  insurer_id?: UUID | null;
}

/** PATCH /claims/{id} (client, draft only). incident/police/driver merge one level deep; witnesses/third_parties are replaced whole. */
export interface ClaimPatch {
  insurer_id?: UUID | null;
  incident?: {
    occurred_at?: ISODateTime | null;
    location_text?: string | null;
    location_lat?: number | null;
    location_lng?: number | null;
    description?: string | null;
  };
  police?: {
    reported?: boolean | null;
    case_number?: string | null;
    station?: string | null;
    reported_at?: ISODateTime | null;
  };
  driver?: {
    is_policyholder?: boolean | null;
    full_name?: string | null;
    relationship_to_policyholder?: string | null;
  };
  vehicle_use?: 'personal' | 'business' | null;
  witnesses?: Witness[];
  third_parties?: ThirdParty[];
}

export interface InsurerDetailsPatch {
  claim_number?: string | null;
  handler_name?: string | null;
  handler_email?: string | null;
  handler_phone?: string | null;
}

export interface ClaimTransitionRequest {
  to_status: ClaimStatus;
  /** Max 1000 chars. */
  note?: string | null;
  /** Defaults to true. */
  visible_to_client?: boolean;
}

export interface RepairDetailsPatch {
  repairer_name?: string | null;
  repairer_phone?: string | null;
  quote_amount_cents?: number | null;
  authorised_amount_cents?: number | null;
  estimated_completion_date?: ISODate | null;
  completed_at?: ISODateTime | null;
}

export interface RepairDateRequest {
  /** Today or later. */
  drop_off_date: ISODate;
}

export interface HireCarPatch {
  status?: HireCarStatus;
  provider?: string | null;
  delivery_date?: ISODate | null;
  return_date?: ISODate | null;
}

export interface ClaimUpdateRequest {
  type: 'note' | 'repair_update';
  /** 1 to 2000 chars. */
  message: string;
  visible_to_client?: boolean;
}

export interface ClaimReviewRequest {
  rating: 1 | 2 | 3 | 4 | 5;
  /** Max 1000 chars. */
  comment?: string | null;
}

export interface RequestCreate {
  type: RequestType;
  payload: Record<string, unknown>;
  /** Max 1000 chars. */
  client_note?: string | null;
}

export interface RequestPatch {
  status?: 'in_progress' | 'completed' | 'declined';
  /** Required when declining. Max 2000 chars. */
  adviser_response?: string | null;
}

export interface GoalCreate {
  /** 1 to 5 distinct assigned clients. */
  client_ids: UUID[];
  title: string;
  description?: string | null;
  category: GoalCategory;
  target_amount_cents: number;
  current_amount_cents?: number;
  target_date?: ISODate | null;
}

export interface GoalPatch {
  title?: string;
  description?: string | null;
  category?: GoalCategory;
  target_amount_cents?: number;
  current_amount_cents?: number;
  target_date?: ISODate | null;
  status?: 'active' | 'archived';
  client_ids?: UUID[];
}

export interface ReminderCreate {
  client_id: UUID;
  type: ReminderType;
  title: string;
  description?: string | null;
  due_date: ISODate;
  audience: 'client' | 'advisor' | 'both';
}

export interface ReminderPatch {
  title?: string;
  description?: string | null;
  due_date?: ISODate;
  audience?: 'client' | 'advisor' | 'both';
  status?: 'pending' | 'dismissed';
}

export interface FinancialItemCreate {
  client_id: UUID;
  kind: FinancialItemKind;
  category: FinancialItemCategory;
  label: string;
  /** Integer cents, greater than 0. */
  amount_cents: number;
  as_of_date: ISODate;
}
