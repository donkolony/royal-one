import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Car,
  ClipboardList,
  FileText,
  Mail,
  ShieldCheck,
  Target,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatZAR, formatDate } from "@/lib/utils";
import { Skeleton, ErrorBanner, EmptyState, StatusPill } from "@/components/ui";
import type { ClientDashboard } from "@/lib/types";
import "./dashboard.css";

const actions = [
  {
    path: "/claims/report",
    title: "Report an accident",
    description: "Know what to do next.",
    icon: Car,
  },
  {
    path: "/claims/new",
    title: "Register a claim",
    description: "Start or continue your claim.",
    icon: ClipboardList,
  },
  {
    path: "/requests",
    title: "Request a document",
    description: "Get the paperwork you need.",
    icon: FileText,
  },
];

export default function Dashboard() {
  const { data, isLoading, error, refetch } = useQuery<ClientDashboard>({
    queryKey: ["dashboard"],
    queryFn: () => api.get("/me/dashboard"),
    staleTime: 0,
  });
  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error)
    return <ErrorBanner error={error} onRetry={() => void refetch()} />;
  if (!data) return <EmptyState message="No dashboard data found." />;
  const {
    client,
    net_worth,
    policies,
    open_claims,
    goals,
    reminders,
    adviser,
    pending_requests,
  } = data;
  const upcoming = [...reminders.upcoming]
    .sort((a, b) => a.due_date.localeCompare(b.due_date))
    .slice(0, 3);

  return (
    <div className="dashboard-home">
      <header className="dashboard-heading">
        <div>
          <p className="dashboard-eyebrow">YOUR FINANCIAL HOME</p>
          <h1>Good morning, {client.full_name.split(" ")[0]}.</h1>
          <p>Here’s where you stand, and what’s next.</p>
        </div>
        <Link className="dashboard-primary" to="/requests">
          New request <ArrowUpRight size={17} aria-hidden="true" />
        </Link>
      </header>

      <div className="dashboard-summary">
        <section className="dashboard-balance" aria-labelledby="balance-title">
          <div className="dashboard-card-heading">
            <h2 id="balance-title">Your net worth</h2>
            <span className="dashboard-symbol">
              <ShieldCheck size={20} aria-hidden="true" />
            </span>
          </div>
          <p className="dashboard-amount">
            {formatZAR(net_worth.net_worth_cents)}
          </p>
          <p className="dashboard-asof">As of {formatDate(net_worth.as_of)}</p>
          <dl className="dashboard-breakdown">
            <div>
              <dt>
                <span className="dashboard-dot" />
                Total assets
              </dt>
              <dd>{formatZAR(net_worth.total_assets_cents)}</dd>
            </div>
            <div>
              <dt>
                <span className="dashboard-dot muted-dot" />
                Total liabilities
              </dt>
              <dd>{formatZAR(net_worth.total_liabilities_cents)}</dd>
            </div>
          </dl>
          <div className="dashboard-account-stats">
            {[
              { label: "Policies", count: policies.count, to: "/policies" },
              { label: "Open claims", count: open_claims.count, to: "/claims" },
              {
                label: "Pending requests",
                count: pending_requests.count,
                to: "/requests",
              },
            ].map((item) => (
              <Link key={item.label} to={item.to}>
                <strong>{item.count}</strong>
                <span>{item.label}</span>
                <ArrowUpRight size={15} aria-hidden="true" />
              </Link>
            ))}
          </div>
        </section>

        <section
          className="dashboard-card dashboard-agenda"
          aria-labelledby="agenda-title"
        >
          <div className="dashboard-card-heading">
            <h2 id="agenda-title">Coming up</h2>
            <Link
              className="dashboard-link"
              to="/reminders"
              aria-label="View all reminders"
            >
              View all <ArrowRight size={15} aria-hidden="true" />
            </Link>
          </div>
          <p className="dashboard-caption">
            A little planning goes a long way.
          </p>
          {reminders.overdue_count > 0 && (
            <Link className="dashboard-overdue" to="/reminders">
              {reminders.overdue_count} overdue reminder
              {reminders.overdue_count === 1 ? "" : "s"}{" "}
              <ArrowRight size={14} aria-hidden="true" />
            </Link>
          )}
          <div className="dashboard-agenda-list">
            {upcoming.map((reminder) => (
              <Link
                key={reminder.id}
                to="/reminders"
                className="dashboard-agenda-item"
              >
                <span className="dashboard-calendar">
                  <CalendarDays size={18} aria-hidden="true" />
                </span>
                <div>
                  <strong>{reminder.title}</strong>
                  <span>{formatDate(reminder.due_date)}</span>
                </div>
                <ArrowRight size={15} aria-hidden="true" />
              </Link>
            ))}
          </div>
          {!upcoming.length && (
            <div className="dashboard-empty">
              <CalendarDays size={23} aria-hidden="true" />
              <h3>You’re all caught up</h3>
              <p>Your upcoming reminders will appear here.</p>
            </div>
          )}
        </section>
      </div>

      <nav className="dashboard-actions" aria-label="Quick actions">
        {actions.map(({ path, title, description, icon: Icon }) => (
          <Link key={path} to={path}>
            <span className="dashboard-action-icon">
              <Icon size={21} aria-hidden="true" />
            </span>
            <div>
              <strong>{title}</strong>
              <span>{description}</span>
            </div>
            <ArrowUpRight size={17} aria-hidden="true" />
          </Link>
        ))}
      </nav>

      <section className="dashboard-goals" aria-labelledby="goals-title">
        <div className="dashboard-section-heading">
          <div>
            <h2 id="goals-title">Your goals, taking shape</h2>
            <p>Small steps towards the things that matter.</p>
          </div>
          <Link className="dashboard-link" to="/goals">
            View all goals <ArrowRight size={15} aria-hidden="true" />
          </Link>
        </div>
        <div className="dashboard-goal-grid">
          {goals.items.slice(0, 3).map((goal) => {
            const progress = Math.max(
              0,
              Math.min(
                100,
                Number.isFinite(goal.progress_percent)
                  ? goal.progress_percent
                  : 0,
              ),
            );
            return (
              <Link to="/goals" className="dashboard-goal" key={goal.id}>
                <div className="dashboard-card-heading">
                  <span className="dashboard-symbol">
                    <Target size={19} aria-hidden="true" />
                  </span>
                  <span className="dashboard-goal-percent">
                    {Math.round(progress)}% saved
                  </span>
                </div>
                <h3>{goal.title}</h3>
                <p className="dashboard-goal-value">
                  {formatZAR(goal.current_amount_cents)}{" "}
                  <span>of {formatZAR(goal.target_amount_cents)}</span>
                </p>
                <progress
                  max={100}
                  value={progress}
                  aria-label={`${goal.title} progress`}
                />
                <div className="dashboard-goal-footer">
                  <span>
                    {goal.target_date
                      ? `Target: ${formatDate(goal.target_date)}`
                      : "Set your pace with your adviser"}
                  </span>
                  <ArrowRight size={15} aria-hidden="true" />
                </div>
              </Link>
            );
          })}
        </div>
        {!goals.items.length && (
          <div className="dashboard-card dashboard-empty">
            <Target size={24} aria-hidden="true" />
            <h3>What would you like to work towards?</h3>
            <p>Your adviser can help you put a plan in place.</p>
            <Link className="dashboard-link" to="/requests">
              Talk to your adviser <ArrowRight size={15} aria-hidden="true" />
            </Link>
          </div>
        )}
      </section>

      <div className="dashboard-bottom">
        <section className="dashboard-card" aria-labelledby="claims-title">
          <div className="dashboard-card-heading">
            <h2 id="claims-title">
              Active claims{" "}
              <span className="dashboard-count">{open_claims.count}</span>
            </h2>
            <Link
              to="/claims"
              className="dashboard-link"
              aria-label="View all claims"
            >
              View all <ArrowRight size={15} aria-hidden="true" />
            </Link>
          </div>
          <div className="dashboard-claim-list">
            {open_claims.items.slice(0, 3).map((claim) => (
              <Link
                className="dashboard-claim"
                key={claim.id}
                to={
                  claim.status === "draft"
                    ? `/claims/new?draft=${claim.id}`
                    : `/claims/${claim.id}`
                }
              >
                <span className="dashboard-symbol">
                  <ClipboardList size={19} aria-hidden="true" />
                </span>
                <div>
                  <strong>{claim.reference || "Continue your draft"}</strong>
                  <span>
                    {claim.insurer?.name ?? "Insurer not selected"}
                    {claim.submitted_at
                      ? ` · ${formatDate(claim.submitted_at)}`
                      : " · Not yet submitted"}
                  </span>
                </div>
                <StatusPill status={claim.status} />
                <ArrowRight size={15} aria-hidden="true" />
              </Link>
            ))}
          </div>
          {!open_claims.items.length && (
            <div className="dashboard-empty">
              <ShieldCheck size={24} aria-hidden="true" />
              <h3>No open claims</h3>
              <p>We’re here when you need us.</p>
            </div>
          )}
        </section>
        <aside className="dashboard-adviser">
          <p className="dashboard-eyebrow">A PERSON IN YOUR CORNER</p>
          <h2>
            A little guidance.
            <br />A clearer way forward.
          </h2>
          {adviser ? (
            <>
              <div className="dashboard-adviser-person">
                <span className="dashboard-adviser-avatar">
                  {adviser.full_name
                    .split(" ")
                    .map((p) => p[0])
                    .slice(0, 2)
                    .join("")}
                </span>
                <div>
                  <strong>{adviser.full_name}</strong>
                  <span>Your financial adviser</span>
                </div>
              </div>
              <a
                href={`mailto:${adviser.email}`}
                className="dashboard-adviser-contact"
              >
                <Mail size={17} aria-hidden="true" />
                Contact your adviser{" "}
                <ArrowUpRight size={16} aria-hidden="true" />
              </a>
            </>
          ) : (
            <>
              <p>Let’s make time for your next chapter.</p>
              <Link to="/requests" className="dashboard-adviser-contact">
                Request a consultation{" "}
                <ArrowUpRight size={16} aria-hidden="true" />
              </Link>
            </>
          )}
        </aside>
      </div>
      <footer className="dashboard-footer">
        <ShieldCheck size={15} aria-hidden="true" />
        Independent advice. Personal attention.
      </footer>
    </div>
  );
}
