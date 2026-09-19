import React, { useState } from "react";
import {
  Badge, Button, Card, ClaimStatusStepper, EmptyState, ErrorBanner, GoalCard, Modal, NetWorthCard, ProgressBar,
  ReminderRow, Skeleton, Spinner, StatusPill,
} from "../ui";
import { ApiError } from "../../lib/errors";
import { formatDate, formatDateTime, formatZAR, randsToCents } from "../../lib/utils";
import type { Goal, NetWorth, Reminder } from "../../lib/types";

const goal: Goal = {
  id: "g1", title: "Children's university fund", description: "Shared goal for the household", category: "education", type: "shared", status: "active",
  target_amount_cents: 60_000_000, current_amount_cents: 15_000_000, progress_percent: 25, target_date: "2036-01-31",
  participants: [{ client_id: "a", full_name: "A" }, { client_id: "b", full_name: "B" }], created_by: "x", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
};
const net: NetWorth = { currency: "ZAR", total_assets_cents: 480_000_000, total_liabilities_cents: 165_000_000, net_worth_cents: 315_000_000, as_of: "2026-09-19", breakdown: [] };
const rem = (o: Partial<Reminder>): Reminder => ({
  id: "r", type: "custom", title: "Renew your driving licence", description: null, due_date: "2026-09-20", audience: "client", status: "pending", urgency: "due_soon",
  source: "rule", client: { id: "c", full_name: "Thabo Mokoena" }, related: null, completed_at: null, created_at: "2026-09-01T00:00:00Z", ...o,
});
const env = (status: number, code: string, message: string, extra: Record<string, unknown> = {}) =>
  new ApiError(status, { error: { code, message, request_id: "9f3c2b1e-6d1a-4c1f-9d55-0c6c2f3e7a10", ...extra } });

/** Dev-only kitchen sink for the shared UI kit (route /__ui, absent from production builds). */
export default function UiPreview() {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen bg-charcoal-50 dark:bg-charcoal-900 p-4 md:p-8 space-y-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-charcoal-900 dark:text-white">UI kit preview</h1>

      <section className="space-y-3" data-testid="errors">
        <h2 className="font-semibold text-charcoal-800 dark:text-charcoal-100">ErrorBanner</h2>
        <ErrorBanner error={env(403, "forbidden", "This action is only available to advisers.")} onRetry={() => {}} />
        <ErrorBanner error={env(422, "validation_error", "One or more fields are invalid.", { details: [{ field: "incident.description", code: "too_short", message: "Describe what happened in at least 10 characters." }, { field: "witnesses[0].phone", code: "invalid", message: "Enter a valid phone number." }] })} />
        <ErrorBanner error={env(503, "llm_unavailable", "provider down", { retry_after_seconds: 30 })} />
        <ErrorBanner error={env(500, "internal_error", "KeyError: secret internal detail")} />
        <ErrorBanner error={new ApiError(0, { error: { code: "network_error", message: "We could not reach the server. Check your internet connection and try again." } })} />
        <ErrorBanner error={new Error("Choose a file to upload.")} />
        <ErrorBanner error={new TypeError("data.map is not a function")} />
        <ErrorBanner error="A plain string error" />
        <ErrorBanner error={{ error: { code: "not_found", message: "That claim was not found.", request_id: "abc" } }} />
        <ErrorBanner error={{ weird: { nested: true } }} />
        <ErrorBanner error={{ message: { nested: "object" } }} />
      </section>

      <section className="space-y-3" data-testid="pills">
        <h2 className="font-semibold text-charcoal-800 dark:text-charcoal-100">StatusPill / Badge</h2>
        <div className="flex flex-wrap gap-2">
          {["draft", "submitted", "registered", "assessment", "quotes", "authorised", "in_repair", "completed", "closed", "in_progress", "declined", "pending", "done", "dismissed", "overdue", "due_soon", "upcoming", "brand_new_value"].map((s) => (
            <StatusPill key={s} status={s} />
          ))}
          <StatusPill status="assessment" label="Vehicle assessment" />
          <StatusPill status="assessment" role="advisor" />
          <Badge variant="success">Badge</Badge>
        </div>
      </section>

      <section className="space-y-3" data-testid="stepper">
        <h2 className="font-semibold text-charcoal-800 dark:text-charcoal-100">ClaimStatusStepper</h2>
        <Card><ClaimStatusStepper currentStatus="assessment" role="client" /></Card>
        <Card><ClaimStatusStepper currentStatus="in_repair" role="advisor" /></Card>
        <Card><ClaimStatusStepper currentStatus="draft" role="client" /></Card>
      </section>

      <section className="grid md:grid-cols-2 gap-4" data-testid="cards">
        <NetWorthCard netWorth={net} />
        <GoalCard goal={goal} />
        <ReminderRow reminder={rem({ urgency: "overdue", due_date: "2026-09-10" })} onComplete={async () => {}} showClient />
        <ReminderRow reminder={rem({ urgency: "upcoming", due_date: "2026-12-01" })} onComplete={async () => {}} />
        <ReminderRow reminder={rem({ status: "done" })} />
        <ProgressBar percent={62.5} label="Repairs" showPercent colour="success" />
      </section>

      <section className="space-y-3" data-testid="misc">
        <h2 className="font-semibold text-charcoal-800 dark:text-charcoal-100">Buttons, skeleton, empty state, formatting</h2>
        <div className="flex flex-wrap gap-2 items-center">
          <Button>Primary</Button><Button variant="secondary">Secondary</Button><Button variant="ghost">Ghost</Button><Button variant="danger">Danger</Button>
          <Button loading>Loading</Button><Button disabled>Disabled</Button><Spinner />
          <Button variant="secondary" onClick={() => setOpen(true)}>Open modal</Button>
        </div>
        <Skeleton className="h-8 w-3/4" />
        <Skeleton lines={3} />
        <EmptyState message="No policies found." />
        <Card>
          <ul className="text-sm space-y-1 text-charcoal-800 dark:text-charcoal-100" data-testid="formats">
            <li data-k="zar">{formatZAR(315_000_000)} | {formatZAR(-5050)} | {formatZAR(null)} | {formatZAR(0)}</li>
            <li data-k="date">{formatDate("2026-09-19")} | {formatDate("2026-09-19T22:30:00Z")} | {formatDate("")}</li>
            <li data-k="datetime">{formatDateTime("2026-09-19T14:30:00Z")} | {formatDateTime("2026-09-19")} | {formatDateTime("2026-12-31T22:30:00Z")}</li>
            <li data-k="rands">{[randsToCents("1 234,50"), randsToCents("1,234.50"), randsToCents("R 1234.5"), randsToCents("abc"), randsToCents("0.29")].join(" | ")}</li>
          </ul>
        </Card>
      </section>

      <Modal open={open} onClose={() => setOpen(false)} title="Example modal" footer={<Button onClick={() => setOpen(false)}>Close</Button>}>
        <p className="text-charcoal-700 dark:text-charcoal-200">Modal body.</p>
      </Modal>
    </div>
  );
}
