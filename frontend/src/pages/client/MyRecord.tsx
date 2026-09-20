import React from "react";
import { Link } from "react-router-dom";
import { Button, Card, ErrorBanner, PageHeader, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { useAct, useGet } from "@/lib/hooks";
import { formatDate, formatDateTime } from "@/lib/utils";
import type { AdviceRecord, ConsentPurpose, ConsentState, TimelineItem } from "@/lib/typesExt";

const REFRESH = [["my-consents"], ["my-advice"], ["my-timeline"], ["notifications"]];

/** What the client can see and control about their own record: consents, advice records to confirm, and their history. */
export default function MyRecord() {
  const consents = useGet<ConsentState>(["my-consents"], "/consents");
  const advice = useGet<{ items: AdviceRecord[] }>(["my-advice"], "/advice-records", { refetchMs: 10000 });
  const tl = useGet<{ items: TimelineItem[] }>(["my-timeline"], "/me/timeline", { refetchMs: 10000 });
  const set = useAct((v: { purpose: ConsentPurpose; status: "granted" | "withdrawn" }) => api.post("/consents", { ...v, method: "in_app" }), REFRESH);
  const ack = useAct((id: string) => api.post(`/advice-records/${id}/acknowledge`, {}), REFRESH);

  if (consents.isLoading || advice.isLoading) return <Skeleton className="h-96 w-full" />;
  if (consents.error) return <ErrorBanner error={consents.error} onRetry={() => void consents.refetch()} />;
  const c = consents.data;
  const records = advice.data?.items ?? [];

  return (
    <div className="p-4 md:p-8 max-w-3xl space-y-6">
      <PageHeader title="My record" subtitle="Your consents, the summaries your adviser has recorded, and everything that has happened on your account." />
      <Card>
        <h2 className="font-semibold text-charcoal-900 dark:text-white">Your consents</h2>
        <p className="text-xs text-charcoal-500 mt-1">You can change these at any time. Privacy notice {c?.notice_version}{c?.notice_is_draft ? " (draft for legal review)" : ""}. <Link to="/privacy" className="text-brand-600 hover:underline">Read how your data is handled</Link>.</p>
        <ul className="mt-2 divide-y divide-charcoal-100 dark:divide-charcoal-700 text-sm">
          {c && (Object.keys(c.purposes) as ConsentPurpose[]).map((p) => {
            const cur = c.current[p];
            const on = cur?.status === "granted";
            return (
              <li key={p} className="py-3 flex flex-wrap items-center justify-between gap-3">
                <span className="max-w-md"><span className="font-medium capitalize">{p.replace("_", " ")}</span><span className="block text-charcoal-600 dark:text-charcoal-300">{c.purposes[p]}</span>{cur && <span className="block text-xs text-charcoal-500">{on ? "Granted" : "Withdrawn"} on {formatDate(cur.recorded_at)}</span>}</span>
                <Button size="sm" variant={on ? "secondary" : "primary"} loading={set.isPending} onClick={() => set.mutate({ purpose: p, status: on ? "withdrawn" : "granted" })}>{on ? "Withdraw" : "Give consent"}</Button>
              </li>
            );
          })}
        </ul>
        {set.error ? <div className="mt-2"><ErrorBanner error={set.error} /></div> : null}
      </Card>
      <Card>
        <h2 className="font-semibold text-charcoal-900 dark:text-white">Summaries of your meetings</h2>
        {records.length === 0 ? <p className="mt-2 text-sm text-charcoal-500">Nothing recorded yet.</p> : (
          <ul className="mt-2 divide-y divide-charcoal-100 dark:divide-charcoal-700">
            {records.map((r) => (
              <li key={r.id} className="py-3 text-sm space-y-1">
                <p className="font-medium capitalize">{r.interaction_type.replace("_", " ")} · {formatDateTime(r.created_at)} · {r.adviser.full_name}</p>
                <p className="text-charcoal-700 dark:text-charcoal-300">{r.final_summary}</p>
                {r.client_acknowledged ? <p className="text-xs text-green-700">You confirmed this summary.</p> : <Button size="sm" loading={ack.isPending} onClick={() => ack.mutate(r.id)}>This is correct: confirm</Button>}
              </li>
            ))}
          </ul>
        )}
        {ack.error ? <div className="mt-2"><ErrorBanner error={ack.error} /></div> : null}
      </Card>
      <Card>
        <h2 className="font-semibold text-charcoal-900 dark:text-white mb-3">What has happened on your account</h2>
        {tl.isLoading && <Skeleton lines={3} />}
        {tl.data && tl.data.items.length === 0 && <p className="text-sm text-charcoal-500">Nothing yet.</p>}
        <ol className="relative border-l-2 border-charcoal-200 dark:border-charcoal-700 ml-2 space-y-3">{(tl.data?.items ?? []).slice(0, 30).map((e) => (
          <li key={e.id} className="pl-4 relative"><span className="absolute -left-[7px] top-1.5 w-3 h-3 rounded-full bg-brand-500" aria-hidden="true" /><p className="text-sm text-charcoal-900 dark:text-white">{e.summary}</p><p className="text-xs text-charcoal-500">{e.actor.full_name ?? "System"} · {formatDateTime(e.occurred_at)}</p></li>))}</ol>
      </Card>
    </div>
  );
}
