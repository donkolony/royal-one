import React, { useState } from "react";
import { Download, ShieldCheck } from "lucide-react";
import { Button, EmptyState, ErrorBanner, PageHeader, Skeleton, InfoPopover } from "../../components/ui";
import { download } from "../../lib/api";
import { api } from "../../lib/api";
import { useGet } from "../../lib/hooks";
import { useIsOwner } from "../../lib/staff";
import { formatDateTime, itemsOf } from "../../lib/utils";
import type { ClientSummary, Page } from "../../lib/types";
import type { AuditPage } from "../../lib/typesExt";

const GROUPS: [string, string][] = [["", "Everything"], ["claim", "Claims"], ["request", "Requests"], ["document", "Documents"], ["identity", "Identity"], ["consent", "Consents"],
  ["advice", "Advice records"], ["opportunity", "Opportunities"], ["assistant", "Assistant questions"], ["client", "Client file views"], ["access.denied", "Refused access"],
  ["compliance", "Compliance packs"], ["audit", "Audit exports"]];

const ROLE_TONE: Record<string, string> = { client: "bg-blue-50 text-blue-800", advisor: "bg-brand-50 text-brand-700", owner: "bg-accent-50 text-accent-700", system: "bg-charcoal-100 text-charcoal-700" };

/** The audit trail: who did what, to whom, when. Searchable, filterable and exportable for a regulator or an insurer. */
export default function AuditLog() {
  const owner = useIsOwner();
  const [f, setF] = useState({ client_id: "", action: "", q: "", date_from: "", date_to: "" });
  const [limit, setLimit] = useState(50);
  const [verify, setVerify] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const filters = Object.entries(f).filter(([, v]) => v).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  const clients = useGet<Page<ClientSummary>>(["clients-lite"], "/clients?limit=100");
  const q = useGet<AuditPage>(["audit", filters, limit], `/audit?limit=${limit}${filters ? `&${filters}` : ""}`, { refetchMs: 15000 });
  const set = (k: keyof typeof f, v: string) => { setF((s) => ({ ...s, [k]: v })); setLimit(50); };

  const doExport = async () => { setBusy(true); setErr(null); try { await download(`/audit/export${filters ? `?${filters}` : ""}`, "royal-square-audit-log.csv"); } catch (e) { setErr(e); } finally { setBusy(false); } };
  const doVerify = async () => { setErr(null); try { const v = await api.get<{ ok: boolean; checked: number; first_bad_id: number | null }>("/audit/verify"); setVerify(v.ok ? `Intact: ${v.checked} entries verified from the first to the latest.` : `Broken at entry #${v.first_bad_id}: an entry no longer matches its hash.`); } catch (e) { setErr(e); } };

  const inp = "h-9 rounded-md border-charcoal-300 py-0 text-sm dark:bg-charcoal-900 dark:border-charcoal-600";
  return (
    <div>
      <PageHeader title="Audit log" subtitle={owner ? "Every meaningful event across the firm. Append-only and hash-chained." : "Every event on your clients, and everything you did. Append-only."}
        actions={<>{owner && <Button variant="secondary" size="sm" onClick={() => void doVerify()}><ShieldCheck className="w-4 h-4 mr-1.5" aria-hidden="true" />Verify integrity</Button>}<Button size="sm" onClick={() => void doExport()} loading={busy}><Download className="w-4 h-4 mr-1.5" aria-hidden="true" />Export CSV</Button></>} />
      {verify && <p role="status" className={`mb-3 rounded-md px-4 py-2 text-sm ${verify.startsWith("Intact") ? "bg-green-50 text-green-900" : "bg-red-50 text-red-900"}`}>{verify}</p>}
      <div className="mb-2"><InfoPopover label="How tamper-evidence works">Each entry stores a SHA-256 hash of its content and of the entry before it, and the database refuses to change or delete entries. This is demo-level protection: a database administrator could still remove those safeguards, but "Verify integrity" would then show which entry no longer matches.</InfoPopover></div>
      <form className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-5" onSubmit={(e) => e.preventDefault()} aria-label="Filters">
        <label className="text-xs">Client<select className={inp + " w-full"} value={f.client_id} onChange={(e) => set("client_id", e.target.value)}><option value="">All clients</option>{itemsOf(clients.data).map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}</select></label>
        <label className="text-xs">What<select className={inp + " w-full"} value={f.action} onChange={(e) => set("action", e.target.value)}>{GROUPS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label className="text-xs">From<input type="date" className={inp + " w-full"} value={f.date_from} onChange={(e) => set("date_from", e.target.value)} /></label>
        <label className="text-xs">To<input type="date" className={inp + " w-full"} value={f.date_to} onChange={(e) => set("date_to", e.target.value)} /></label>
        <label className="text-xs">Search<input className={inp + " w-full"} placeholder="Words in the summary" value={f.q} onChange={(e) => set("q", e.target.value)} /></label>
      </form>
      {err ? <div className="mb-3"><ErrorBanner error={err} /></div> : null}
      {q.isLoading && <Skeleton className="h-64 w-full" />}
      {q.error ? <ErrorBanner error={q.error} onRetry={() => void q.refetch()} /> : null}
      {q.data && q.data.items.length === 0 && <EmptyState title="No entries match" description="Try a wider date range or fewer filters." />}
      {q.data && q.data.items.length > 0 && (
        <>
          <p className="mb-2 text-sm text-charcoal-600 dark:text-charcoal-300">{q.data.total} entr{q.data.total === 1 ? "y" : "ies"} · showing {q.data.items.length}</p>
          <div className="overflow-x-auto rounded-lg border border-charcoal-100 dark:border-charcoal-700 bg-white dark:bg-charcoal-800">
            <table className="min-w-full text-sm">
              <caption className="sr-only">Audit log</caption>
              <thead className="bg-charcoal-50 dark:bg-charcoal-900 text-left text-xs uppercase tracking-wide text-charcoal-500"><tr><th scope="col" className="px-3 py-2">When</th><th scope="col" className="px-3 py-2">Who</th><th scope="col" className="px-3 py-2">What happened</th><th scope="col" className="px-3 py-2">Client</th></tr></thead>
              <tbody className="divide-y divide-charcoal-100 dark:divide-charcoal-700">
                {q.data.items.map((e) => (
                  <tr key={e.id} className="align-top">
                    <td className="px-3 py-2 whitespace-nowrap text-charcoal-600 dark:text-charcoal-300">{formatDateTime(e.occurred_at)}<span className="block text-[11px] text-charcoal-400">#{e.id}</span></td>
                    <td className="px-3 py-2 whitespace-nowrap"><span className="font-medium text-charcoal-900 dark:text-white">{e.actor.full_name ?? "System"}</span> <span className={`ml-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${ROLE_TONE[e.actor.role] ?? ""}`}>{e.actor.role}</span></td>
                    <td className="px-3 py-2"><span className="text-charcoal-900 dark:text-white">{e.summary}</span><span className="block font-mono text-[11px] text-charcoal-400">{e.action}{e.ip ? ` · ${e.ip}` : ""}</span></td>
                    <td className="px-3 py-2 whitespace-nowrap text-charcoal-700 dark:text-charcoal-300">{e.client?.full_name ?? "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {q.data.total > limit && <div className="mt-3 text-center"><Button variant="secondary" size="sm" onClick={() => setLimit((n) => n + 50)}>Show 50 more</Button></div>}
        </>
      )}
    </div>
  );
}
