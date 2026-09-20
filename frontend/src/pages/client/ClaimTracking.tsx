import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Star } from "lucide-react";
import { Button, ClaimStatusStepper, ErrorBanner, PageHeader, Skeleton, Card } from "@/components/ui";
import { Timeline } from "@/components/workflow/Timeline";
import { api } from "@/lib/api";
import { useAct, useGet } from "@/lib/hooks";
import { formatDate, formatDateTime, formatZAR } from "@/lib/utils";
import type { Claim } from "@/lib/types";

/**
 * The client's live claim: the same record and the same timeline the adviser sees. It re-reads every 5 seconds, so a status change
 * made by the adviser (or the simulated insurer) appears here by itself, with no WhatsApp and no calling to ask.
 */
export default function ClaimTracking() {
  const { id } = useParams();
  const q = useGet<Claim>(["claim", id], `/claims/${id}`, { refetchMs: 5000, enabled: !!id });
  const [date, setDate] = useState("");
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const chooseDate = useAct((d: string) => api.post(`/claims/${id}/repair-date`, { drop_off_date: d }), [["claim", id!]]);
  const review = useAct(() => api.post(`/claims/${id}/review`, { rating, comment: comment.trim() || null }), [["claim", id!], ["dashboard"]]);

  if (q.isLoading) return <Skeleton className="h-96 w-full" />;
  if (q.error) return <ErrorBanner error={q.error} onRetry={() => void q.refetch()} />;
  const c = q.data;
  if (!c) return null;
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="p-4 md:p-8 space-y-6 max-w-5xl">
      <PageHeader
        title={`Claim ${c.reference ?? "(draft)"}`}
        subtitle={<>{c.insurer?.name ?? "Insurer not set"} · <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-success animate-pulse" aria-hidden="true" />Live: updates appear by themselves</span></>}
      />
      <Card><ClaimStatusStepper currentStatus={c.status} /><p className="mt-4 text-lg font-semibold text-charcoal-900 dark:text-white">{c.status_label}</p></Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <h2 className="font-semibold text-charcoal-900 dark:text-white mb-2">Your insurer</h2>
          <p className="text-sm text-charcoal-500">Claim number</p><p className="font-medium">{c.insurer_details?.claim_number ?? "Not issued yet"}</p>
          {c.insurer_details?.handler_name && <><p className="text-sm text-charcoal-500 mt-2">Claims handler</p><p className="font-medium">{c.insurer_details.handler_name}</p></>}
        </Card>
        <Card>
          <h2 className="font-semibold text-charcoal-900 dark:text-white mb-2">Repair</h2>
          <p className="text-sm text-charcoal-500">Repairer</p><p className="font-medium">{c.repair?.repairer_name ?? "Not arranged yet"}</p>
          {c.repair?.authorised_amount_cents != null && <><p className="text-sm text-charcoal-500 mt-2">Authorised</p><p className="font-medium">{formatZAR(c.repair.authorised_amount_cents)}</p></>}
          {c.repair?.drop_off_date && <><p className="text-sm text-charcoal-500 mt-2">Vehicle goes in</p><p className="font-medium">{formatDate(c.repair.drop_off_date)}</p></>}
          {c.hire_car?.status !== "not_required" && <><p className="text-sm text-charcoal-500 mt-2">Hire car</p><p className="font-medium capitalize">{c.hire_car.status.replace(/_/g, " ")}</p></>}
        </Card>
        <Card>
          <h2 className="font-semibold text-charcoal-900 dark:text-white mb-2">Police</h2>
          <p className="text-sm text-charcoal-500">Case number</p><p className="font-medium">{c.police?.case_number ?? "Not recorded"}</p>
          <p className="text-sm text-charcoal-500 mt-2">Submitted</p><p className="font-medium">{formatDateTime(c.submitted_at ?? c.created_at)}</p>
        </Card>
      </div>

      {c.status === "authorised" && !c.repair?.drop_off_date && (
        <Card>
          <h2 className="font-semibold text-charcoal-900 dark:text-white">Your repairs are approved. Pick a date for the vehicle to go in.</h2>
          <form className="mt-3 flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); if (date) chooseDate.mutate(date); }}>
            <label className="text-sm"><span className="block font-medium mb-1">Drop-off date</span><input type="date" min={today} value={date} onChange={(e) => setDate(e.target.value)} className="rounded-md border-charcoal-300 dark:bg-charcoal-900 dark:border-charcoal-600" /></label>
            <Button type="submit" disabled={!date} loading={chooseDate.isPending}>Confirm date</Button>
          </form>
          {chooseDate.error ? <div className="mt-3"><ErrorBanner error={chooseDate.error} /></div> : null}
        </Card>
      )}

      {c.status === "completed" && !c.review && (
        <Card>
          <h2 className="font-semibold text-charcoal-900 dark:text-white">Repairs are finished. How did we do?</h2>
          <div className="mt-3 flex gap-1" role="radiogroup" aria-label="Rating">
            {[1, 2, 3, 4, 5].map((n) => (
              <button key={n} type="button" role="radio" aria-checked={rating === n} aria-label={`${n} star${n === 1 ? "" : "s"}`} onClick={() => setRating(n)} className="p-1">
                <Star className={`w-7 h-7 ${n <= rating ? "fill-amber-400 text-amber-500" : "text-charcoal-300"}`} aria-hidden="true" />
              </button>
            ))}
          </div>
          <label className="block mt-3 text-sm"><span className="font-medium">A short comment (optional)</span><textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={3} maxLength={1000} className="mt-1 w-full rounded-md border-charcoal-300 dark:bg-charcoal-900 dark:border-charcoal-600" /></label>
          <div className="mt-3"><Button disabled={rating === 0} loading={review.isPending} onClick={() => review.mutate()}>Sign off and close the claim</Button></div>
          {review.error ? <div className="mt-3"><ErrorBanner error={review.error} /></div> : null}
        </Card>
      )}

      <Card>
        <h2 className="font-semibold text-charcoal-900 dark:text-white mb-4">What has happened so far</h2>
        <Timeline events={c.timeline ?? []} />
      </Card>

      {c.attachments?.length > 0 && (
        <Card>
          <h2 className="font-semibold text-charcoal-900 dark:text-white mb-2">Your documents</h2>
          <ul className="text-sm space-y-1">{c.attachments.map((a) => <li key={a.id}><a className="text-brand-600 dark:text-brand-300 hover:underline" href={a.url} target="_blank" rel="noreferrer">{a.label ?? a.filename}</a></li>)}</ul>
        </Card>
      )}
      <p className="text-sm"><Link to="/dashboard" className="text-brand-600 hover:underline">Back to my dashboard</Link></p>
    </div>
  );
}
