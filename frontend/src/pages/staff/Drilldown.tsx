import React from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { PageHeader, DemoBadge, Skeleton, ErrorBanner, EmptyState } from "../../components/ui";
import { useGet } from "../../lib/hooks";
import { useStaffBase } from "../../lib/staff";
import { formatRand0 } from "../../lib/utils";
import type { DrillResult } from "../../lib/typesExt";

const TITLES: Record<string, string> = {
  "at_risk.all": "Clients with revenue at risk", "at_risk.lapsed": "Clients with lapsed policies", "at_risk.review_overdue": "Reviews overdue",
  "at_risk.stale_claims": "Claims stuck in one status", "at_risk.identity": "Identity documents expiring or expired",
  "opportunities.open": "Live opportunities", "retention.not_contacted": "Clients not contacted recently", "retention.reviews_overdue": "Reviews overdue",
  "retention.at_risk": "At-risk clients (health score)", "compliance.gaps": "Open compliance gaps",
};

/** The records behind any Business Health number. The count on the tile equals the number of rows here. */
export default function Drilldown() {
  const base = useStaffBase();
  const { metric = "" } = useParams<{ metric: string }>();
  const q = useGet<DrillResult>(["drill", metric], `/owner/drilldown?limit=100&metric=${encodeURIComponent(metric)}`);
  const title = TITLES[metric] ?? (metric.startsWith("products.") ? `Clients with ${metric.slice(9)} active product(s)` : "Records");

  return (
    <div>
      <Link to={base} className="inline-flex items-center gap-1 text-sm text-charcoal-500 hover:text-charcoal-800 dark:hover:text-white mb-3"><ArrowLeft className="w-4 h-4" aria-hidden="true" />Business health</Link>
      <PageHeader title={title} badge={q.data?.value_cents ? <DemoBadge /> : undefined}
        subtitle={q.data ? <>{q.data.total} record(s){q.data.value_cents ? <> · about {formatRand0(q.data.value_cents)} a year at stake (demo estimate)</> : null}</> : undefined} />
      {q.isLoading && <Skeleton className="h-64 w-full" />}
      {q.error ? <ErrorBanner error={q.error} onRetry={() => void q.refetch()} /> : null}
      {q.data && q.data.items.length === 0 && <EmptyState title="No records" description="Nothing matches right now." />}
      {q.data && q.data.items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-charcoal-100 dark:border-charcoal-700 bg-white dark:bg-charcoal-800">
          <table className="min-w-full text-sm">
            <caption className="sr-only">{title}</caption>
            <thead className="bg-charcoal-50 dark:bg-charcoal-900 text-left text-xs uppercase tracking-wide text-charcoal-500">
              <tr><th scope="col" className="px-4 py-3">Client</th><th scope="col" className="px-4 py-3">Detail</th><th scope="col" className="px-4 py-3">Adviser</th><th scope="col" className="px-4 py-3 text-right">Value / year</th><th scope="col" className="px-4 py-3"><span className="sr-only">Open</span></th></tr>
            </thead>
            <tbody className="divide-y divide-charcoal-100 dark:divide-charcoal-700">
              {q.data.items.map((r, i) => (
                <tr key={`${r.client.id}-${i}`} className="align-top">
                  <td className="px-4 py-3 font-medium text-charcoal-900 dark:text-white whitespace-nowrap">{r.client.full_name}</td>
                  <td className="px-4 py-3 text-charcoal-700 dark:text-charcoal-300">{r.severity && <span className={`mr-2 font-semibold ${r.severity === "high" ? "text-accent-600" : "text-amber-700"}`}>{r.severity === "high" ? "High" : "Medium"}</span>}{r.detail}</td>
                  <td className="px-4 py-3 text-charcoal-600 dark:text-charcoal-400 whitespace-nowrap">{r.adviser.full_name}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{r.value_cents ? formatRand0(r.value_cents) : "–"}</td>
                  <td className="px-4 py-3 text-right whitespace-nowrap"><Link className="text-brand-600 dark:text-brand-300 hover:underline" to={`${base}${r.link.path}`}>Open</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
