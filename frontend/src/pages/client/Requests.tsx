import React, { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Modal, PageHeader, Skeleton, ErrorBanner, EmptyState, StatusPill } from "@/components/ui";
import { WorkflowForm } from "@/components/workflow/WorkflowForm";
import { Timeline } from "@/components/workflow/Timeline";
import { api } from "@/lib/api";
import { useAct, useGet } from "@/lib/hooks";
import { formatDate, itemsOf } from "@/lib/utils";
import type { Page } from "@/lib/types";
import type { RequestItem, RequestTypeDef } from "@/lib/typesExt";

const STEPS = [["submitted", "Received"], ["in_progress", "In progress"], ["completed", "Done"]] as const;

/**
 * Client requests. The forms are rendered from the workflow definitions the API serves, so a new request type needs no new
 * screen. The list refreshes every few seconds: when the adviser (or the provider) moves a request, the client sees it happen.
 */
export default function Requests() {
  const [picked, setPicked] = useState<RequestTypeDef | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);

  const types = useGet<{ items: RequestTypeDef[] }>(["request-types"], "/requests/types");
  const list = useGet<Page<RequestItem>>(["requests"], "/requests?limit=50", { refetchMs: 8000 });
  const policies = useGet<Page<{ id: string; product_name: string; policy_number: string; category: string }>>(["policies-lite"], "/policies?limit=100");
  const detail = useGet<RequestItem>(["request", open], `/requests/${open}`, { enabled: !!open, refetchMs: 6000 });

  const create = useAct(
    (v: { type: string; payload: Record<string, unknown>; note: string }) => api.post<RequestItem>("/requests", { type: v.type, payload: v.payload, client_note: v.note || null }),
    [["requests"], ["notifications"]],
    (r) => { setSent(r.type_label); setPicked(null); setOpen(r.id); },
  );

  if (types.isLoading || list.isLoading) return <Skeleton className="h-96 w-full" />;
  if (types.error) return <ErrorBanner error={types.error} onRetry={() => void types.refetch()} />;
  const requests = itemsOf(list.data);

  return (
    <div className="p-4 md:p-8 space-y-8 max-w-4xl">
      <PageHeader title="Requests" subtitle="Ask for a document, change your details or book time with your adviser. You will see every step here, so there is no need to chase." />
      {sent && <p role="status" className="rounded-md bg-green-50 dark:bg-green-900/30 text-green-900 dark:text-green-100 px-4 py-3 text-sm">Sent: {sent}. Your adviser has been told, and updates will appear below.</p>}

      <section aria-labelledby="start" className="space-y-3">
        <h2 id="start" className="text-lg font-semibold text-charcoal-900 dark:text-white">Start a request</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {itemsOf(types.data).map((t) => (
            <button key={t.type} onClick={() => { setPicked(t); setSent(null); create.reset(); }} className="text-left rounded-lg border border-charcoal-200 dark:border-charcoal-700 bg-white dark:bg-charcoal-800 p-4 hover:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500">
              <span className="block font-semibold text-charcoal-900 dark:text-white">{t.label}</span>
              <span className="block text-sm text-charcoal-600 dark:text-charcoal-300 mt-0.5">{t.description}</span>
              <span className="block text-xs text-charcoal-500 mt-2">Usually within {t.sla_days} working day{t.sla_days === 1 ? "" : "s"}{t.insurer_forward ? " · passed to your provider (demo)" : ""}</span>
            </button>
          ))}
        </div>
      </section>

      <section aria-labelledby="mine" className="space-y-3">
        <h2 id="mine" className="text-lg font-semibold text-charcoal-900 dark:text-white">Your requests</h2>
        {list.error ? <ErrorBanner error={list.error} onRetry={() => void list.refetch()} /> : null}
        {requests.length === 0 && <EmptyState title="No requests yet" description="Pick one above to get started." />}
        {requests.map((r) => {
          const isOpen = open === r.id;
          const idx = STEPS.findIndex(([s]) => s === r.status);
          return (
            <article key={r.id} className="rounded-lg border border-charcoal-100 dark:border-charcoal-700 bg-white dark:bg-charcoal-800 shadow-sm">
              <button className="w-full text-left p-4 flex flex-wrap items-center justify-between gap-2" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : r.id)}>
                <span>
                  <span className="block font-semibold text-charcoal-900 dark:text-white">{r.type_label}</span>
                  <span className="block text-xs text-charcoal-500">Sent {formatDate(r.submitted_at)}</span>
                </span>
                <span className="flex items-center gap-3"><StatusPill status={r.status} label={r.status === "submitted" ? "Received" : undefined} />{isOpen ? <ChevronUp className="w-4 h-4" aria-hidden="true" /> : <ChevronDown className="w-4 h-4" aria-hidden="true" />}</span>
              </button>
              {r.status !== "declined" && (
                <ol className="flex px-4 pb-3 gap-1" aria-label="Progress">
                  {STEPS.map(([s, label], i) => <li key={s} className={`flex-1 text-center text-[11px] py-1 rounded ${i <= idx ? "bg-brand-500 text-white" : "bg-charcoal-100 dark:bg-charcoal-700 text-charcoal-500"}`}>{label}</li>)}
                </ol>
              )}
              {r.adviser_response && <p className="mx-4 mb-3 rounded bg-charcoal-50 dark:bg-charcoal-900 border-l-4 border-brand-500 p-3 text-sm"><span className="font-semibold">Your adviser: </span>{r.adviser_response}</p>}
              {isOpen && (
                <div className="border-t border-charcoal-100 dark:border-charcoal-700 p-4">
                  {detail.isLoading ? <Skeleton lines={3} /> : <Timeline events={detail.data?.timeline ?? []} />}
                </div>
              )}
            </article>
          );
        })}
      </section>

      <Modal open={!!picked} onClose={() => setPicked(null)} title={picked?.label ?? ""} size="lg">
        {picked && (
          <WorkflowForm workflow={picked} policies={itemsOf(policies.data)} submitting={create.isPending} error={create.error}
            onSubmit={(payload, note) => create.mutate({ type: picked.type, payload, note })} onCancel={() => setPicked(null)} />
        )}
      </Modal>
    </div>
  );
}
