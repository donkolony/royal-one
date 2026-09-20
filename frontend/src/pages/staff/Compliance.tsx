import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Download, FileText } from "lucide-react";
import { Bar, Button, Card, DemoBadge, EmptyState, ErrorBanner, InfoPopover, PageHeader, Skeleton, StatTile } from "../../components/ui";
import { IdentityStateChip } from "../../components/identity/IdentityStateChip";
import { api, download } from "../../lib/api";
import { useGet } from "../../lib/hooks";
import { useIsOwner, useStaffBase } from "../../lib/staff";
import { formatDate, formatDateTime } from "../../lib/utils";
import type { CompliancePack, ComplianceOverview, IdentityState, RetentionReview } from "../../lib/typesExt";

const STATE_TONE: Record<string, string> = { valid: "text-green-700", current: "text-green-700", expiring: "text-amber-700", missing: "text-accent-600", expired: "text-accent-600", withdrawn: "text-accent-600", stale: "text-amber-700", unacknowledged: "text-amber-700", pending: "text-blue-700" };

/**
 * Compliance in one place: how healthy the records are, what to fix, and the regulator / insurer request button that assembles a
 * client's complete, timestamped, audit-backed pack in seconds.
 */
export default function Compliance() {
  const base = useStaffBase();
  const owner = useIsOwner();
  const o = useGet<ComplianceOverview>(["compliance-overview"], "/compliance/overview", { refetchMs: 15000 });
  const ret = useGet<RetentionReview>(["retention"], "/compliance/retention", { enabled: owner });
  const [client, setClient] = useState("");
  const [pack, setPack] = useState<CompliancePack | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const run = async (kind: "view" | "pdf" | "csv") => {
    if (!client) return;
    setBusy(kind); setErr(null);
    try {
      if (kind === "view") setPack(await api.get<CompliancePack>(`/clients/${client}/compliance`));
      else if (kind === "pdf") await download(`/clients/${client}/compliance/pack.pdf`, "compliance-pack.pdf");
      else await download(`/audit/export?client_id=${client}`, "audit-log-client.csv");
    } catch (e) { setErr(e); } finally { setBusy(null); }
  };

  if (o.isLoading) return <Skeleton className="h-96 w-full" />;
  if (o.error) return <ErrorBanner error={o.error} onRetry={() => void o.refetch()} />;
  const d = o.data;
  if (!d) return null;
  const s = d.summary;
  const name = d.clients.find((c) => c.id === client)?.full_name;

  return (
    <div>
      <PageHeader title="Compliance" subtitle={owner ? "Identity, advice records and consent across every client, and the request button for a regulator or an insurer." : "Identity, advice records and consent for your clients."} />
      <div className="grid gap-4 lg:grid-cols-3">
        <StatTile label="Compliance score" value={s.score_percent === null ? "n/a" : `${s.score_percent}%`} tone={(s.score_percent ?? 0) >= 80 ? "success" : "danger"} sub={`${s.fully_compliant_clients} of ${s.clients} clients fully compliant`} />
        <Card className="lg:col-span-2 space-y-2">
          <Bar label="Valid identity document" value={s.components.identity.ok} max={s.components.identity.total} right={`${s.components.identity.ok}/${s.components.identity.total}`} tone="success" />
          <Bar label="Advice record, acknowledged, last 12 months" value={s.components.advice.ok} max={s.components.advice.total} right={`${s.components.advice.ok}/${s.components.advice.total}`} tone="success" />
          <Bar label="Current data-processing consent" value={s.components.consent.ok} max={s.components.consent.total} right={`${s.components.consent.ok}/${s.components.consent.total}`} tone="success" />
          <InfoPopover>{s.definition}</InfoPopover>
        </Card>
      </div>

      <Card className="mt-6">
        <h2 className="font-semibold text-charcoal-900 dark:text-white">Regulator or insurer request</h2>
        <p className="text-sm text-charcoal-600 dark:text-charcoal-300 mt-1">Pick a client to assemble their identity, advice, consent, claims and access history into one timestamped pack. Every export is itself logged.</p>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <label className="text-sm"><span className="block font-medium mb-1">Client</span>
            <select value={client} onChange={(e) => { setClient(e.target.value); setPack(null); }} className="h-10 min-w-[16rem] rounded-md border-charcoal-300 dark:bg-charcoal-900 dark:border-charcoal-600 text-sm"><option value="">Choose a client…</option>{d.clients.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}</select></label>
          <Button disabled={!client} loading={busy === "view"} onClick={() => void run("view")}><FileText className="w-4 h-4 mr-1.5" aria-hidden="true" />Build pack</Button>
          <Button variant="secondary" disabled={!client} loading={busy === "pdf"} onClick={() => void run("pdf")}><Download className="w-4 h-4 mr-1.5" aria-hidden="true" />PDF</Button>
          <Button variant="secondary" disabled={!client} loading={busy === "csv"} onClick={() => void run("csv")}><Download className="w-4 h-4 mr-1.5" aria-hidden="true" />Audit CSV</Button>
        </div>
        {err ? <div className="mt-3"><ErrorBanner error={err} /></div> : null}
        {pack && (
          <div className="mt-4 rounded-md border border-charcoal-200 dark:border-charcoal-700 p-4 text-sm space-y-2" role="region" aria-label="Pack summary">
            <p><span className="font-semibold">{pack.reference}</span> for {pack.client.full_name}, generated {formatDateTime(pack.generated_at)} in {pack.generation_ms} ms by {pack.generated_by.full_name}.</p>
            <p className="font-mono text-xs break-all">SHA-256 {pack.content_sha256}</p>
            <ul className="grid sm:grid-cols-3 gap-2">
              {(["identity", "advice", "consent"] as const).map((k) => <li key={k} className="rounded bg-charcoal-50 dark:bg-charcoal-900 px-3 py-2 capitalize">{k}: <span className={`font-semibold ${STATE_TONE[pack.compliance_status[k].state] ?? ""}`}>{pack.compliance_status[k].state}</span></li>)}
            </ul>
            <p>{pack.advice_records.length} advice record(s) · {pack.claims.length} claim(s) · {pack.requests.length} request(s) · {pack.access_history.length} access-history entries · audit chain {pack.integrity.audit_chain_ok ? <span className="text-green-700 font-semibold">intact</span> : <span className="text-accent-600 font-semibold">BROKEN</span>}.</p>
            <p className="text-xs text-charcoal-500">Left out on purpose: {pack.excluded_for_data_minimisation.join(", ")}.</p>
          </div>
        )}
        {name && !pack && <p className="mt-3 text-xs text-charcoal-500">Ready to build the pack for {name}.</p>}
      </Card>

      <Card className="mt-6">
        <h2 className="font-semibold text-charcoal-900 dark:text-white mb-2">Open gaps ({s.gaps.length})</h2>
        {s.gaps.length === 0 ? <p className="text-sm text-charcoal-500">Nothing to fix.</p> : (
          <ul className="divide-y divide-charcoal-100 dark:divide-charcoal-700 text-sm">
            {s.gaps.map((g) => (
              <li key={`${g.client.id}-${g.kind}`} className="py-2 flex flex-wrap items-center justify-between gap-2">
                <span><span className={`font-semibold ${g.severity === "high" ? "text-accent-600" : "text-amber-700"}`}>{g.severity === "high" ? "High" : "Medium"}</span> · {g.client.full_name}: {g.label}</span>
                <Link className="text-brand-600 dark:text-brand-300 hover:underline" to={`${base}${g.fix_path}`}>Fix</Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card className="mt-6 overflow-x-auto">
        <h2 className="font-semibold text-charcoal-900 dark:text-white mb-2">Every client</h2>
        <table className="min-w-full text-sm"><caption className="sr-only">Compliance by client</caption>
          <thead className="text-left text-xs uppercase text-charcoal-500"><tr><th scope="col" className="py-2 pr-4">Client</th><th scope="col" className="pr-4">Identity</th><th scope="col" className="pr-4">Advice record</th><th scope="col">Consent</th></tr></thead>
          <tbody className="divide-y divide-charcoal-100 dark:divide-charcoal-700">
            {d.clients.map((c) => <tr key={c.id}><td className="py-2 pr-4"><Link className="font-medium text-brand-600 dark:text-brand-300 hover:underline" to={`${base}/clients/${c.id}?tab=compliance`}>{c.full_name}</Link><span className="block text-xs text-charcoal-500">{c.adviser}</span></td>
              <td className="pr-4"><IdentityStateChip state={(["valid", "expiring", "expired", "pending", "missing"].includes(c.identity) ? c.identity : "missing") as IdentityState} /></td>
              <td className={`pr-4 capitalize ${STATE_TONE[c.advice] ?? ""}`}>{c.advice}</td><td className={`capitalize ${STATE_TONE[c.consent] ?? ""}`}>{c.consent}</td></tr>)}
          </tbody></table>
      </Card>

      {owner && (
        <Card className="mt-6">
          <div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold text-charcoal-900 dark:text-white">Retention review</h2><DemoBadge>Placeholder period</DemoBadge></div>
          {ret.isLoading && <Skeleton lines={2} />}
          {ret.data && (
            <>
              <p className="text-sm text-charcoal-600 dark:text-charcoal-300 mt-1">{ret.data.note}</p>
              <p className="text-sm mt-2">Records closed before <strong>{formatDate(ret.data.cutoff_date)}</strong> ({ret.data.retention_years} years): <strong>{ret.data.total}</strong> flagged.</p>
              {ret.data.items.length === 0 ? <EmptyState title="Nothing past retention" description="No record is older than the configured period." /> : (
                <ul className="mt-2 divide-y divide-charcoal-100 dark:divide-charcoal-700 text-sm">{ret.data.items.map((i) => <li key={i.entity_id} className="py-2 flex justify-between gap-2"><span>{i.label} · {i.client.full_name}</span><span className="text-charcoal-500">{formatDate(i.date)}</span></li>)}</ul>
              )}
            </>
          )}
        </Card>
      )}
    </div>
  );
}
