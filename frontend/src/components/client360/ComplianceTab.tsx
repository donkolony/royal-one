import React, { useState } from "react";
import { Download } from "lucide-react";
import { Button, Card, DemoBadge, ErrorBanner, Skeleton } from "../ui";
import { AdviceModal } from "./AdviceModal";
import { api, download } from "../../lib/api";
import { useAct, useGet } from "../../lib/hooks";
import { formatDate, formatDateTime } from "../../lib/utils";
import type { AdviceRecord, ConsentPurpose, ConsentState } from "../../lib/typesExt";

const REFRESH = (id: string) => [["client-compliance", id], ["client-timeline", id], ["business-health"], ["compliance-overview"], ["client-health", id], ["audit"], ["notifications"]];

/** Consents, advice records and the compliance pack for one client. The owner sees them; only the client's adviser can record. */
export function ComplianceTab({ clientId, clientName, canAct }: { clientId: string; clientName: string; canAct: boolean }) {
  const consents = useGet<ConsentState>(["client-compliance", clientId, "consents"], `/consents?client_id=${clientId}`);
  const advice = useGet<{ items: AdviceRecord[] }>(["client-compliance", clientId, "advice"], `/advice-records?client_id=${clientId}`);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const setConsent = useAct((v: { purpose: ConsentPurpose; status: "granted" | "withdrawn" }) => api.post("/consents", { ...v, method: "in_person", client_id: clientId }), REFRESH(clientId));
  const ackRec = useAct((id: string) => api.post(`/advice-records/${id}/acknowledge`, { method: "verbal" }), REFRESH(clientId));
  const dl = async (kind: "pdf" | "csv") => { setBusy(kind); setErr(null); try { await (kind === "pdf" ? download(`/clients/${clientId}/compliance/pack.pdf`, "compliance-pack.pdf") : download(`/audit/export?client_id=${clientId}`, "audit-log-client.csv")); } catch (e) { setErr(e); } finally { setBusy(null); } };

  if (consents.isLoading || advice.isLoading) return <Skeleton className="h-48 w-full" />;
  if (consents.error || advice.error) return <ErrorBanner error={consents.error || advice.error} />;
  const c = consents.data, records = advice.data?.items ?? [];
  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold">Regulator or insurer request</h3>
          <div className="flex gap-2"><Button size="sm" loading={busy === "pdf"} onClick={() => void dl("pdf")}><Download className="w-4 h-4 mr-1.5" aria-hidden="true" />Compliance pack (PDF)</Button><Button size="sm" variant="secondary" loading={busy === "csv"} onClick={() => void dl("csv")}>Audit log (CSV)</Button></div></div>
        <p className="text-sm text-charcoal-600 dark:text-charcoal-300 mt-1">Identity, advice, consent, claims and access history in one timestamped pack. Each export is logged.</p>
        {err ? <div className="mt-2"><ErrorBanner error={err} /></div> : null}
      </Card>

      <Card>
        <h3 className="font-semibold">Consents</h3>
        {c && <p className="text-xs text-charcoal-500 mt-1">Privacy notice {c.notice_version}{c.notice_is_draft ? " (draft for legal review)" : ""}. History is append-only.</p>}
        <ul className="mt-2 divide-y divide-charcoal-100 dark:divide-charcoal-700 text-sm">
          {c && (Object.keys(c.purposes) as ConsentPurpose[]).map((p) => {
            const cur = c.current[p];
            return (
              <li key={p} className="py-2 flex flex-wrap items-center justify-between gap-2">
                <span><span className="font-medium capitalize">{p.replace("_", " ")}</span><span className="block text-xs text-charcoal-500">{c.purposes[p]}</span></span>
                <span className="flex items-center gap-2"><span className={`font-semibold ${cur?.status === "granted" ? "text-green-700" : "text-accent-600"}`}>{cur ? `${cur.status === "granted" ? "Granted" : "Withdrawn"} ${formatDate(cur.recorded_at)}` : "Not recorded"}</span>
                  {canAct && <><Button size="sm" variant="secondary" onClick={() => setConsent.mutate({ purpose: p, status: "granted" })} disabled={cur?.status === "granted"}>Record granted</Button><Button size="sm" variant="ghost" onClick={() => setConsent.mutate({ purpose: p, status: "withdrawn" })} disabled={cur?.status === "withdrawn"}>Record withdrawn</Button></>}</span>
              </li>
            );
          })}
        </ul>
        {setConsent.error ? <div className="mt-2"><ErrorBanner error={setConsent.error} /></div> : null}
      </Card>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold">Advice records</h3>{canAct && <Button size="sm" onClick={() => setOpen(true)}>Record advice</Button>}</div>
        {records.length === 0 ? <p className="text-sm text-charcoal-500 mt-2">No advice record on file.</p> : (
          <ul className="mt-2 divide-y divide-charcoal-100 dark:divide-charcoal-700">
            {records.map((r) => (
              <li key={r.id} className="py-3 text-sm space-y-1">
                <p className="font-medium capitalize">{r.interaction_type.replace("_", " ")} · {formatDateTime(r.created_at)} · {r.adviser.full_name}</p>
                <p className="text-charcoal-700 dark:text-charcoal-300">{r.final_summary}</p>
                <p className="text-xs text-charcoal-500">{r.draft_source ? `Drafted (${r.draft_source === "ai" ? "AI-polished" : "standard wording"})${r.edited_from_draft ? ", edited" : ", unedited"}, then approved by the adviser. ` : "Written by the adviser. "}
                  {r.client_acknowledged ? `Acknowledged by the client (${r.acknowledgement_method?.replace("_", " ")}).` : <span className="text-amber-700">Not yet acknowledged by the client.{canAct && <button className="ml-2 text-brand-600 hover:underline" onClick={() => ackRec.mutate(r.id)}>Record verbal acknowledgement</button>}</span>}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>
      {canAct && <AdviceModal clientId={clientId} clientName={clientName} open={open} onClose={() => setOpen(false)} />}
      <p className="text-xs text-charcoal-500"><DemoBadge>Demo data</DemoBadge> All records here are synthetic.</p>
    </div>
  );
}
