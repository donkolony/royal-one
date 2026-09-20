import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Button, PageHeader, Skeleton, ErrorBanner, EmptyState, StatusPill, DemoBadge } from "@/components/ui";
import { Timeline } from "@/components/workflow/Timeline";
import { api } from "@/lib/api";
import { useAct, useGet } from "@/lib/hooks";
import { useMeta } from "@/lib/meta";
import { useStaffBase } from "@/lib/staff";
import { formatDate, humanize, itemsOf } from "@/lib/utils";
import type { Page } from "@/lib/types";
import type { RequestItem } from "@/lib/typesExt";

const FILTERS: [string, string][] = [["open", "Open"], ["completed", "Completed"], ["all", "All"]];

/** The adviser's queue: one screen per request, status buttons from the workflow config, and the same timeline the client sees. */
export default function AdvisorRequests() {
  const base = useStaffBase();
  const [filter, setFilter] = useState("open");
  const [open, setOpen] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const { data: meta } = useMeta();
  const qs = filter === "open" ? "&open=true" : filter === "all" ? "" : `&status=${filter}`;
  const list = useGet<Page<RequestItem>>(["requests", filter], `/requests?limit=50${qs}`, { refetchMs: 8000 });
  const detail = useGet<RequestItem>(["request", open], `/requests/${open}`, { enabled: !!open, refetchMs: 6000 });

  const move = useAct((v: { id: string; status?: string; response?: string }) =>
    api.patch(`/requests/${v.id}`, { ...(v.status ? { status: v.status } : {}), ...(v.response ? { adviser_response: v.response } : {}) }),
    [["requests"], ["request"], ["notifications"], ["advisorDashboard"]], () => setReply(""));
  const provider = useAct((id: string) => api.post("/demo/insurer-step", { request_id: id }), [["requests"], ["request"], ["notifications"]]);

  const items = itemsOf(list.data);
  return (
    <div className="max-w-4xl">
      <PageHeader title="Requests" subtitle="Client requests, newest first. Anything you change appears on the client's screen within seconds." />
      <div role="tablist" aria-label="Filter" className="inline-flex rounded-md border border-charcoal-200 dark:border-charcoal-600 p-0.5 mb-4">
        {FILTERS.map(([v, l]) => <button key={v} role="tab" aria-selected={filter === v} onClick={() => setFilter(v)} className={`px-3 py-1.5 text-sm rounded ${filter === v ? "bg-brand-500 text-white" : "text-charcoal-600 dark:text-charcoal-300"}`}>{l}</button>)}
      </div>
      {list.isLoading && <Skeleton className="h-64 w-full" />}
      {list.error ? <ErrorBanner error={list.error} onRetry={() => void list.refetch()} /> : null}
      {!list.isLoading && items.length === 0 && <EmptyState title="Nothing in this list" description="New requests from clients appear here by themselves." />}
      <div className="space-y-3">
        {items.map((r) => {
          const isOpen = open === r.id;
          const terminal = r.status === "completed" || r.status === "declined";
          return (
            <article key={r.id} className="rounded-lg border border-charcoal-100 dark:border-charcoal-700 bg-white dark:bg-charcoal-800 shadow-sm">
              <button className="w-full text-left p-4 flex flex-wrap items-center justify-between gap-2" aria-expanded={isOpen} onClick={() => { setOpen(isOpen ? null : r.id); setReply(""); }}>
                <span>
                  <span className="block font-semibold text-charcoal-900 dark:text-white">{r.type_label}</span>
                  <span className="block text-sm text-charcoal-600 dark:text-charcoal-300">{r.client.full_name} · sent {formatDate(r.submitted_at)}</span>
                </span>
                <span className="flex items-center gap-3"><StatusPill status={r.status} />{isOpen ? <ChevronUp className="w-4 h-4" aria-hidden="true" /> : <ChevronDown className="w-4 h-4" aria-hidden="true" />}</span>
              </button>
              {isOpen && (
                <div className="border-t border-charcoal-100 dark:border-charcoal-700 p-4 space-y-4">
                  <dl className="grid sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
                    {Object.entries(r.payload).map(([k, v]) => (
                      <div key={k}><dt className="text-xs uppercase tracking-wide text-charcoal-500">{humanize(k)}</dt><dd className="text-charcoal-900 dark:text-white break-words">{Array.isArray(v) ? v.map((x) => (typeof x === "object" ? JSON.stringify(x) : String(x))).join(", ") : String(v ?? "")}</dd></div>
                    ))}
                  </dl>
                  {r.client_note && <p className="text-sm rounded bg-charcoal-50 dark:bg-charcoal-900 p-3"><span className="font-semibold">Client note: </span>{r.client_note}</p>}
                  <p className="text-sm"><Link to={`${base}/clients/${r.client.id}`} className="text-brand-600 dark:text-brand-300 hover:underline">Open {r.client.full_name}</Link></p>
                  <Timeline events={detail.data?.timeline ?? []} />
                  {!terminal && (
                    <div className="space-y-2">
                      <label className="block text-sm"><span className="font-medium">Reply to the client (required to decline)</span>
                        <textarea value={reply} onChange={(e) => setReply(e.target.value)} rows={2} maxLength={2000} className="mt-1 w-full rounded-md border-charcoal-300 dark:bg-charcoal-900 dark:border-charcoal-600 text-sm" /></label>
                      <div className="flex flex-wrap gap-2">
                        {r.status === "submitted" && <Button size="sm" variant="secondary" loading={move.isPending} onClick={() => move.mutate({ id: r.id, status: "in_progress", response: reply })}>Start work</Button>}
                        <Button size="sm" loading={move.isPending} onClick={() => move.mutate({ id: r.id, status: "completed", response: reply })}>Mark completed</Button>
                        <Button size="sm" variant="danger" disabled={reply.trim().length < 3} onClick={() => move.mutate({ id: r.id, status: "declined", response: reply })}>Decline</Button>
                        {reply.trim() && <Button size="sm" variant="ghost" onClick={() => move.mutate({ id: r.id, response: reply })}>Send reply only</Button>}
                        {meta?.demo_mode && r.insurer_forward && <Button size="sm" variant="ghost" loading={provider.isPending} onClick={() => provider.mutate(r.id)}>Demo: simulate provider <DemoBadge>Demo</DemoBadge></Button>}
                      </div>
                      {(move.error || provider.error) ? <ErrorBanner error={move.error || provider.error} /> : null}
                    </div>
                  )}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
