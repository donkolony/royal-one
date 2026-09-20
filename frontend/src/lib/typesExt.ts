// Types for the Revenue & Compliance work (docs/api.md sections 5.15 to 5.20). The API is the source of truth.
import type { ISODate, ISODateTime, Page, UUID } from "./types";

export interface PersonName { id: UUID; full_name: string | null }

// ---- Opportunity Radar (5.16)
export type OpportunitySignal =
  | "under_insured_life" | "goal_behind" | "life_event" | "missing_cover" | "single_product" | "lapsed_cover" | "expiring_document";
export type OpportunityStatus = "open" | "snoozed" | "actioned" | "won" | "lost" | "expired";

export interface OpportunityEvent {
  id: UUID; kind: string; actor: PersonName | null; channel: string | null; note: string | null; created_at: ISODateTime;
}

export interface Opportunity {
  id: UUID;
  client: { id: UUID; full_name: string };
  adviser: { id: UUID; full_name: string };
  signal: OpportunitySignal; signal_label: string; title: string; why_now: string; suggested_action: string;
  talking_points: string[]; evidence: Record<string, unknown>; is_touchpoint: boolean;
  est_annual_premium_cents: number; est_annual_value_cents: number; value_formula: string; is_demo_estimate: true;
  status: OpportunityStatus; snoozed_until: ISODate | null; outcome_reason: string | null; won_value_cents: number | null;
  task_reminder_id: UUID | null; surfaced_at: ISODateTime; actioned_at: ISODateTime | null; closed_at: ISODateTime | null;
  events?: OpportunityEvent[];
}

export interface OpportunityBlock {
  surfaced: number; open: number; snoozed: number; actioned: number; won: number; lost: number; expired: number;
  open_value_cents: number; won_value_cents: number; conversion_rate: number | null;
}
export interface OpportunitySummary {
  totals: OpportunityBlock;
  by_signal: (OpportunityBlock & { signal: OpportunitySignal; label: string })[];
  by_adviser: (OpportunityBlock & { adviser: PersonName })[];
  definitions: Record<string, string>;
  assumptions: Assumptions;
}
export interface Assumptions { label: string; values: Record<string, unknown>; signals: Record<string, { label: string; how: string }> }

export interface OutreachDraft {
  channel: "email" | "whatsapp"; subject: string | null; body: string; source: "template" | "ai";
  requires_human_review: true; warnings: string[]; note: string;
}

// ---- Business Health (5.17)
export interface DrillRecord {
  client: { id: UUID; full_name: string }; adviser: PersonName; detail: string; value_cents: number | null;
  link: { path: string }; signal?: string; severity?: "high" | "medium"; kind?: string;
}
export interface DrillResult { metric: string; total: number; limit: number; offset: number; items: DrillRecord[]; value_cents: number; is_demo_estimate: boolean }

export interface TopAction { key: string; title: string; detail: string; tier: number; impact_cents: number; count: number; path: string }

export interface ComplianceGap {
  client: PersonName; kind: "identity" | "advice" | "consent"; state: string; label: string; severity: "high" | "medium"; fix_path: string;
}
export interface ComplianceSummary {
  score_percent: number | null; fully_compliant_clients: number; clients: number; definition: string;
  components: Record<"identity" | "advice" | "consent", { ok: number; total: number; percent: number | null }>;
  open_gaps?: number; gaps: ComplianceGap[];
}

export interface BusinessHealth {
  generated_at: ISODateTime; is_demo_estimate: true; label: string; clients: number;
  top_actions: TopAction[]; top_actions_rule: string;
  revenue_at_risk: {
    total_cents: number; premium_cents: number; clients: number; drilldown: string; formula: string;
    reasons: { key: string; label: string; how: string; count: number; value_cents: number; drilldown: string }[];
  };
  revenue_opportunity: {
    open_value_cents: number; open_count: number; drilldown: string; totals: OpportunityBlock; definitions: Record<string, string>;
    by_adviser: { adviser: PersonName; open: number; open_value_cents: number; won: number; lost: number; actioned: number; surfaced: number; conversion_rate: number | null }[];
    by_signal: { signal: OpportunitySignal; label: string; open: number; open_value_cents: number; won: number }[];
  };
  productivity: {
    window_days: number; label: string; clients_per_adviser: { adviser: PersonName; clients: number }[];
    avg_claim_handling_days: number | null; avg_claim_handling_basis: string; open_claims_avg_age_days: number | null; workflows_completed: number;
    admin_tasks_automated: { count: number; minutes_avoided: number; how: string; items: Record<string, { count: number; minutes_each: number; minutes: number }> };
    client_facing_share: { percent: number | null; client_facing_minutes: number; manual_admin_minutes: number; how: string };
  };
  retention: {
    not_contacted: { days: number; count: number; drilldown: string };
    reviews_overdue: { count: number; drilldown: string; rule: string };
    at_risk: { count: number; threshold: number; drilldown: string; formula: string };
  };
  products_per_client: { average: number | null; distribution: Record<string, number>; how: string };
  compliance: ComplianceSummary & { drilldown: string; open_gaps: number };
}

export interface HealthComponent { key: string; label: string; weight: number; value: number; points: number; detail: string }
export interface ClientHealth {
  score: number; band: "healthy" | "watch" | "at_risk"; components: HealthComponent[]; last_contact_at: ISODateTime | null;
  days_since_contact: number | null; weakest: string; formula: string; at_risk_below: number;
}

// ---- Audit (5.15)
export interface AuditEntry {
  id: number; occurred_at: ISODateTime; actor: { id: UUID | null; full_name: string | null; role: string };
  action: string; entity_type: string; entity_id: string | null; client: { id: UUID; full_name: string } | null;
  summary: string; details: Record<string, unknown>; ip: string | null; user_agent: string | null; request_id: string | null; hash: string;
}
export type AuditPage = Page<AuditEntry>;

// ---- Workflows, requests and notifications (5.18)
export interface RequestField {
  name: string; label: string; type: string; required?: boolean; max_length?: number; pattern?: string; options?: string[];
  min?: number; max?: number; ref?: string; min_items?: number; max_items?: number; item_fields?: RequestField[]; not_before?: string; not_in_past?: boolean;
}
export interface WorkflowStep { key: string; label: string }
export interface WorkflowDoc { kind: string; label: string; required: boolean; reuse_from_vault: string | null }
export interface RequestTypeDef {
  type: string; label: string; description: string; requires_verification: boolean; requires_identity: boolean; insurer_forward: boolean;
  sla_days: number; max_attachments: number; fields: RequestField[]; steps: WorkflowStep[]; documents: WorkflowDoc[];
}
export interface TimelineEvent {
  id: UUID; type: string; title: string; message: string | null; visible_to_client: boolean; from_status: string | null; to_status: string | null;
  created_at: ISODateTime; actor: { id: UUID; full_name: string | null; role: string } | null;
}
export type RequestState = "submitted" | "in_progress" | "completed" | "declined";
export interface RequestItem {
  id: UUID; type: string; type_label: string; status: RequestState; client: { id: UUID; full_name: string }; payload: Record<string, unknown>;
  client_note: string | null; adviser_response: string | null; insurer_forward: boolean; requires_verification: boolean;
  submitted_at: ISODateTime; updated_at: ISODateTime; completed_at: ISODateTime | null; timeline?: TimelineEvent[];
}
export interface AppNotification {
  id: UUID; kind: string; title: string; body: string | null; link: { resource: string; id: UUID } | null; client_id: UUID | null;
  created_at: ISODateTime; read_at: ISODateTime | null;
}
export interface NotificationList { items: AppNotification[]; unread_count: number }

// ---- Identity vault (5.19)
export type IdentityDocType = "id_document" | "drivers_licence" | "proof_of_address";
export type IdentityState = "valid" | "expiring" | "expired" | "pending" | "stale" | "missing";
export interface IdentityDocument {
  id: UUID; client_id: UUID; doc_type: IdentityDocType; label: string; filename: string; content_type: string; size_bytes: number;
  status: "pending" | "verified" | "rejected" | "superseded"; verification_source: "uploaded" | "simulated_verification" | null; verifier: string | null;
  verified_by: PersonName | null; verified_at: ISODateTime | null; issued_date: ISODate | null; expiry_date: ISODate | null;
  rejected_reason: string | null; uploaded_at: ISODateTime; reuse_count: number; is_simulated_verification: boolean;
}
export interface IdentityVault {
  client_id: UUID; documents: IdentityDocument[];
  summary: Record<IdentityDocType, { state: IdentityState; document_id: UUID | null; expiry_date: ISODate | null; verified_at: ISODateTime | null }>;
  reuse_log: { id: UUID; doc_type: IdentityDocType; label: string; used_for: string; used_for_id: UUID | null; used_at: ISODateTime; used_by: string | null }[];
  verifier: { name: string; is_simulated: boolean; note: string };
  rules: { proof_of_address_max_age_days: number; expiry_warning_days: number };
}

// ---- Compliance (5.20)
export interface AdviceRecord {
  id: UUID; client: { id: UUID; full_name: string | null }; adviser: { id: UUID; full_name: string | null }; interaction_type: string;
  needs_goals: string[]; products_considered: { product: string; category: string; provider?: string | null }[]; recommendation: string;
  ai_draft: string | null; draft_source: "template" | "ai" | null; final_summary: string; edited_from_draft: boolean; client_acknowledged: boolean;
  acknowledged_at: ISODateTime | null; acknowledgement_method: string | null; approved_by: UUID; approved_at: ISODateTime; created_at: ISODateTime;
}
export interface AdviceDraft { draft: { summary: string; source: "template" | "ai" }; warnings: string[]; requires_human_review: true; note: string }
export type ConsentPurpose = "data_processing" | "marketing" | "insurer_sharing";
export interface ConsentState {
  client_id: UUID; notice_version: string; notice_is_draft: boolean; purposes: Record<ConsentPurpose, string>;
  current: Record<ConsentPurpose, { status: "granted" | "withdrawn"; method: string; notice_version: string; recorded_at: ISODateTime } | null>;
  history: { id: UUID; purpose: ConsentPurpose; status: string; method: string; notice_version: string; recorded_at: ISODateTime; recorded_by: string | null }[];
}
export interface CompliancePack {
  reference: string; generated_at: ISODateTime; generated_by: { id: UUID; full_name: string; role: string }; generation_ms: number; content_sha256: string;
  client: { id: UUID; full_name: string; adviser: { id: UUID; full_name: string } };
  compliance_status: Record<"identity" | "advice" | "consent", { state: string; ok: boolean }>;
  advice_records: AdviceRecord[]; claims: unknown[]; requests: unknown[]; access_history: AuditEntry[];
  integrity: { audit_chain_ok: boolean; audit_entries_checked: number; note: string }; excluded_for_data_minimisation: string[];
}
export interface TimelineItem { id: number; occurred_at: ISODateTime; actor: { id: UUID | null; full_name: string | null; role: string }; action: string; summary: string; entity_type: string; entity_id: string | null }
export interface ComplianceOverview {
  summary: ComplianceSummary & { gaps: ComplianceGap[] };
  clients: { id: UUID; full_name: string; adviser: string; identity: string; advice: string; consent: string }[];
}
export interface RetentionReview {
  retention_years: number; cutoff_date: ISODate; total: number; action: "flag_only"; note: string;
  items: { kind: string; label: string; client: { id: UUID; full_name: string }; date: ISODateTime; entity_id: UUID }[];
}
