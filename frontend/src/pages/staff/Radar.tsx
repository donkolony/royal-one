import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader, StatTile, DemoBadge, InfoPopover, Skeleton, ErrorBanner, EmptyState } from "../../components/ui";
import { OpportunityCard } from "../../components/staff/OpportunityCard";
import { useGet } from "../../lib/hooks";
import { useIsOwner, useStaffBase } from "../../lib/staff";
import { formatRand0, itemsOf } from "../../lib/utils";
import type { Page } from "../../lib/types";
import type { Opportunity, OpportunitySummary } from "../../lib/typesExt";

const STATUSES: [string, string][] = [["live", "Live"], ["snoozed", "Snoozed"], ["won", "Won"], ["lost", "Lost"], ["expired", "Expired"], ["all", "All"]];

/**
 * The Opportunity Radar: rules on client data, ranked by estimated annual value, each card showing the evidence that
 * triggered it. Advisers act on their own clients' cards; the owner sees everything, read-only.
 */
export default function Radar() {
  const base = useStaffBase();
  const owner = useIsOwner();
  const [params, setParams] = useSearchParams();
  const client = params.get("client") ?? "";
  const [signal, setSignal] = useState("");
  const [status, setStatus] = useState("live");
  const [shown, setShown] = useState(10);

  const qs = `limit=100&status=${status}${signal ? `&signal=${signal}` : ""}${client ? `&client_id=${client}` : ""}`;
  const list = useGet<Page<Opportunity>>(["opportunities", status, signal, client], `/opportunities?${qs}`, { refetchMs: 15000 });
  const summary = useGet<OpportunitySummary>(["opp-summary"], "/opportunities/summary", { refetchMs: 15000 });
  const items = itemsOf(list.data);
  const t = summary.data?.totals;

  return (
    <div>
      <PageHeader
        title="Opportunities"
        badge={<DemoBadge />}
        subtitle={owner
          ? "Every adviser's open opportunities, found by rules on the client data. You see them read-only; advisers act on them."
          : "Clients worth a conversation today, found by rules on your clients' data and ranked by estimated annual value."}
      />

      {summary.isLoading ? <Skeleton className="h-24 w-full" /> : t && (
        <section aria-label="Radar summary" className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <StatTile label="Open value" value={formatRand0(t.open_value_cents)} sub={`${t.open + t.actioned} live opportunities`} tone="brand" />
          <StatTile label="Surfaced" value={t.surfaced} sub="ever detected" />
          <StatTile label="Actioned" value={t.actioned} sub="task made or outreach logged" />
          <StatTile label="Won / lost" value={`${t.won} / ${t.lost}`} sub={t.conversion_rate === null ? "no outcomes yet" : `${Math.round(t.conversion_rate * 100)}% conversion`} tone="success" />
        </section>
      )}
      {summary.data && (
        <div className="mb-4">
          <InfoPopover label="How is this calculated? Definitions and assumptions">
            <ul className="space-y-1">
              {Object.entries(summary.data.definitions).map(([k, v]) => <li key={k}><span className="font-semibold capitalize">{k}:</span> {v}</li>)}
            </ul>
            <p className="mt-2 font-semibold">{summary.data.assumptions.label}</p>
            <ul className="mt-1 grid sm:grid-cols-2 gap-x-6">
              {Object.entries(summary.data.assumptions.values).filter(([, v]) => typeof v !== "object").map(([k, v]) => <li key={k}><span className="text-charcoal-500">{k.replace(/_/g, " ")}:</span> {String(v)}</li>)}
            </ul>
          </InfoPopover>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 mb-4" role="group" aria-label="Filter by signal">
        <FilterChip active={!signal} onClick={() => setSignal("")}>All signals</FilterChip>
        {summary.data?.by_signal.filter((s) => s.surfaced > 0).map((s) => (
          <FilterChip key={s.signal} active={signal === s.signal} onClick={() => setSignal(signal === s.signal ? "" : s.signal)}>{s.label} ({s.open + s.actioned + s.snoozed})</FilterChip>
        ))}
        <span className="grow" />
        <label className="text-sm text-charcoal-600 dark:text-charcoal-300">
          <span className="sr-only">Status</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="h-9 rounded-md border-charcoal-300 py-0 text-sm dark:bg-charcoal-900 dark:border-charcoal-600">
            {STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        {client && <button className="text-sm text-brand-600 hover:underline" onClick={() => setParams({})}>Show all clients</button>}
      </div>

      {list.isLoading && <div className="space-y-3"><Skeleton className="h-40 w-full" /><Skeleton className="h-40 w-full" /></div>}
      {list.error ? <ErrorBanner error={list.error} onRetry={() => void list.refetch()} /> : null}
      {!list.isLoading && !list.error && items.length === 0 && (
        <EmptyState title="Nothing to chase here" description={status === "live" ? "No live opportunities match. The rules re-run every time this page loads." : "No opportunities with this status."} />
      )}
      <div className="space-y-3" aria-live="polite">
        {items.slice(0, shown).map((o) => <OpportunityCard key={o.id} opportunity={o} base={base} canAct={!owner} />)}
      </div>
      {items.length > shown && (
        <div className="mt-4 text-center">
          <button type="button" onClick={() => setShown((n) => n + 10)} className="rounded-md border border-charcoal-300 dark:border-charcoal-600 px-4 py-2 text-sm font-medium hover:bg-charcoal-100 dark:hover:bg-charcoal-700">
            Show more ({items.length - shown} more, lower value first)
          </button>
        </div>
      )}
    </div>
  );
}

function FilterChip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`rounded-full border px-3 py-1 text-sm transition-colors ${active ? "border-brand-500 bg-brand-500 text-white" : "border-charcoal-300 dark:border-charcoal-600 text-charcoal-700 dark:text-charcoal-200 hover:bg-charcoal-100 dark:hover:bg-charcoal-700"}`}
    >
      {children}
    </button>
  );
}
