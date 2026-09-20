import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  Clock,
  FileText,
  Mail,
  Users,
} from "lucide-react";
import { api } from "@/lib/api";
import { advisorLinkFor, formatDate } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";
import { Skeleton, ErrorBanner, EmptyState } from "@/components/ui";
import type { AdvisorDashboard as DashboardData } from "@/lib/types";
import "./dashboard.css";

export default function AdvisorDashboard() {
  const { profile } = useAuth();
  const { data, isLoading, error, refetch } = useQuery<DashboardData>({
    queryKey: ["advisorDashboard"],
    queryFn: () => api.get("/advisor/dashboard"),
    staleTime: 0,
  });
  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error)
    return <ErrorBanner error={error} onRetry={() => void refetch()} />;
  if (!data) return <EmptyState message="No dashboard data found." />;
  const { counts, claims_by_status, needs_attention, upcoming_reminders } =
    data;
  const totalClaims = claims_by_status.reduce(
    (total, stage) => total + stage.count,
    0,
  );
  const reminders = [...upcoming_reminders]
    .sort((a, b) => a.due_date.localeCompare(b.due_date))
    .slice(0, 5);
  const metrics = [
    {
      title: "Your clients",
      value: counts.clients,
      caption: "View client records",
      to: "/advisor/clients",
      icon: Users,
    },
    {
      title: "Open claims",
      value: counts.open_claims,
      caption: "View claims pipeline",
      to: "/advisor/claims",
      icon: ClipboardList,
    },
    {
      title: "Pending requests",
      value: counts.pending_requests,
      caption: "Review requests",
      to: "/advisor/requests",
      icon: FileText,
    },
    {
      title: "Due in 7 days",
      value: counts.reminders_due_7d,
      caption: "Plan your follow-ups",
      to: "/advisor/reminders",
      icon: CalendarDays,
    },
  ];
  const attentionIcons = {
    claim: ClipboardList,
    request: FileText,
    reminder: Clock,
    email: Mail,
  };

  return (
    <div className="adviser-dashboard">
      <header className="adviser-heading">
        <div>
          <p className="adviser-eyebrow">ADVISER WORKSPACE</p>
          <h1>
            A clearer day ahead
            {profile?.full_name ? `, ${profile.full_name.split(" ")[0]}` : ""}.
          </h1>
          <p>Your clients, priorities and next steps. All in one place.</p>
        </div>
        <Link className="adviser-primary" to="/advisor/clients">
          View clients <ArrowUpRight size={18} aria-hidden="true" />
        </Link>
      </header>
      <section className="adviser-metrics" aria-label="Practice overview">
        {metrics.map(({ title, value, caption, to, icon: Icon }) => (
          <Link key={title} to={to} className="adviser-metric">
            <div>
              <span>{title}</span>
              <Icon size={21} aria-hidden="true" />
            </div>
            <strong>{value}</strong>
            <p>
              {caption}
              <ArrowRight size={16} aria-hidden="true" />
            </p>
          </Link>
        ))}
      </section>
      {counts.overdue_reminders > 0 && (
        <Link to="/advisor/reminders" className="adviser-alert">
          <span className="adviser-alert-icon">
            <Clock size={20} aria-hidden="true" />
          </span>
          <div>
            <strong>
              {counts.overdue_reminders} overdue reminder
              {counts.overdue_reminders === 1 ? "" : "s"} to follow up
            </strong>
            <p>A quick check-in can keep things moving.</p>
          </div>
          <span className="adviser-alert-action">
            Review reminders <ArrowRight size={17} aria-hidden="true" />
          </span>
        </Link>
      )}
      <div className="adviser-work-grid">
        <section className="adviser-card" aria-labelledby="attention-heading">
          <div className="adviser-section-heading">
            <div>
              <h2 id="attention-heading">
                Needs your attention{" "}
                <span className="adviser-count">{needs_attention.length}</span>
              </h2>
              <p>Pick up where your clients need you.</p>
            </div>
          </div>
          <div className="adviser-task-list">
            {needs_attention.map((item) => {
              const Icon = attentionIcons[item.kind] ?? FileText;
              return (
                <Link
                  key={`${item.kind}-${item.id}`}
                  to={advisorLinkFor(item.link)}
                  className="adviser-task"
                >
                  <span
                    className={`adviser-task-icon ${item.kind === "reminder" ? "is-reminder" : ""}`}
                  >
                    <Icon size={20} aria-hidden="true" />
                  </span>
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.subtitle || item.client.full_name}</p>
                    {item.due_at && (
                      <span className="adviser-task-date">
                        Due {formatDate(item.due_at)}
                      </span>
                    )}
                  </div>
                  <ArrowRight size={18} aria-hidden="true" />
                </Link>
              );
            })}
          </div>
          {!needs_attention.length && (
            <div className="adviser-empty">
              <CheckCircle2 size={28} aria-hidden="true" />
              <h3>You’re all caught up</h3>
              <p>New items that need your attention will appear here.</p>
            </div>
          )}
        </section>
        <section className="adviser-card" aria-labelledby="upcoming-heading">
          <div className="adviser-section-heading">
            <div>
              <h2 id="upcoming-heading">Coming up</h2>
              <p>Keep the next conversation in sight.</p>
            </div>
            <Link to="/advisor/reminders" className="adviser-link">
              View all <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
          <div>
            {reminders.map((reminder) => (
              <Link
                to="/advisor/reminders"
                key={reminder.id}
                className="adviser-reminder"
              >
                <span className="adviser-task-icon">
                  <CalendarDays size={20} aria-hidden="true" />
                </span>
                <div>
                  <strong>{reminder.client.full_name}</strong>
                  <p>{reminder.title}</p>
                  <time dateTime={reminder.due_date}>
                    {formatDate(reminder.due_date)}
                  </time>
                </div>
                <ArrowRight size={16} aria-hidden="true" />
              </Link>
            ))}
          </div>
          {!reminders.length && (
            <div className="adviser-empty">
              <CalendarDays size={28} aria-hidden="true" />
              <h3>A little room to plan</h3>
              <p>No upcoming reminders.</p>
              <Link className="adviser-link" to="/advisor/reminders">
                View reminders <ArrowRight size={16} aria-hidden="true" />
              </Link>
            </div>
          )}
        </section>
      </div>
      <section
        className="adviser-card adviser-pipeline"
        aria-labelledby="pipeline-heading"
      >
        <div className="adviser-section-heading">
          <div>
            <h2 id="pipeline-heading">Claims at a glance</h2>
            <p>See where each claim stands.</p>
          </div>
          <Link className="adviser-link" to="/advisor/claims">
            Open pipeline <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>
        {totalClaims > 0 ? (
          <div className="adviser-stage-grid">
            {claims_by_status.map((stage) => (
              <Link
                to="/advisor/claims"
                key={stage.status}
                className="adviser-stage"
              >
                <div>
                  <span>{stage.label}</span>
                  <strong>{stage.count}</strong>
                </div>
                <progress
                  value={stage.count}
                  max={totalClaims}
                  aria-label={`${stage.label}: ${stage.count} of ${totalClaims} claims`}
                />
              </Link>
            ))}
          </div>
        ) : (
          <div className="adviser-empty">
            <ClipboardList size={26} aria-hidden="true" />
            <h3>No claims to track</h3>
            <p>New claims will appear in your pipeline.</p>
          </div>
        )}
      </section>
      <nav className="adviser-shortcuts" aria-label="Adviser tools">
        <Link to="/advisor/assistant">
          <span>Need an answer?</span>
          <strong>
            Document assistant <ArrowUpRight size={17} aria-hidden="true" />
          </strong>
        </Link>
        <Link to="/advisor/email">
          <span>Keep the conversation going</span>
          <strong>
            Review your inbox <ArrowUpRight size={17} aria-hidden="true" />
          </strong>
        </Link>
        <Link to="/advisor/radar">
          <span>Plan the next step</span>
          <strong>
            Client opportunities <ArrowUpRight size={17} aria-hidden="true" />
          </strong>
        </Link>
      </nav>
    </div>
  );
}
