import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { PageHeader, StatTile, Bar, DemoBadge, InfoPopover, Skeleton, ErrorBanner, Card } from "../../components/ui";
import { useGet } from "../../lib/hooks";
import { ResetDemoButton } from "../../components/staff/ResetDemoButton";
import { useStaffBase } from "../../lib/staff";
import { formatRand0, relativeTime } from "../../lib/utils";
import type { BusinessHealth } from "../../lib/typesExt";

const drill = (base: string, metric: string) => `${base}/drill/${encodeURIComponent(metric)}`;

/**
 * The owner's home. Every tile answers "where is money made or lost?" and every number is a link to the records behind it.
 * Rand figures are demo estimates and say so; the productivity block is an illustrative model and says so too.
 */
export default function BusinessHealthPage() {
  const base = useStaffBase();
  const q = useGet<BusinessHealth>(["business-health"], "/owner/business-health", { refetchMs: 10000 });

  if (q.isLoading) return <div className="space-y-4"><Skeleton className="h-16 w-full" /><Skeleton className="h-40 w-full" /><Skeleton className="h-72 w-full" /></div>;
  if (q.error) return <ErrorBanner error={q.error} onRetry={() => void q.refetch()} />;
  const d = q.data;
  if (!d) return null;
  const { revenue_at_risk: risk, revenue_opportunity: opp, compliance: comp, retention: ret, productivity: prod, products_per_client: prods } = d;
  const maxOpp = Math.max(1, ...opp.by_adviser.map((a) => a.open_value_cents));
  const maxDist = Math.max(1, ...Object.values(prods.distribution));

  return (
    <div>
      <PageHeader
        title="Business health"
        badge={<DemoBadge />}
        actions={<ResetDemoButton />}
        subtitle={<>Where money is made or lost across {d.clients} clients. Updated {relativeTime(d.generated_at)}. {d.label}</>}
      />

      <section aria-labelledby="act-today" className="mb-6">
        <h2 id="act-today" className="text-lg font-semibold text-charcoal-900 dark:text-white mb-3">Act on today</h2>
        <ol className="grid gap-3 md:grid-cols-3">
          {d.top_actions.map((a, i) => (
            <li key={a.key} className="rounded-lg border border-charcoal-100 dark:border-charcoal-700 bg-white dark:bg-charcoal-800 p-4 shadow-sm flex flex-col">
              <div className="flex items-center gap-2">
                <span className="grid place-items-center w-6 h-6 rounded-full bg-brand-500 text-white text-xs font-bold" aria-hidden="true">{i + 1}</span>
                <span className="text-xs uppercase tracking-wide text-charcoal-500">{a.tier === 3 ? "Urgent" : a.tier === 2 ? "Money" : "Watch"}</span>
              </div>
              <p className="mt-2 font-semibold text-charcoal-900 dark:text-white">{a.title}</p>
              <p className="mt-1 text-sm text-charcoal-600 dark:text-charcoal-300 grow">{a.detail}</p>
              <Link to={`${base}${a.path}`} className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-600 dark:text-brand-300 hover:underline">
                Open the records <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ol>
        <div className="mt-2"><InfoPopover label="How are these three chosen?">{d.top_actions_rule}</InfoPopover></div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="text-base font-semibold text-charcoal-900 dark:text-white">Revenue at risk</h2>
          <StatTile label="Estimated annual commission at stake" value={formatRand0(risk.total_cents)} tone="danger" sub={`${risk.clients} client(s), each counted once, on ${formatRand0(risk.premium_cents)} of annual premium`} to={drill(base, risk.drilldown)} />
          <ul className="mt-3 divide-y divide-charcoal-100 dark:divide-charcoal-700">
            {risk.reasons.map((r) => (
              <li key={r.key}>
                <Link to={drill(base, r.drilldown)} className="flex items-center justify-between gap-3 py-2 text-sm hover:bg-charcoal-50 dark:hover:bg-charcoal-700/50 rounded px-1">
                  <span><span className="font-medium text-charcoal-800 dark:text-charcoal-100">{r.label}</span><span className="block text-xs text-charcoal-500">{r.how}</span></span>
                  <span className="text-right tabular-nums shrink-0"><span className="font-semibold">{r.count}</span><span className="block text-xs text-charcoal-500">{formatRand0(r.value_cents)}</span></span>
                </Link>
              </li>
            ))}
          </ul>
          <div className="mt-2"><InfoPopover>{risk.formula} Reasons can overlap, so the rows add up to more than the total.</InfoPopover></div>
        </Card>

        <Card>
          <h2 className="text-base font-semibold text-charcoal-900 dark:text-white">Revenue opportunity</h2>
          <StatTile label="Estimated annual value of live opportunities" value={formatRand0(opp.open_value_cents)} tone="brand" sub={`${opp.open_count} opportunities`} to={drill(base, opp.drilldown)} />
          <div className="mt-3 space-y-2">
            {opp.by_adviser.map((a) => (
              <Bar key={a.adviser.id} label={`${a.adviser.full_name} · ${a.open} open · ${a.won} won / ${a.lost} lost`} value={a.open_value_cents} max={maxOpp} right={formatRand0(a.open_value_cents)} />
            ))}
          </div>
          <p className="mt-3 text-xs text-charcoal-600 dark:text-charcoal-300">
            Surfaced {opp.totals.surfaced} · actioned {opp.totals.actioned} · won {opp.totals.won} (worth {formatRand0(opp.totals.won_value_cents)}) · conversion {opp.totals.conversion_rate === null ? "n/a yet" : `${Math.round(opp.totals.conversion_rate * 100)}%`}
          </p>
          <div className="mt-2 flex flex-wrap gap-x-4"><Link to={`${base}/radar`} className="text-sm text-brand-600 dark:text-brand-300 hover:underline">Open the radar</Link>
            <InfoPopover label="Definitions">{Object.entries(opp.definitions).map(([k, v]) => <p key={k}><span className="font-semibold capitalize">{k}:</span> {v}</p>)}</InfoPopover></div>
        </Card>

        <Card>
          <h2 className="text-base font-semibold text-charcoal-900 dark:text-white">Compliance health</h2>
          <StatTile label="Compliance score" value={comp.score_percent === null ? "n/a" : `${comp.score_percent}%`} tone={comp.score_percent !== null && comp.score_percent >= 80 ? "success" : "danger"} sub={`${comp.fully_compliant_clients} of ${comp.clients} clients fully compliant · ${comp.open_gaps} open gap(s)`} to={drill(base, comp.drilldown)} />
          <div className="mt-3 space-y-2">
            <Bar label="Valid identity document" value={comp.components.identity.ok} max={comp.components.identity.total} right={`${comp.components.identity.ok}/${comp.components.identity.total}`} tone="success" />
            <Bar label="Advice record, acknowledged, last 12 months" value={comp.components.advice.ok} max={comp.components.advice.total} right={`${comp.components.advice.ok}/${comp.components.advice.total}`} tone="success" />
            <Bar label="Current data-processing consent" value={comp.components.consent.ok} max={comp.components.consent.total} right={`${comp.components.consent.ok}/${comp.components.consent.total}`} tone="success" />
          </div>
          <ul className="mt-3 space-y-1">
            {comp.gaps.slice(0, 5).map((g) => (
              <li key={`${g.client.id}-${g.kind}`} className="flex items-center justify-between gap-2 text-sm">
                <span><span className={g.severity === "high" ? "text-accent-600 font-semibold" : "text-amber-700 dark:text-amber-300 font-semibold"}>{g.severity === "high" ? "High" : "Medium"}</span> · {g.client.full_name}: {g.label}</span>
                <Link to={`${base}${g.fix_path}`} className="shrink-0 text-brand-600 dark:text-brand-300 hover:underline">Fix</Link>
              </li>
            ))}
          </ul>
          <div className="mt-2 flex flex-wrap gap-x-4"><Link to={`${base}/compliance`} className="text-sm text-brand-600 dark:text-brand-300 hover:underline">All compliance gaps</Link><InfoPopover>{comp.definition}</InfoPopover></div>
        </Card>

        <Card>
          <h2 className="text-base font-semibold text-charcoal-900 dark:text-white">Retention</h2>
          <div className="mt-2 grid grid-cols-3 gap-3">
            <StatTile label={`Not contacted in ${ret.not_contacted.days} days`} value={ret.not_contacted.count} tone={ret.not_contacted.count ? "danger" : "success"} to={drill(base, ret.not_contacted.drilldown)} />
            <StatTile label="Reviews overdue" value={ret.reviews_overdue.count} tone={ret.reviews_overdue.count ? "danger" : "success"} to={drill(base, ret.reviews_overdue.drilldown)} />
            <StatTile label="At-risk clients" value={ret.at_risk.count} tone={ret.at_risk.count ? "danger" : "success"} to={drill(base, ret.at_risk.drilldown)} />
          </div>
          <div className="mt-3"><InfoPopover label="How are these calculated?"><p>{ret.reviews_overdue.rule}</p><p className="mt-1">{ret.at_risk.formula}</p></InfoPopover></div>
          <h3 className="mt-5 text-sm font-semibold text-charcoal-900 dark:text-white">Products per client <span className="font-normal text-charcoal-500">· average {prods.average ?? "n/a"}</span></h3>
          <div className="mt-2 space-y-2">
            {Object.entries(prods.distribution).map(([n, count]) => (
              <Link key={n} to={drill(base, `products.${n}`)} className="block hover:bg-charcoal-50 dark:hover:bg-charcoal-700/50 rounded px-1 py-0.5">
                <Bar label={`${n} product${n === "1" ? "" : "s"}`} value={count} max={maxDist} right={`${count} client${count === 1 ? "" : "s"}`} />
              </Link>
            ))}
          </div>
          <div className="mt-2"><InfoPopover>{prods.how}</InfoPopover></div>
        </Card>

        <Card className="lg:col-span-2">
          <div className="flex flex-wrap items-center gap-2"><h2 className="text-base font-semibold text-charcoal-900 dark:text-white">Adviser productivity</h2><DemoBadge>Illustrative model</DemoBadge></div>
          <p className="text-xs text-charcoal-500 mt-1">{prod.label}</p>
          <div className="mt-3 grid grid-cols-2 lg:grid-cols-4 gap-3">
            <StatTile label="Admin tasks automated" value={prod.admin_tasks_automated.count} sub={`about ${Math.round(prod.admin_tasks_automated.minutes_avoided / 60 * 10) / 10} h avoided in ${prod.window_days} days`} />
            <StatTile label="Client-facing share" value={prod.client_facing_share.percent === null ? "n/a" : `${prod.client_facing_share.percent}%`} sub="of modelled adviser time" tone="brand" />
            <StatTile label="Average claim handling" value={prod.avg_claim_handling_days === null ? "n/a" : `${prod.avg_claim_handling_days} d`} sub={prod.avg_claim_handling_basis} />
            <StatTile label="Workflows completed" value={prod.workflows_completed} sub={`last ${prod.window_days} days`} />
          </div>
          <div className="mt-3 grid sm:grid-cols-2 gap-x-8 gap-y-1 text-sm">
            {prod.clients_per_adviser.map((a) => <div key={a.adviser.id} className="flex justify-between"><span>{a.adviser.full_name}</span><span className="tabular-nums font-medium">{a.clients} clients</span></div>)}
          </div>
          <div className="mt-2 flex flex-wrap gap-x-4">
            <InfoPopover label="How is automation counted?">{prod.admin_tasks_automated.how}<ul className="mt-1">{Object.entries(prod.admin_tasks_automated.items).map(([k, v]) => <li key={k}>{k.replace(/_/g, " ")}: {v.count} × {v.minutes_each} min</li>)}</ul></InfoPopover>
            <InfoPopover label="How is the client-facing share modelled?">{prod.client_facing_share.how} Client-facing {prod.client_facing_share.client_facing_minutes} min vs manual admin {prod.client_facing_share.manual_admin_minutes} min.</InfoPopover>
          </div>
        </Card>
      </div>
    </div>
  );
}
