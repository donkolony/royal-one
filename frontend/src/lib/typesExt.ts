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
