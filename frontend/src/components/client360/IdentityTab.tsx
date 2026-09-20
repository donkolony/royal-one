import React, { useState } from "react";
import { Button, Card, DemoBadge, ErrorBanner, Skeleton } from "../ui";
import { IdentityStateChip } from "../identity/IdentityStateChip";
import { IdentityUpload } from "../identity/IdentityUpload";
import { api } from "../../lib/api";
import { useAct, useGet } from "../../lib/hooks";
import { formatDate, formatDateTime } from "../../lib/utils";
import type { IdentityDocument, IdentityDocType, IdentityVault } from "../../lib/typesExt";

const REFRESH = [["identity"], ["client-compliance"], ["notifications"], ["business-health"], ["compliance-overview"], ["audit"], ["client-health"]];
const TYPES: [IdentityDocType, string][] = [["id_document", "ID document"], ["drivers_licence", "Driver's licence"], ["proof_of_address", "Proof of address"]];

function DocRow({ d, canAct }: { d: IdentityDocument; canAct: boolean }) {
  const [expiry, setExpiry] = useState(d.expiry_date ?? "");
  const [reason, setReason] = useState("");
  const [rejecting, setRejecting] = useState(false);
  const verify = useAct(() => api.post(`/identity/${d.id}/verify`, { expiry_date: expiry || null }), REFRESH);
  const reject = useAct(() => api.post(`/identity/${d.id}/reject`, { reason }), REFRESH, () => setRejecting(false));
  const view = useAct(() => api.get<{ url: string }>(`/identity/${d.id}/url`), [["audit"]], (r) => window.open(r.url, "_blank", "noopener,noreferrer"));
  return (
    <li className="py-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span><span className="font-medium">{d.label}</span> · {d.filename} <span className="text-charcoal-500">· added {formatDate(d.uploaded_at)}</span></span>
        <span className="flex items-center gap-2 capitalize">{d.status}{d.status === "verified" && <DemoBadge>Demo verification</DemoBadge>}<button className="text-brand-600 hover:underline normal-case" onClick={() => view.mutate()}>Open file</button></span>
      </div>
      {d.status === "verified" && <p className="text-xs text-charcoal-600 dark:text-charcoal-300 mt-1">Verified by {d.verified_by?.full_name} on {formatDateTime(d.verified_at)} · expiry {d.expiry_date ? formatDate(d.expiry_date) : "not set"} · reused {d.reuse_count}×</p>}
      {d.status === "rejected" && <p className="text-xs text-accent-600 mt-1">Rejected: {d.rejected_reason}</p>}
      {canAct && d.status === "pending" && (
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <label className="text-xs">Expiry date<input type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} className="block h-9 rounded-md border-charcoal-300 text-sm dark:bg-charcoal-900 dark:border-charcoal-600" /></label>
          <Button size="sm" loading={verify.isPending} onClick={() => verify.mutate()}>Verify (demo)</Button>
          <Button size="sm" variant="ghost" onClick={() => setRejecting((r) => !r)}>Reject…</Button>
          {rejecting && <span className="flex gap-2"><input aria-label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason" className="h-9 rounded-md border-charcoal-300 text-sm dark:bg-charcoal-900" /><Button size="sm" variant="danger" disabled={reason.trim().length < 3} onClick={() => reject.mutate()}>Send</Button></span>}
        </div>
      )}
      {(verify.error || reject.error || view.error) ? <div className="mt-2"><ErrorBanner error={verify.error || reject.error || view.error} /></div> : null}
    </li>
  );
}

/** The client's identity vault from the adviser's side: verify or reject, see where each document was reused, add one on their behalf. */
export function IdentityTab({ clientId, canAct }: { clientId: string; canAct: boolean }) {
  const q = useGet<IdentityVault>(["identity", clientId], `/identity?client_id=${clientId}`, { refetchMs: 10000 });
  if (q.isLoading) return <Skeleton className="h-48 w-full" />;
  if (q.error) return <ErrorBanner error={q.error} onRetry={() => void q.refetch()} />;
  const v = q.data;
  if (!v) return null;
  return (
    <div className="space-y-4">
      <p className="text-xs text-charcoal-600 dark:text-charcoal-300">{v.verifier.note}</p>
      <div className="grid sm:grid-cols-3 gap-3">{TYPES.map(([t, label]) => <Card key={t} padding="sm"><p className="text-sm font-medium">{label}</p><div className="mt-1"><IdentityStateChip state={v.summary[t].state} /></div>{v.summary[t].expiry_date && <p className="text-xs text-charcoal-500 mt-1">Expires {formatDate(v.summary[t].expiry_date)}</p>}</Card>)}</div>
      <Card>
        <h3 className="font-semibold mb-1">Documents</h3>
        {v.documents.length === 0 ? <p className="text-sm text-charcoal-500">Nothing on file yet.</p> : <ul className="divide-y divide-charcoal-100 dark:divide-charcoal-700">{v.documents.map((d) => <DocRow key={d.id} d={d} canAct={canAct} />)}</ul>}
        {canAct && (
          <div className="mt-3 border-t border-charcoal-100 dark:border-charcoal-700 pt-3 space-y-2"><p className="text-sm font-medium">Add a document for this client</p>
            {TYPES.map(([t, label]) => <details key={t} className="text-sm"><summary className="cursor-pointer text-brand-600">{label}</summary><div className="mt-2"><IdentityUpload docType={t} clientId={clientId} /></div></details>)}
          </div>
        )}
      </Card>
      <Card>
        <h3 className="font-semibold mb-1">Where these were reused</h3>
        {v.reuse_log.length === 0 ? <p className="text-sm text-charcoal-500">Not reused yet.</p> : <ul className="text-sm space-y-1">{v.reuse_log.map((r) => <li key={r.id}>{formatDateTime(r.used_at)}: {r.label} used for a {r.used_for}{r.used_by ? ` (${r.used_by})` : ""}. The client was not asked again.</li>)}</ul>}
      </Card>
    </div>
  );
}
