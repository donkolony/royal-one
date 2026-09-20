import React, { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, ListTodo, MailPlus, Moon, ThumbsDown, ThumbsUp, Undo2 } from "lucide-react";
import { Button, DemoBadge, ErrorBanner, InfoPopover } from "../ui";
import { api } from "../../lib/api";
import { useAct } from "../../lib/hooks";
import { formatDate, formatRand0, relativeTime } from "../../lib/utils";
import { evidenceFacts, SIGNAL_TONE } from "./format";
import { OutreachModal } from "./OutreachModal";
import { OutcomeModal } from "./OutcomeModal";
import type { Opportunity } from "../../lib/typesExt";

interface Props {
  opportunity: Opportunity;
  base: string;
  /** Only the client's adviser can act. The owner sees the same card, read-only. */
  canAct: boolean;
}

const REFRESH = [["opportunities"], ["opp-summary"], ["business-health"], ["audit"], ["client-opps"]];
const LIVE = new Set(["open", "actioned"]);

export function OpportunityCard({ opportunity: o, base, canAct }: Props) {
  const [drafting, setDrafting] = useState(false);
  const [outcome, setOutcome] = useState<"won" | "lost" | null>(null);
  const [showPoints, setShowPoints] = useState(false);
  const facts = evidenceFacts(o.evidence);
  const live = LIVE.has(o.status);
  const id = o.id;

  const task = useAct(() => api.post(`/opportunities/${id}/task`), REFRESH);
  const snooze = useAct((days: number) => api.post(`/opportunities/${id}/snooze`, { days }), REFRESH);
  const reopen = useAct(() => api.post(`/opportunities/${id}/reopen`), REFRESH);
  const sent = useAct(
    (v: { channel: "email" | "whatsapp"; note: string }) => api.post(`/opportunities/${id}/outreach`, v),
    REFRESH,
    () => setDrafting(false),
  );
  const decide = useAct(
    (v: { outcome: "won" | "lost"; reason: string; actual: number | null }) =>
      api.post(`/opportunities/${id}/outcome`, { outcome: v.outcome, reason: v.reason, actual_annual_value_cents: v.actual === null ? null : v.actual * 100 }),
    REFRESH,
    () => setOutcome(null),
  );
  const err = task.error || snooze.error || reopen.error || sent.error || decide.error;

  return (
    <article className="rounded-lg border border-charcoal-100 dark:border-charcoal-700 bg-white dark:bg-charcoal-800 shadow-sm p-4 sm:p-5" aria-label={o.title}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${SIGNAL_TONE[o.signal] ?? ""}`}>{o.signal_label}</span>
          {o.status !== "open" && (
            <span className="rounded-full bg-charcoal-100 dark:bg-charcoal-700 px-2 py-0.5 text-xs font-medium capitalize text-charcoal-700 dark:text-charcoal-200">
              {o.status === "snoozed" && o.snoozed_until ? `Snoozed until ${formatDate(o.snoozed_until)}` : o.status}
            </span>
          )}
        </div>
        <div className="text-right">
          {o.is_touchpoint ? (
            <p className="text-sm font-semibold text-charcoal-600 dark:text-charcoal-300">Touchpoint</p>
          ) : (
            <p className="text-xl font-bold tabular-nums text-charcoal-900 dark:text-white">
              {formatRand0(o.est_annual_value_cents)}<span className="text-xs font-medium text-charcoal-500"> / year</span>
            </p>
          )}
          <DemoBadge />
        </div>
      </div>

      <h3 className="mt-2 text-lg font-semibold text-charcoal-900 dark:text-white">{o.title}</h3>
      <p className="text-sm text-charcoal-600 dark:text-charcoal-300">
        <Link to={`${base}/clients/${o.client.id}`} className="font-medium text-brand-600 dark:text-brand-300 hover:underline">{o.client.full_name}</Link>
        {" · "}{o.adviser.full_name}{" · surfaced "}{relativeTime(o.surfaced_at)}
      </p>
      <p className="mt-2 text-sm text-charcoal-700 dark:text-charcoal-200">{o.why_now}</p>

      {facts.length > 0 && (
        <dl className="mt-3 flex flex-wrap gap-2" aria-label="Evidence">
          {facts.map((f) => (
            <div key={f.label} className="rounded-md bg-charcoal-50 dark:bg-charcoal-900 px-2.5 py-1.5">
              <dt className="text-[11px] uppercase tracking-wide text-charcoal-500 dark:text-charcoal-400">{f.label}</dt>
              <dd className="text-sm font-semibold tabular-nums text-charcoal-900 dark:text-white">{f.value}</dd>
            </div>
          ))}
        </dl>
      )}

      <div className="mt-3 rounded-md border-l-4 border-brand-500 bg-brand-50/60 dark:bg-brand-900/20 px-3 py-2 text-sm text-charcoal-800 dark:text-charcoal-100">
        <span className="font-semibold">Next action: </span>{o.suggested_action}
      </div>

      {o.talking_points.length > 0 && (
        <div className="mt-2">
          <button type="button" className="text-xs text-brand-600 dark:text-brand-300 hover:underline" aria-expanded={showPoints} onClick={() => setShowPoints((s) => !s)}>
            {showPoints ? "Hide talking points" : `Talking points (${o.talking_points.length})`}
          </button>
          {showPoints && <ul className="mt-1 list-disc pl-5 text-sm text-charcoal-700 dark:text-charcoal-300 space-y-0.5">{o.talking_points.map((t) => <li key={t}>{t}</li>)}</ul>}
        </div>
      )}

      <div className="mt-3">
        <InfoPopover>
          <p><span className="font-semibold">Estimate:</span> {o.value_formula}.</p>
          <p className="mt-1">Assumptions are placeholders shown on the Opportunities page ("Assumptions"). They are not real commission rates or premiums.</p>
        </InfoPopover>
      </div>

      {err ? <div className="mt-3"><ErrorBanner error={err} /></div> : null}

      {!live && (
        <p className="mt-3 text-sm text-charcoal-600 dark:text-charcoal-300">
          {o.status === "won" && <CheckCircle2 className="inline w-4 h-4 mr-1 text-success" aria-hidden="true" />}
          {o.outcome_reason ? <>Outcome: {o.outcome_reason}. </> : null}
          {o.status === "won" && o.won_value_cents !== null ? <>Recorded value {formatRand0(o.won_value_cents)} a year. </> : null}
          {o.closed_at ? <>Closed {relativeTime(o.closed_at)}.</> : null}
        </p>
      )}

      {canAct && (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          {live && (
            <>
              <Button size="sm" variant="secondary" onClick={() => task.mutate()} loading={task.isPending} disabled={!!o.task_reminder_id}>
                <ListTodo className="w-4 h-4 mr-1.5" aria-hidden="true" />{o.task_reminder_id ? "Task created" : "Create task"}
              </Button>
              <Button size="sm" onClick={() => setDrafting(true)}><MailPlus className="w-4 h-4 mr-1.5" aria-hidden="true" />Draft outreach</Button>
              {o.status === "open" && (
                <label className="inline-flex items-center gap-1 text-sm text-charcoal-600 dark:text-charcoal-300">
                  <Moon className="w-4 h-4" aria-hidden="true" />
                  <span className="sr-only">Snooze for</span>
                  <select aria-label="Snooze" className="h-8 rounded-md border-charcoal-300 py-0 text-sm dark:bg-charcoal-900 dark:border-charcoal-600" value="" onChange={(e) => e.target.value && snooze.mutate(Number(e.target.value))}>
                    <option value="">Snooze…</option>
                    <option value="3">3 days</option>
                    <option value="7">1 week</option>
                    <option value="30">30 days</option>
                  </select>
                </label>
              )}
              <span className="grow" />
              <Button size="sm" variant="ghost" onClick={() => setOutcome("won")}><ThumbsUp className="w-4 h-4 mr-1.5" aria-hidden="true" />Won</Button>
              <Button size="sm" variant="ghost" onClick={() => setOutcome("lost")}><ThumbsDown className="w-4 h-4 mr-1.5" aria-hidden="true" />Lost</Button>
            </>
          )}
          {["lost", "expired", "snoozed"].includes(o.status) && (
            <Button size="sm" variant="secondary" onClick={() => reopen.mutate()} loading={reopen.isPending}><Undo2 className="w-4 h-4 mr-1.5" aria-hidden="true" />Reopen</Button>
          )}
        </div>
      )}

      {canAct && (
        <>
          <OutreachModal opportunity={o} open={drafting} onClose={() => setDrafting(false)} onSent={(channel, note) => sent.mutate({ channel, note })} />
          {outcome && <OutcomeModal opportunity={o} outcome={outcome} open onClose={() => setOutcome(null)} saving={decide.isPending} onSave={(oc, reason, actual) => decide.mutate({ outcome: oc, reason, actual })} />}
        </>
      )}
    </article>
  );
}
