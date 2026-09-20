import React, { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Badge, Button, Card, EmptyState, ErrorBanner, InfoPopover, Skeleton, StatusPill, Bar } from "@/components/ui";
import { OpportunityCard } from "@/components/staff/OpportunityCard";
import { IdentityTab } from "@/components/client360/IdentityTab";
import { ComplianceTab } from "@/components/client360/ComplianceTab";
import { AddGoalModal, AddItemModal, AddReminderModal, NeedsForm } from "@/components/client360/SimpleForms";
import { api } from "@/lib/api";
import { useAct, useGet } from "@/lib/hooks";
import { useMeta } from "@/lib/meta";
import { useIsOwner, useStaffBase } from "@/lib/staff";
import { formatDate, formatDateTime, formatRand0, formatZAR, humanize, itemsOf } from "@/lib/utils";
import type { ClientDashboard, ClientDetail, FinancialItem, Goal, Page, Reminder } from "@/lib/types";
import type { ClientHealth, Opportunity, TimelineItem } from "@/lib/typesExt";

const TABS = [["overview", "Overview"], ["opportunities", "Opportunities"], ["goals", "Goals"], ["financial", "Financial items"], ["reminders", "Reminders"], ["identity", "Identity"], ["compliance", "Compliance"], ["timeline", "Timeline"]] as const;
type Tab = (typeof TABS)[number][0];
const BAND: Record<string, "success" | "warning" | "danger"> = { healthy: "success", watch: "warning", at_risk: "danger" };

/** One client, everything about them. Advisers act on their own clients; the owner sees the same screens read-only. */
export default function AdvisorClientDetail() {
  const { clientId = "" } = useParams<{ clientId: string }>();
  const base = useStaffBase();
  const owner = useIsOwner();
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find(([k]) => k === params.get("tab"))?.[0] ?? "overview") as Tab;
  const [modal, setModal] = useState<null | "goal" | "item" | "reminder">(null);
  const { data: meta } = useMeta();

  const client = useGet<ClientDetail>(["client", clientId], `/clients/${clientId}`);
  const health = useGet<ClientHealth>(["client-health", clientId], `/clients/${clientId}/health`, { refetchMs: 20000 });
  const dash = useGet<ClientDashboard>(["clientDashboard", clientId], `/clients/${clientId}/dashboard`, { enabled: tab === "overview", refetchMs: 15000 });
  const opps = useGet<Page<Opportunity>>(["client-opps", clientId], `/opportunities?client_id=${clientId}&status=all&limit=50`, { enabled: tab === "opportunities", refetchMs: 15000 });
  const goals = useGet<Page<Goal>>(["client-goals", clientId], `/goals?client_id=${clientId}&status=all&limit=100`, { enabled: tab === "goals" });
  const items = useGet<Page<FinancialItem>>(["client-items", clientId], `/financial-items?client_id=${clientId}&limit=100`, { enabled: tab === "financial" });
  const rems = useGet<Page<Reminder>>(["client-reminders", clientId], `/reminders?client_id=${clientId}&status=all&limit=100`, { enabled: tab === "reminders" });
  const tl = useGet<{ items: TimelineItem[] }>(["client-timeline", clientId], `/clients/${clientId}/timeline`, { enabled: tab === "timeline", refetchMs: 15000 });
  const done = useAct((id: string) => api.post(`/reminders/${id}/complete`), [["client-reminders", clientId], ["advisorDashboard"], ["client-health", clientId]]);

  if (client.isLoading) return <Skeleton className="h-[600px] w-full" />;
  if (client.error) return <ErrorBanner error={client.error} onRetry={() => void client.refetch()} />;
  const c = client.data;
  if (!c) return <EmptyState message="Client not found" />;
  const h = health.data;

  return (
    <div className="space-y-5">
      <Link to={`${base}/clients`} className="inline-flex items-center gap-1 text-sm text-charcoal-500 hover:text-charcoal-800"><ArrowLeft className="w-4 h-4" aria-hidden="true" />Clients</Link>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold text-charcoal-900 dark:text-white">{c.full_name}</h1><p className="text-sm text-charcoal-600 dark:text-charcoal-300">{c.email}{c.phone ? ` · ${c.phone}` : ""}</p></div>
        {h && <div className="flex items-center gap-2"><Badge variant={BAND[h.band]} size="md">Health {h.score}/100 · {h.band.replace("_", " ")}</Badge></div>}
      </div>

      <div role="tablist" aria-label="Client sections" className="flex gap-1 overflow-x-auto border-b border-charcoal-200 dark:border-charcoal-700">
        {TABS.map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => setParams(k === "overview" ? {} : { tab: k })} className={`whitespace-nowrap px-3 pb-3 pt-1 text-sm font-medium border-b-2 -mb-px ${tab === k ? "border-brand-500 text-brand-600 dark:text-brand-300" : "border-transparent text-charcoal-500 hover:text-charcoal-800"}`}>{l}</button>)}
      </div>

      {tab === "overview" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <h2 className="font-semibold mb-2">Details</h2>
            <dl className="text-sm grid grid-cols-[10rem_1fr] gap-y-1.5">
              <dt className="text-charcoal-500">Client since</dt><dd>{c.client_since ? formatDate(c.client_since) : "–"}</dd>
              <dt className="text-charcoal-500">Date of birth</dt><dd>{c.date_of_birth ? formatDate(c.date_of_birth) : "–"}</dd>
              <dt className="text-charcoal-500">Last annual review</dt><dd>{c.last_annual_review_date ? formatDate(c.last_annual_review_date) : "None recorded"}</dd>
              <dt className="text-charcoal-500">Licence expiry</dt><dd>{c.drivers_licence_expiry ? formatDate(c.drivers_licence_expiry) : "–"}</dd>
              <dt className="text-charcoal-500">Dependants</dt><dd>{c.dependants ?? "not recorded"}</dd>
              <dt className="text-charcoal-500">Annual income</dt><dd>{c.annual_income_cents ? formatRand0(c.annual_income_cents) : "not recorded"}</dd>
            </dl>
            {!owner && (<><p className="mt-3 text-xs text-charcoal-500">Optional. Used only to check whether life cover keeps up with commitments; without them that check does not run.</p><NeedsForm key={`${c.dependants}-${c.annual_income_cents}`} clientId={clientId} dependants={c.dependants} income={c.annual_income_cents} /></>)}
          </Card>
          <Card>
            <h2 className="font-semibold mb-2">Client health</h2>
            {!h ? <Skeleton lines={4} /> : (
              <div className="space-y-2">{h.components.map((x) => <Bar key={x.key} label={`${x.label} · ${x.detail}`} value={x.points} max={x.weight} right={`${x.points}/${x.weight}`} tone={x.value >= 0.8 ? "success" : x.value >= 0.4 ? "brand" : "danger"} />)}
                <p className="text-xs text-charcoal-500">{h.last_contact_at ? `Last reached ${formatDateTime(h.last_contact_at)}.` : "No contact on record."}</p><InfoPopover label="How is health calculated?">{h.formula}</InfoPopover></div>
            )}
          </Card>
          {dash.isLoading && <Skeleton className="h-40 w-full lg:col-span-2" />}
          {dash.data && (<>
            <Card><h2 className="font-semibold mb-2">Position</h2><p className="text-sm text-charcoal-500">Net worth</p><p className="text-2xl font-bold">{formatZAR(dash.data.net_worth.net_worth_cents)}</p>
              <ul className="mt-3 text-sm divide-y divide-charcoal-100 dark:divide-charcoal-700">{dash.data.policies.items.map((p) => <li key={p.id} className="py-1.5 flex justify-between gap-2"><span>{p.product_name} <span className="text-charcoal-500">· {p.insurer.name}</span></span><StatusPill status={p.status} label={humanize(p.status)} /></li>)}</ul></Card>
            <Card><h2 className="font-semibold mb-2">Open claims and requests</h2>
              {dash.data.open_claims.items.length + dash.data.pending_requests.items.length === 0 ? <p className="text-sm text-charcoal-500">Nothing open.</p> : (
                <ul className="text-sm space-y-1.5">{dash.data.open_claims.items.map((cl) => <li key={cl.id} className="flex justify-between gap-2"><Link className="text-brand-600 hover:underline" to={`${base}/claims/${cl.id}`}>Claim {cl.reference}</Link><span>{cl.status_label}</span></li>)}
                  {dash.data.pending_requests.items.map((r) => <li key={r.id} className="flex justify-between gap-2"><span>{r.type_label}</span><StatusPill status={r.status} /></li>)}</ul>)}</Card>
          </>)}
        </div>
      )}

      {tab === "opportunities" && (
        <div className="space-y-3">
          {opps.isLoading && <Skeleton className="h-40 w-full" />}
          {opps.error ? <ErrorBanner error={opps.error} /> : null}
          {opps.data && itemsOf(opps.data).length === 0 && <EmptyState title="No opportunities" description="The rules found nothing worth raising for this client." />}
          {itemsOf(opps.data).map((o) => <OpportunityCard key={o.id} opportunity={o} base={base} canAct={!owner} />)}
        </div>
      )}

      {tab === "goals" && (
        <div className="space-y-3">
          {!owner && <div className="flex justify-end"><Button size="sm" onClick={() => setModal("goal")}>Add goal</Button></div>}
          {goals.isLoading && <Skeleton className="h-32 w-full" />}
          {goals.data && itemsOf(goals.data).length === 0 && <EmptyState message="No goals set" />}
          <div className="grid gap-3 md:grid-cols-2">{itemsOf(goals.data).map((g) => (
            <Card key={g.id} padding="sm"><div className="flex justify-between gap-2"><h3 className="font-semibold">{g.title}</h3><Badge>{humanize(g.status)}</Badge></div>
              <p className="text-xs text-charcoal-500">{humanize(g.category)}{g.target_date ? ` · by ${formatDate(g.target_date)}` : ""}{g.type === "shared" ? " · shared" : ""}</p>
              <div className="mt-2"><Bar label={`${formatRand0(g.current_amount_cents)} of ${formatRand0(g.target_amount_cents)}`} value={g.progress_percent} max={100} right={`${g.progress_percent}%`} /></div></Card>))}</div>
        </div>
      )}

      {tab === "financial" && (
        <div className="space-y-3">
          {!owner && <div className="flex justify-end"><Button size="sm" onClick={() => setModal("item")}>Add item</Button></div>}
          {items.isLoading && <Skeleton className="h-32 w-full" />}
          {items.data && itemsOf(items.data).length === 0 && <EmptyState message="No financial items" />}
          {itemsOf(items.data).length > 0 && <Card padding="none" className="overflow-x-auto"><table className="min-w-full text-sm"><caption className="sr-only">Balance sheet</caption><thead className="bg-charcoal-50 dark:bg-charcoal-900 text-left text-xs uppercase text-charcoal-500"><tr><th scope="col" className="px-4 py-2">Item</th><th scope="col" className="px-4 py-2">Type</th><th scope="col" className="px-4 py-2">Category</th><th scope="col" className="px-4 py-2 text-right">Amount</th></tr></thead>
            <tbody className="divide-y divide-charcoal-100 dark:divide-charcoal-700">{itemsOf(items.data).map((i) => <tr key={i.id}><td className="px-4 py-2 font-medium">{i.label}</td><td className="px-4 py-2 capitalize">{i.kind}</td><td className="px-4 py-2">{humanize(i.category)}</td><td className="px-4 py-2 text-right tabular-nums">{formatZAR(i.amount_cents)}</td></tr>)}</tbody></table></Card>}
        </div>
      )}

      {tab === "reminders" && (
        <div className="space-y-3">
          {!owner && <div className="flex justify-end"><Button size="sm" onClick={() => setModal("reminder")}>Add reminder</Button></div>}
          {rems.isLoading && <Skeleton className="h-32 w-full" />}
          {rems.data && itemsOf(rems.data).length === 0 && <EmptyState message="No reminders for this client" />}
          <Card padding="none"><ul className="divide-y divide-charcoal-100 dark:divide-charcoal-700">{itemsOf(rems.data).map((r) => (
            <li key={r.id} className="p-4 flex flex-wrap items-center justify-between gap-2 text-sm"><span><span className="font-medium">{r.title}</span><span className="block text-xs text-charcoal-500">{humanize(r.type)} · due {formatDate(r.due_date)} · for {r.audience === "both" ? "both" : r.audience}</span></span>
              <span className="flex items-center gap-2"><StatusPill status={r.status === "pending" ? r.urgency : r.status} />{r.status === "pending" && !owner && <Button size="sm" variant="secondary" loading={done.isPending} onClick={() => done.mutate(r.id)}>Mark done</Button>}</span></li>))}</ul></Card>
        </div>
      )}

      {tab === "identity" && <IdentityTab clientId={clientId} canAct={!owner} />}
      {tab === "compliance" && <ComplianceTab clientId={clientId} clientName={c.full_name} canAct={!owner} />}

      {tab === "timeline" && (
        <Card>
          <h2 className="font-semibold mb-3">Everything that has happened for this client</h2>
          {tl.isLoading && <Skeleton lines={4} />}
          {tl.data && tl.data.items.length === 0 && <p className="text-sm text-charcoal-500">Nothing yet.</p>}
          <ol className="relative border-l-2 border-charcoal-200 dark:border-charcoal-700 ml-2 space-y-3">{(tl.data?.items ?? []).map((e) => (
            <li key={e.id} className="pl-4 relative"><span className="absolute -left-[7px] top-1.5 w-3 h-3 rounded-full bg-brand-500" aria-hidden="true" /><p className="text-sm text-charcoal-900 dark:text-white">{e.summary}</p><p className="text-xs text-charcoal-500">{e.actor.full_name ?? "System"} ({e.actor.role}) · {formatDateTime(e.occurred_at)}</p></li>))}</ol>
        </Card>
      )}

      <AddGoalModal key={`g${modal === "goal"}`} clientId={clientId} open={modal === "goal"} onClose={() => setModal(null)} categories={meta?.goal_categories} />
      <AddItemModal key={`i${modal === "item"}`} clientId={clientId} open={modal === "item"} onClose={() => setModal(null)} assets={meta?.financial_item_categories?.asset} liabilities={meta?.financial_item_categories?.liability} />
      <AddReminderModal key={`r${modal === "reminder"}`} clientId={clientId} open={modal === "reminder"} onClose={() => setModal(null)} />
    </div>
  );
}
