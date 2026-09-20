import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useForm } from "react-hook-form";
import {
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  Bell,
  CalendarDays,
  Car,
  Check,
  CheckCheck,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  Download,
  FileText,
  House,
  LayoutDashboard,
  Mail,
  Menu,
  MoreHorizontal,
  MessageSquare,
  Plus,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  TriangleAlert,
  Users,
  Wallet,
  X,
  type LucideIcon,
} from "lucide-react";
import {
  clients,
  dateLabel,
  money,
  policies,
  repository,
  stages,
  today,
  uid,
  type Claim,
  type Goal,
  type Store,
} from "./data";

type ModalState = { kind: string; id?: string } | null;
const requestTypes = [
  "Change of address",
  "Change of bank details",
  "Policy document",
  "Border letter",
  "IRP5 certificate",
  "Consultation",
  "Financial information",
];
const checklist = [
  "Photograph the road surface and direction of travel",
  "Record the address or nearest cross streets",
  "Photograph all vehicles and people involved",
  "Record licence plates and registration discs",
  "Collect identity and contact details of the parties",
  "Record witness names and contact details",
  "Collect the other parties' insurance details",
  "Record your police report and case number",
];
function Badge({
  children,
  tone = "green",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return (
    <span className={`badge ${tone}`}>
      <i />
      {children}
    </span>
  );
}
function IconButton({
  icon: Icon,
  label,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className="icon-button"
      title={label}
      aria-label={label}
      onClick={onClick}
    >
      <Icon size={19} />
    </button>
  );
}
function Empty({ text }: { text: string }) {
  return (
    <div className="empty">
      <CheckCheck size={28} />
      <h3>All clear</h3>
      <p>{text}</p>
    </div>
  );
}
function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
function Modal({
  title,
  children,
  close,
}: {
  title: string;
  children: ReactNode;
  close: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    ref.current?.focus();
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handle = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "Tab") {
        const nodes = ref.current?.querySelectorAll<HTMLElement>(
          "button,input,select,textarea,a[href]",
        );
        if (!nodes?.length) return;
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", handle);
    return () => {
      document.body.style.overflow = old;
      document.removeEventListener("keydown", handle);
      previous?.focus();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div
        className="modal"
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header>
          <h2>{title}</h2>
          <IconButton icon={X} label="Close dialog" onClick={close} />
        </header>
        {children}
      </div>
    </div>
  );
}
function download(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function App() {
  const [data, setData] = useState<Store>(() => repository.load());
  const [role, setRole] = useState<"client" | "adviser">(() =>
    localStorage.getItem("rs-role") === "adviser" ? "adviser" : "client",
  );
  const [client, setClient] = useState(clients[0].name);
  const [modal, setModal] = useState<ModalState>(null);
  const [toast, setToast] = useState("");
  const [mobile, setMobile] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [claimFilter, setClaimFilter] = useState("All");
  const [notifications, setNotifications] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const adviser = role === "adviser";
  const profile = clients.find((c) => c.name === client)!;
  const update = (fn: (d: Store) => Store) => {
    setData((old) => {
      const next = fn(old);
      try {
        repository.save(next);
      } catch {
        setToast(
          "Browser storage is full. Changes are available for this session.",
        );
      }
      return next;
    });
  };
  const notify = (text: string) => {
    setToast(text);
  };
  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(""), 4500);
      return () => clearTimeout(t);
    }
  }, [toast]);
  useEffect(() => {
    setMobile(false);
    setQuery("");
  }, [location.pathname]);
  const ownClaims = data.claims.filter((c) => adviser || c.client === client);
  const ownGoals = data.goals.filter((g) => adviser || g.client === client);
  const ownReminders = data.reminders.filter(
    (r) => adviser || (r.client === client && r.recipient !== "Adviser"),
  );
  const ownRequests = data.requests.filter(
    (r) => adviser || r.client === client,
  );
  const openClaims = ownClaims.filter((c) => c.status < 6);
  const pendingReminders = ownReminders
    .filter((r) => !r.done)
    .sort((a, b) => a.date.localeCompare(b.date));
  const primaryNavigation: [string, string, LucideIcon][] = [
    ["/", "Overview", LayoutDashboard],
    ["/claims", "Claims", ClipboardList],
    ["/goals", "Goals", Target],
    ["/reminders", "Reminders", CalendarDays],
  ];
  const moreNavigation: [string, string, LucideIcon][] = [
    ...(adviser
      ? [["/clients", "Clients", Users] as [string, string, LucideIcon]]
      : []),
    ["/policies", "Policies", ShieldCheck],
    ["/requests", "Requests", MessageSquare],
    ...(adviser
      ? ([
          ["/assistant", "Document assistant", Sparkles],
          ["/inbox", "Inbox", Mail],
        ] as [string, string, LucideIcon][])
      : []),
  ];
  const navigation = [...primaryNavigation, ...moreNavigation];
  const moreActive = moreNavigation.some((n) => n[0] === location.pathname);
  const title =
    navigation.find((n) => n[0] === location.pathname)?.[1] || "Overview";
  const switchRole = (next: "client" | "adviser") => {
    setRole(next);
    localStorage.setItem("rs-role", next);
    setModal(null);
    navigate("/");
  };
  const goalCard = (g: Goal, index: number) => (
    <article className="goal-card" key={g.id}>
      <div className="row between">
        <span className={`goal-icon color-${index % 3}`}>
          {index % 3 === 0 ? (
            <House size={20} />
          ) : index % 3 === 1 ? (
            <Wallet size={20} />
          ) : (
            <TrendingUp size={20} />
          )}
        </span>
        {g.shared ? (
          <span className="muted small">
            <Users size={13} /> Shared goal
          </span>
        ) : (
          <span className="muted small">{dateLabel(g.date)}</span>
        )}
      </div>
      <h3>{g.name}</h3>
      {adviser && <p className="small muted">{g.client}</p>}
      <div className="row between goal-amount">
        <strong>{money(g.current)}</strong>
        <span className="muted small">of {money(g.target)}</span>
      </div>
      <progress value={g.current} max={g.target} />
      <div className="row between small">
        <span className="muted">
          {Math.round((g.current / g.target) * 100)}% achieved
        </span>
        {adviser ? (
          <button
            className="text-button"
            onClick={() => setModal({ kind: "goal", id: g.id })}
          >
            Update <ArrowRight size={14} />
          </button>
        ) : (
          <span>{money(Math.max(0, g.target - g.current))} to go</span>
        )}
      </div>
    </article>
  );
  const remindersList = (limit?: number) => (
    <div className="reminder-list">
      {pendingReminders.slice(0, limit).map((r) => (
        <div className="reminder-item" key={r.id}>
          <span className="date-box">
            <b>{new Date(r.date + "T12:00:00").getDate()}</b>
            {new Date(r.date + "T12:00:00").toLocaleDateString("en", {
              month: "short",
            })}
          </span>
          <div className="grow">
            <strong>{r.title}</strong>
            <p>
              {adviser
                ? r.client
                : r.recipient === "Both"
                  ? "You & your adviser"
                  : "Personal reminder"}
            </p>
          </div>
          <IconButton
            icon={Check}
            label={`Complete ${r.title}`}
            onClick={() => {
              update((d) => ({
                ...d,
                reminders: d.reminders.map((x) =>
                  x.id === r.id ? { ...x, done: true } : x,
                ),
              }));
              notify("Reminder completed");
            }}
          />
        </div>
      ))}
      {!pendingReminders.length && <Empty text="No upcoming reminders." />}
    </div>
  );
  const claimTable = (items: Claim[]) => (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Claim / vehicle</th>
            {adviser && <th>Client</th>}
            <th>Insurer</th>
            <th>Submitted</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((c) => (
            <tr
              key={c.id}
              onClick={() => setModal({ kind: "claim-detail", id: c.id })}
            >
              <td>
                <button
                  className="table-link"
                  onClick={() => setModal({ kind: "claim-detail", id: c.id })}
                >
                  {c.vehicle}
                </button>
                <span className="cell-secondary">{c.id}</span>
              </td>
              {adviser && <td>{c.client}</td>}
              <td>{c.insurer}</td>
              <td>{dateLabel(c.date)}</td>
              <td>
                <Badge
                  tone={
                    c.status === 6 ? "gray" : c.status === 3 ? "green" : "amber"
                  }
                >
                  {stages[c.status]}
                </Badge>
              </td>
              <td>
                <ChevronRight size={16} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!items.length && <Empty text="No claims match this view." />}
    </div>
  );
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <a
          className="brand"
          href="/"
          onClick={(e) => {
            e.preventDefault();
            navigate("/");
          }}
        >
          <img
            className="brand-logo"
            src="/brand/royal-square-logo.png"
            alt="Royal Square Financial"
          />
        </a>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav>
          {primaryNavigation.map(([path, label, Icon]) => (
            <NavLink key={path} to={path} end={path === "/"}>
              <Icon size={19} />
              <span>{label}</span>
              {path === "/claims" && openClaims.length > 0 && (
                <b className="nav-count">{openClaims.length}</b>
              )}
              {path === "/inbox" && <span className="nav-dot" />}
            </NavLink>
          ))}
          <button
            className={`more-nav-button ${moreActive ? "active" : ""}`}
            aria-expanded={moreOpen}
            onClick={() => setMoreOpen((open) => !open)}
          >
            <MoreHorizontal size={19} />
            <span>More</span>
            <ChevronRight
              className={`more-chevron ${moreOpen ? "open" : ""}`}
              size={16}
            />
          </button>
          {moreOpen && (
            <div className="more-nav-items">
              {moreNavigation.map(([path, label, Icon]) => (
                <NavLink key={path} to={path}>
                  <Icon size={19} />
                  <span>{label}</span>
                  {path === "/inbox" && <span className="nav-dot" />}
                </NavLink>
              ))}
            </div>
          )}
        </nav>
        <div className="sidebar-bottom">
          <button
            className="support-link"
            onClick={() => setModal({ kind: "support" })}
          >
            <CircleHelp size={18} /> Help & support <ArrowUpRight size={15} />
          </button>
          <button
            className="support-link"
            onClick={() => navigate("/settings")}
          >
            <Settings size={18} /> Settings
          </button>
          <div className="sidebar-footer">
            Royal Square Financial <span>FSP 29370</span>
          </div>
        </div>
      </aside>
      {mobile && (
        <div className="sidebar-scrim" onClick={() => setMobile(false)} />
      )}
      <div className="main-shell">
        <header className="topbar">
          <div className="row">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMobile(!mobile)}
            >
              <Menu size={22} />
            </button>
            <span className="breadcrumb">
              Workspace <ChevronRight size={14} /> <strong>{title}</strong>
            </span>
          </div>
          <div className="topbar-right">
            <div className="notification-wrap">
              <IconButton
                icon={Bell}
                label="Notifications"
                onClick={() => setNotifications(!notifications)}
              />
              {pendingReminders.length > 0 && (
                <i className="notification-dot" />
              )}
              {notifications && (
                <div className="notification-panel">
                  <h3>Upcoming reminders</h3>
                  {pendingReminders.slice(0, 3).map((r) => (
                    <button
                      key={r.id}
                      onClick={() => {
                        navigate("/reminders");
                        setNotifications(false);
                      }}
                    >
                      <strong>{r.title}</strong>
                      <span>{dateLabel(r.date)}</span>
                    </button>
                  ))}
                  {!pendingReminders.length && <p>You're all caught up.</p>}
                </div>
              )}
            </div>
          </div>
        </header>
        <main>
          <Routes>
            <Route
              path="/"
              element={
                <>
                  <div className="page-heading">
                    <div>
                      {!adviser && (
                        <div className="eyebrow">YOUR FINANCIAL HOME</div>
                      )}
                      <h1>
                        {adviser
                          ? "A clearer day ahead, Qiniso."
                          : `Good morning, ${client.split(" ")[0]}.`}
                      </h1>
                    </div>
                    <button
                      className="button secondary"
                      onClick={() =>
                        setModal({ kind: adviser ? "reminder" : "request" })
                      }
                    >
                      <Plus size={17} />
                      {adviser ? "Add reminder" : "New request"}
                    </button>
                  </div>
                  <div className="overview-top">
                    <section className="wealth-panel">
                      <div className="row between">
                        <span className="wealth-label">
                          {adviser
                            ? "TOTAL CLIENT NET WORTH"
                            : "YOUR ESTIMATED NET WORTH"}
                        </span>
                        <span className="wealth-icon">
                          <Wallet size={20} />
                        </span>
                      </div>
                      <h2>
                        {money(
                          adviser
                            ? clients.reduce(
                                (s, c) => s + c.assets - c.liabilities,
                                0,
                              )
                            : profile.assets - profile.liabilities,
                        )}
                        <span>.00</span>
                      </h2>
                      <div className="wealth-trend">
                        <TrendingUp size={15} />
                        <strong>8.2%</strong>
                        <span>vs. last year</span>
                        <span className="wealth-period">Past 12 months</span>
                      </div>
                      <div
                        className="wealth-chart"
                        aria-label="Illustrative net worth trend over the past year"
                      >
                        {[
                          25, 30, 28, 39, 35, 45, 43, 53, 49, 58, 64, 70, 67,
                          79, 76, 85, 81, 92, 89, 100, 97, 110, 106, 122, 116,
                          128, 124, 142, 136, 153, 148, 160,
                        ].map((h, i) => (
                          <i key={i} style={{ height: h + "px" }} />
                        ))}
                      </div>
                      <div className="wealth-axis">
                        <span>OCT 2025</span>
                        <span>MAR 2026</span>
                        <span>SEP 2026</span>
                      </div>
                      <div className="wealth-breakdown">
                        <div>
                          <span>
                            <ArrowDownLeft size={15} /> Total assets
                          </span>
                          <strong>
                            {money(
                              adviser
                                ? clients.reduce((s, c) => s + c.assets, 0)
                                : profile.assets,
                            )}
                          </strong>
                        </div>
                        <div>
                          <span>
                            <ArrowUpRight size={15} /> Total liabilities
                          </span>
                          <strong>
                            {money(
                              adviser
                                ? clients.reduce((s, c) => s + c.liabilities, 0)
                                : profile.liabilities,
                            )}
                          </strong>
                        </div>
                      </div>
                    </section>
                    <div className="overview-side">
                      <div className="stat-grid">
                        <div className="stat">
                          <span className="stat-icon">
                            <ShieldCheck size={20} />
                          </span>
                          <span>
                            {adviser ? "Assigned clients" : "Active policies"}
                          </span>
                          <strong>
                            {adviser
                              ? clients.length
                              : policies.length.toString().padStart(2, "0")}
                          </strong>
                          <button
                            className="text-button"
                            onClick={() =>
                              navigate(adviser ? "/clients" : "/policies")
                            }
                          >
                            View {adviser ? "clients" : "policies"}{" "}
                            <ArrowRight size={14} />
                          </button>
                        </div>
                        <div className="stat">
                          <span className="stat-icon amber-icon">
                            <ClipboardList size={20} />
                          </span>
                          <span>Open claims</span>
                          <strong>
                            {openClaims.length.toString().padStart(2, "0")}
                          </strong>
                          <button
                            className="text-button"
                            onClick={() => navigate("/claims")}
                          >
                            Track progress <ArrowRight size={14} />
                          </button>
                        </div>
                      </div>
                      <div className="review-banner">
                        <div className="review-copy">
                          <span className="eyebrow">LET'S LOOK AHEAD</span>
                          <h3>
                            Your next chapter
                            <br />
                            starts with a conversation.
                          </h3>
                          <button
                            className="text-button"
                            onClick={() => setModal({ kind: "consultation" })}
                          >
                            Book your annual review <ArrowRight size={15} />
                          </button>
                        </div>
                        <img
                          src="https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=440&q=85"
                          alt="A bright meeting space with plants"
                        />
                      </div>
                    </div>
                  </div>
                  <section className="quick-actions">
                    <span>How can we help?</span>
                    <button onClick={() => setModal({ kind: "accident" })}>
                      <span className="action-icon">
                        <Car size={19} />
                      </span>
                      Report an accident <ArrowUpRight size={15} />
                    </button>
                    <button onClick={() => setModal({ kind: "claim" })}>
                      <span className="action-icon">
                        <ClipboardList size={19} />
                      </span>
                      Register a claim <ArrowUpRight size={15} />
                    </button>
                    <button
                      onClick={() => setModal({ kind: "document-request" })}
                    >
                      <span className="action-icon">
                        <FileText size={19} />
                      </span>
                      Request a document <ArrowUpRight size={15} />
                    </button>
                  </section>
                  <div className="section-title">
                    <h2>
                      {adviser ? "Client goals" : "Big plans. Steady progress."}
                    </h2>
                    <button
                      className="text-button"
                      onClick={() => navigate("/goals")}
                    >
                      View all goals <ArrowRight size={15} />
                    </button>
                  </div>
                  <div className="goal-grid">
                    {ownGoals.slice(0, 3).map(goalCard)}
                  </div>
                  <div className="bottom-grid">
                    <section>
                      <div className="section-title">
                        <h2>
                          Active claims{" "}
                          <span className="count">{openClaims.length}</span>
                        </h2>
                        <button
                          className="text-button"
                          onClick={() => navigate("/claims")}
                        >
                          View all <ArrowRight size={15} />
                        </button>
                      </div>
                      {claimTable(openClaims.slice(0, 3))}
                    </section>
                    <section>
                      <div className="section-title">
                        <h2>Coming up</h2>
                        <button
                          className="text-button"
                          onClick={() => navigate("/reminders")}
                        >
                          View all <ArrowRight size={15} />
                        </button>
                      </div>
                      {remindersList(3)}
                    </section>
                  </div>
                  <div className="reassurance">
                    <ShieldCheck size={15} />
                    <span>Your future, thoughtfully protected.</span>
                    <span>Independent advice. Personal attention.</span>
                  </div>
                </>
              }
            />
            <Route
              path="/policies"
              element={
                <>
                  <PageHeading title="Your policies" />
                  <div className="toolbar">
                    <SearchInput
                      value={query}
                      onChange={setQuery}
                      placeholder="Search policies or providers"
                    />
                    <span className="muted small">
                      {policies.length} active policies ·{" "}
                      {money(policies.reduce((s, p) => s + p.premium, 0))}/month
                    </span>
                  </div>
                  <div className="policy-grid">
                    {policies
                      .filter((p) =>
                        (p.name + p.provider + p.id)
                          .toLowerCase()
                          .includes(query.toLowerCase()),
                      )
                      .map((p) => (
                        <article className="policy-card" key={p.id}>
                          <div className="row between">
                            <span className="policy-provider">
                              {p.provider}
                            </span>
                            <Badge>Active</Badge>
                          </div>
                          <span className="policy-category">{p.category}</span>
                          <h2>{p.name}</h2>
                          <p>{p.detail}</p>
                          <dl>
                            <div>
                              <dt>
                                {p.category === "Investment"
                                  ? "Fund value"
                                  : "Sum insured"}
                              </dt>
                              <dd>{money(p.cover)}</dd>
                            </div>
                            <div>
                              <dt>
                                Monthly{" "}
                                {p.category === "Investment"
                                  ? "contribution"
                                  : "premium"}
                              </dt>
                              <dd>{money(p.premium)}</dd>
                            </div>
                            <div>
                              <dt>Next review</dt>
                              <dd>{dateLabel(p.renewal)}</dd>
                            </div>
                          </dl>
                          <div className="row between">
                            <span className="muted small">{p.id}</span>
                            <button
                              className="text-button"
                              onClick={() =>
                                setModal({ kind: "policy", id: p.id })
                              }
                            >
                              Policy details <ArrowRight size={15} />
                            </button>
                          </div>
                        </article>
                      ))}
                  </div>
                </>
              }
            />
            <Route
              path="/claims"
              element={
                <>
                  <PageHeading
                    title={adviser ? "Claims workspace" : "Your claims"}
                    action={
                      <button
                        className="button"
                        onClick={() => setModal({ kind: "claim" })}
                      >
                        <Plus size={17} />
                        Register claim
                      </button>
                    }
                  />
                  <div className="toolbar">
                    <div className="tabs">
                      {["All", "Open", "Closed"].map((s) => (
                        <button
                          className={claimFilter === s ? "selected" : ""}
                          key={s}
                          onClick={() => setClaimFilter(s)}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                    <SearchInput
                      value={query}
                      onChange={setQuery}
                      placeholder="Search claims"
                    />
                  </div>
                  {claimTable(
                    ownClaims.filter(
                      (c) =>
                        (claimFilter === "All" ||
                          (claimFilter === "Closed"
                            ? c.status === 6
                            : c.status < 6)) &&
                        (c.vehicle + c.id + c.client + c.insurer)
                          .toLowerCase()
                          .includes(query.toLowerCase()),
                    ),
                  )}
                </>
              }
            />
            <Route
              path="/goals"
              element={
                <>
                  <PageHeading
                    title="Make room for your future"
                    action={
                      adviser && (
                        <button
                          className="button"
                          onClick={() => setModal({ kind: "goal" })}
                        >
                          <Plus size={17} />
                          Add goal
                        </button>
                      )
                    }
                  />
                  <div className="goal-grid">{ownGoals.map(goalCard)}</div>
                  {!ownGoals.length && (
                    <Empty text="Your adviser can help you set your first goal." />
                  )}
                </>
              }
            />
            <Route
              path="/reminders"
              element={
                <>
                  <PageHeading
                    title="A little ahead of life"
                    action={
                      adviser && (
                        <button
                          className="button"
                          onClick={() => setModal({ kind: "reminder" })}
                        >
                          <Plus size={17} />
                          Add reminder
                        </button>
                      )
                    }
                  />
                  <div className="reminders-page">
                    {remindersList()}
                    <h2 className="completed-heading">Completed</h2>
                    {ownReminders
                      .filter((r) => r.done)
                      .map((r) => (
                        <div className="completed-row" key={r.id}>
                          <CheckCheck size={19} />
                          <span>{r.title}</span>
                          <button
                            className="text-button"
                            onClick={() =>
                              update((d) => ({
                                ...d,
                                reminders: d.reminders.map((x) =>
                                  x.id === r.id ? { ...x, done: false } : x,
                                ),
                              }))
                            }
                          >
                            Restore
                          </button>
                        </div>
                      ))}
                  </div>
                </>
              }
            />
            <Route
              path="/requests"
              element={
                <>
                  <PageHeading
                    title="Requests"
                    action={
                      <button
                        className="button"
                        onClick={() => setModal({ kind: "request" })}
                      >
                        <Plus size={17} />
                        New request
                      </button>
                    }
                  />
                  <div className="request-list">
                    {ownRequests.map((r) => (
                      <article key={r.id} className="request-row">
                        <span className="request-icon">
                          <MessageSquare size={20} />
                        </span>
                        <div className="grow">
                          <div className="row">
                            <h3>{r.type}</h3>
                            <Badge
                              tone={
                                r.status === "Completed" ? "green" : "amber"
                              }
                            >
                              {r.status}
                            </Badge>
                          </div>
                          <p>{r.details}</p>
                          <span className="muted small">
                            {r.id} · {dateLabel(r.date)}
                            {adviser ? " · " + r.client : ""}
                          </span>
                        </div>
                        {adviser && (
                          <select
                            aria-label={`Status for ${r.id}`}
                            value={r.status}
                            onChange={(e) => {
                              update((d) => ({
                                ...d,
                                requests: d.requests.map((x) =>
                                  x.id === r.id
                                    ? { ...x, status: e.target.value }
                                    : x,
                                ),
                              }));
                              notify("Request updated");
                            }}
                          >
                            {["Submitted", "In progress", "Completed"].map(
                              (s) => (
                                <option key={s}>{s}</option>
                              ),
                            )}
                          </select>
                        )}
                      </article>
                    ))}
                    {!ownRequests.length && (
                      <Empty text="Your requests will appear here." />
                    )}
                  </div>
                </>
              }
            />
            <Route
              path="/clients"
              element={
                adviser ? (
                  <>
                    <PageHeading title="Your clients" />
                    <SearchInput
                      value={query}
                      onChange={setQuery}
                      placeholder="Search clients"
                    />
                    <div className="client-list">
                      {clients
                        .filter((c) =>
                          query.trim() &&
                          (c.name + c.email)
                            .toLowerCase()
                            .includes(query.toLowerCase()),
                        )
                        .map((c) => (
                          <article key={c.name}>
                            <span className="avatar">{c.initials}</span>
                            <div className="grow">
                              <h3>{c.name}</h3>
                              <p>{c.email}</p>
                            </div>
                            <div>
                              <span className="muted small">
                                Estimated net worth
                              </span>
                              <h3>{money(c.assets - c.liabilities)}</h3>
                            </div>
                            <button
                              className="button secondary"
                              onClick={() =>
                                setModal({ kind: "client", id: c.name })
                              }
                            >
                              View client <ArrowRight size={16} />
                            </button>
                          </article>
                        ))}
                    </div>
                  </>
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
            <Route
              path="/assistant"
              element={adviser ? <Assistant /> : <Navigate to="/" replace />}
            />
            <Route
              path="/inbox"
              element={
                adviser ? (
                  <Inbox data={data} update={update} notify={notify} />
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
            <Route
              path="/settings"
              element={
                <>
                  <PageHeading
                    title="Workspace settings"
                  />
                  <section className="settings-section">
                    <h2>Profile</h2>
                    <div className="row">
                      <span className="avatar large">
                        {adviser ? "QN" : profile.initials}
                      </span>
                      <div>
                        <h3>{adviser ? "Qiniso Ntuli" : client}</h3>
                        <p className="muted">
                          {adviser ? "Financial adviser" : profile.email}
                        </p>
                      </div>
                    </div>
                    <h2>Demo workspace</h2>
                    <Field label="View as">
                      <select
                        value={role}
                        onChange={(e) =>
                          switchRole(e.target.value as "client" | "adviser")
                        }
                      >
                        <option value="client">Client</option>
                        <option value="adviser">Adviser</option>
                      </select>
                    </Field>
                    <p className="muted small">
                      Synthetic records. Changes are saved in this browser. No
                      information is sent to Royal Square or an insurer.
                    </p>
                    <button
                      className="button secondary"
                      onClick={() =>
                        download(
                          "royal-square-demo.json",
                          JSON.stringify(data, null, 2),
                        )
                      }
                    >
                      <Download size={16} />
                      Export workspace
                    </button>
                  </section>
                </>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
      {toast && (
        <div className="toast" role="status">
          <Check size={17} />
          {toast}
          <IconButton
            icon={X}
            label="Dismiss notification"
            onClick={() => setToast("")}
          />
        </div>
      )}
      {modal && (
        <Modal
          title={
            modal.kind === "claim"
              ? "Register a motor claim"
              : modal.kind === "accident"
                ? "Accident & loss checklist"
                : modal.kind === "claim-detail"
                  ? "Claim details"
                  : modal.kind === "goal"
                    ? modal.id
                      ? "Update goal"
                      : "Create a goal"
                    : modal.kind === "reminder"
                      ? "Add a reminder"
                      : modal.kind === "policy"
                        ? "Policy details"
                        : modal.kind === "client"
                          ? "Client overview"
                          : modal.kind === "support"
                            ? "Here when you need us"
                            : "How can we help?"
          }
          close={() => setModal(null)}
        >
          {modal.kind === "accident" && (
            <Accident onContinue={() => setModal({ kind: "claim" })} />
          )}
          {modal.kind === "claim" && (
            <ClaimForm
              adviser={adviser}
              client={client}
              onSubmit={(c) => {
                update((d) => ({ ...d, claims: [c, ...d.claims] }));
                setModal({ kind: "claim-detail", id: c.id });
                notify("Claim registered in your demo workspace");
              }}
            />
          )}
          {modal.kind === "claim-detail" &&
            (() => {
              const c = data.claims.find((c) => c.id === modal.id);
              return c ? (
                <ClaimDetail
                  claim={c}
                  adviser={adviser}
                  save={(next) => {
                    update((d) => ({
                      ...d,
                      claims: d.claims.map((x) =>
                        x.id === next.id ? next : x,
                      ),
                    }));
                    notify("Claim updated");
                  }}
                />
              ) : null;
            })()}
          {["request", "consultation", "document-request"].includes(
            modal.kind,
          ) && (
            <RequestForm
              adviser={adviser}
              client={client}
              initial={
                modal.kind === "consultation"
                  ? "Consultation"
                  : modal.kind === "document-request"
                    ? "Policy document"
                    : requestTypes[0]
              }
              save={(values) => {
                update((d) => ({
                  ...d,
                  requests: [
                    {
                      id: uid("REQ"),
                      client: values.client,
                      type: values.type,
                      details: values.details,
                      date: today(),
                      status: "Submitted",
                    },
                    ...d.requests,
                  ],
                }));
                setModal(null);
                navigate("/requests");
                notify("Request submitted");
              }}
            />
          )}
          {modal.kind === "goal" && adviser && (
            <GoalForm
              goal={data.goals.find((g) => g.id === modal.id)}
              save={(g) => {
                update((d) => ({
                  ...d,
                  goals: d.goals.some((x) => x.id === g.id)
                    ? d.goals.map((x) => (x.id === g.id ? g : x))
                    : [...d.goals, g],
                }));
                setModal(null);
                notify("Goal saved");
              }}
            />
          )}
          {modal.kind === "reminder" && adviser && (
            <form
              className="form"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                update((d) => ({
                  ...d,
                  reminders: [
                    ...d.reminders,
                    {
                      id: uid("REM"),
                      client: String(f.get("client")),
                      title: String(f.get("title")).trim(),
                      date: String(f.get("date")),
                      recipient: String(f.get("recipient")),
                      done: false,
                    },
                  ],
                }));
                setModal(null);
                notify("Reminder added");
              }}
            >
              <ClientField />
              <Field label="Reminder">
                <input
                  name="title"
                  required
                  placeholder="e.g. Annual financial review"
                />
              </Field>
              <div className="form-grid">
                <Field label="Due date">
                  <input type="date" name="date" required min={today()} />
                </Field>
                <Field label="Notify">
                  <select name="recipient">
                    <option>Both</option>
                    <option>Client</option>
                    <option>Adviser</option>
                  </select>
                </Field>
              </div>
              <button className="button" type="submit">
                Save reminder
              </button>
            </form>
          )}
          {modal.kind === "policy" &&
            (() => {
              const p = policies.find((p) => p.id === modal.id)!;
              return (
                <div className="modal-body">
                  <Badge>Active</Badge>
                  <h2>{p.name}</h2>
                  <p>
                    {p.provider} · {p.id}
                  </p>
                  <p>{p.detail}</p>
                  <dl className="detail-list">
                    <div>
                      <dt>Cover / fund value</dt>
                      <dd>{money(p.cover)}</dd>
                    </div>
                    <div>
                      <dt>Monthly payment</dt>
                      <dd>{money(p.premium)}</dd>
                    </div>
                    <div>
                      <dt>Review date</dt>
                      <dd>{dateLabel(p.renewal)}</dd>
                    </div>
                  </dl>
                  <button
                    className="button secondary"
                    onClick={() =>
                      download(
                        `${p.id}-demo-summary.txt`,
                        `DEMO POLICY SUMMARY - NOT A POLICY CONTRACT\n${p.name}\n${p.provider}\n${p.id}\nCover / value: ${money(p.cover)}\nMonthly payment: ${money(p.premium)}\nReview: ${p.renewal}`,
                      )
                    }
                  >
                    <Download size={16} />
                    Download demo summary
                  </button>
                  <button
                    className="text-button block-button"
                    onClick={() => setModal({ kind: "document-request" })}
                  >
                    Request official policy document <ArrowRight size={15} />
                  </button>
                </div>
              );
            })()}
          {modal.kind === "client" && (
            <div className="modal-body">
              <h2>{modal.id}</h2>
              <p>{clients.find((c) => c.name === modal.id)?.email}</p>
              <div className="client-stats">
                <span>
                  <strong>
                    {
                      data.claims.filter(
                        (c) => c.client === modal.id && c.status < 6,
                      ).length
                    }
                  </strong>
                  Open claims
                </span>
                <span>
                  <strong>
                    {data.goals.filter((c) => c.client === modal.id).length}
                  </strong>
                  Goals
                </span>
                <span>
                  <strong>
                    {
                      data.requests.filter(
                        (c) =>
                          c.client === modal.id && c.status !== "Completed",
                      ).length
                    }
                  </strong>
                  Requests
                </span>
              </div>
              <h3>Recent activity</h3>
              {data.claims
                .filter((c) => c.client === modal.id)
                .map((c) => (
                  <button
                    className="client-claim"
                    key={c.id}
                    onClick={() => setModal({ kind: "claim-detail", id: c.id })}
                  >
                    {c.vehicle}
                    <Badge>{stages[c.status]}</Badge>
                    <ChevronRight size={16} />
                  </button>
                ))}
              <button
                className="button secondary"
                onClick={() => {
                  setClient(modal.id!);
                  setModal({ kind: "consultation" });
                }}
              >
                Schedule consultation
              </button>
            </div>
          )}
          {modal.kind === "support" && (
            <div className="modal-body">
              <span className="avatar large">QN</span>
              <h2>Qiniso Ntuli</h2>
              <p>Your Royal Square financial adviser</p>
              <a className="contact-line" href="tel:+27114921566">
                011 492 1566
              </a>
              <a className="contact-line" href="mailto:qiniso@royal-square.com">
                qiniso@royal-square.com
              </a>
              <p className="muted">
                1401 The Franklin, 4 Pritchard Street, Newtown
              </p>
              <button
                className="button"
                onClick={() => setModal({ kind: "consultation" })}
              >
                Request a consultation <ArrowRight size={16} />
              </button>
            </div>
          )}
        </Modal>
      )}
    </div>
  );
}

function PageHeading({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  );
}
function SearchInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (s: string) => void;
  placeholder: string;
}) {
  return (
    <label className="search-input">
      <Search size={17} />
      <input
        aria-label={placeholder}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {value && (
        <button aria-label="Clear search" onClick={() => onChange("")}>
          <X size={14} />
        </button>
      )}
    </label>
  );
}
function ClientField({ value }: { value?: string }) {
  return (
    <Field label="Client">
      <select name="client" defaultValue={value}>
        {clients.map((c) => (
          <option key={c.name}>{c.name}</option>
        ))}
      </select>
    </Field>
  );
}
function Accident({ onContinue }: { onContinue: () => void }) {
  const [checked, setChecked] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem("rs-checklist") || "[]");
    } catch {
      return [];
    }
  });
  return (
    <div className="modal-body">
      <div className="notice">
        <TriangleAlert size={20} />
        <div>
          <strong>Take a moment. Put your safety first.</strong>
          <p>
            Move to a safe place when possible. For an emergency, call{" "}
            <a href="tel:112">112</a>.
          </p>
        </div>
      </div>
      <p className="muted">
        Gather what you can. Your adviser will help with the next steps.
      </p>
      <div className="checklist">
        {checklist.map((text) => (
          <label key={text}>
            <input
              type="checkbox"
              checked={checked.includes(text)}
              onChange={(e) => {
                const next = e.target.checked
                  ? [...checked, text]
                  : checked.filter((x) => x !== text);
                setChecked(next);
                localStorage.setItem("rs-checklist", JSON.stringify(next));
              }}
            />
            <span>{text}</span>
          </label>
        ))}
      </div>
      <div className="notice neutral">
        <FileText size={18} />
        <p>
          Report the incident to the police promptly and confirm the applicable
          reporting deadline with your adviser.
        </p>
      </div>
      <div className="modal-actions">
        <span className="muted small">
          {checked.length} of {checklist.length} collected
        </span>
        <button className="button" onClick={onContinue}>
          Continue to claim <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
function ClaimForm({
  adviser,
  client,
  onSubmit,
}: {
  adviser: boolean;
  client: string;
  onSubmit: (c: Claim) => void;
}) {
  const [step, setStep] = useState(0);
  const [files, setFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState("");
  const {
    register,
    handleSubmit,
    trigger,
    formState: { errors },
  } = useForm<Record<string, string>>({
    defaultValues: { client, insurer: "Santam", use: "Personal" },
  });
  const steps = ["Incident", "People & parties", "Documents"];
  const next = async () => {
    const fields =
      step === 0
        ? ["vehicle", "date", "time", "location", "description"]
        : ["driver"];
    if (await trigger(fields)) setStep(step + 1);
  };
  return (
    <form
      className="form"
      onSubmit={handleSubmit((v) =>
        onSubmit({
          id: uid("CLM"),
          client: v.client || client,
          insurer: v.insurer,
          vehicle: v.vehicle,
          description: v.description,
          date: v.date,
          status: 0,
          files: files.map((f) => f.name),
          details: v,
          updates: [
            {
              date: today(),
              text: "Claim registered. Your adviser will review the incident details.",
            },
          ],
        }),
      )}
    >
      <div className="stepper">
        {steps.map((s, i) => (
          <div
            className={i === step ? "active" : i < step ? "complete" : ""}
            key={s}
          >
            <span>{i < step ? <Check size={13} /> : i + 1}</span>
            {s}
          </div>
        ))}
      </div>
      <div style={{ display: step === 0 ? "block" : "none" }}>
        {adviser && (
          <Field label="Client">
            <select {...register("client")}>
              {clients.map((c) => (
                <option key={c.name}>{c.name}</option>
              ))}
            </select>
          </Field>
        )}
        <div className="form-grid">
          <Field label="Insurer">
            <select {...register("insurer")}>
              <option>Santam</option>
              <option>Discovery</option>
              <option>Old Mutual</option>
              <option>Momentum</option>
              <option>Other</option>
            </select>
          </Field>
          <Field label="Vehicle">
            <input
              {...register("vehicle", { required: true })}
              placeholder="Year, make and model"
              aria-invalid={!!errors.vehicle}
            />
          </Field>
          <Field label="Incident date">
            <input
              type="date"
              max={today()}
              {...register("date", { required: true })}
              aria-invalid={!!errors.date}
            />
          </Field>
          <Field label="Incident time">
            <input
              type="time"
              {...register("time", { required: true })}
              aria-invalid={!!errors.time}
            />
          </Field>
        </div>
        <Field label="Location / cross streets">
          <input
            {...register("location", { required: true })}
            aria-invalid={!!errors.location}
          />
        </Field>
        <Field label="What happened?">
          <textarea
            rows={3}
            {...register("description", { required: true })}
            aria-invalid={!!errors.description}
          />
        </Field>
        <div className="form-grid">
          <Field label="Police notification">
            <select {...register("police")}>
              <option>Not yet reported</option>
              <option>Reported</option>
            </select>
          </Field>
          <Field label="Police case number (if available)">
            <input {...register("caseNumber")} />
          </Field>
        </div>
      </div>
      <div style={{ display: step === 1 ? "block" : "none" }}>
        <div className="form-grid">
          <Field label="Driver's full name">
            <input
              {...register("driver", { required: true })}
              aria-invalid={!!errors.driver}
            />
          </Field>
          <Field label="Vehicle use">
            <select {...register("use")}>
              <option>Personal</option>
              <option>Business</option>
            </select>
          </Field>
        </div>
        <Field label="Witness names and contact details">
          <textarea {...register("witnesses")} rows={2} />
        </Field>
        <h3>Other parties</h3>
        <Field label="Other vehicles or property involved">
          <textarea {...register("thirdPartyProperty")} rows={2} />
        </Field>
        <div className="form-grid">
          <Field label="Third-party name and contact">
            <input {...register("thirdPartyName")} />
          </Field>
          <Field label="Licence number">
            <input {...register("thirdPartyLicence")} />
          </Field>
          <Field label="Vehicle registration">
            <input {...register("thirdPartyRegistration")} />
          </Field>
          <Field label="Insurer and policy number">
            <input {...register("thirdPartyInsurance")} />
          </Field>
        </div>
      </div>
      <div style={{ display: step === 2 ? "block" : "none" }}>
        <h3>Supporting documents</h3>
        <p className="muted">
          Accident photos, your driver's licence, an accident sketch or a
          witness voice note.
        </p>
        <label className="upload-zone">
          <Plus size={26} />
          <strong>Add photos & documents</strong>
          <span>Images, PDF or audio · up to 10 MB per file</span>
          <input
            aria-label="Claim attachments"
            type="file"
            multiple
            accept="image/*,application/pdf,audio/*"
            onChange={(e) => {
              const selected = Array.from(e.target.files || []);
              const valid = selected.filter(
                (f) =>
                  f.size <= 10 * 1024 * 1024 &&
                  (/^(image|audio)\//.test(f.type) ||
                    f.type === "application/pdf"),
              );
              setFileError(
                valid.length < selected.length
                  ? "Some files were not added. Use images, PDF or audio up to 10 MB."
                  : "",
              );
              setFiles((old) => [...old, ...valid]);
              e.target.value = "";
            }}
          />
        </label>
        {fileError && (
          <p className="error" role="alert">
            {fileError}
          </p>
        )}
        {files.map((f, i) => (
          <div className="file-row" key={i}>
            <FileText size={16} />
            <span>{f.name}</span>
            <IconButton
              icon={X}
              label={`Remove ${f.name}`}
              onClick={() => setFiles(files.filter((_, j) => j !== i))}
            />
          </div>
        ))}
        <p className="small muted">
          Demo: attachment names are saved; file contents are not uploaded or
          retained.
        </p>
      </div>
      {Object.keys(errors).length > 0 && (
        <p className="error" role="alert">
          Please complete the highlighted required fields.
        </p>
      )}
      <div className="modal-actions">
        <button
          type="button"
          className="button secondary"
          disabled={step === 0}
          onClick={() => setStep(step - 1)}
        >
          Back
        </button>
        {step < 2 ? (
          <button
            key="next"
            type="button"
            className="button"
            onClick={(event) => {
              event.preventDefault();
              void next();
            }}
          >
            Continue <ArrowRight size={16} />
          </button>
        ) : (
          <button key="submit" type="submit" className="button">
            Submit claim <Check size={16} />
          </button>
        )}
      </div>
    </form>
  );
}
function ClaimDetail({
  claim: c,
  adviser,
  save,
}: {
  claim: Claim;
  adviser: boolean;
  save: (c: Claim) => void;
}) {
  return (
    <div className="modal-body">
      <div className="row between">
        <span className="muted small">{c.id}</span>
        <Badge>{stages[c.status]}</Badge>
      </div>
      <h2>{c.vehicle}</h2>
      <p>
        {c.client} · {c.insurer} · {dateLabel(c.date)}
      </p>
      <p>{c.description}</p>
      <div className="claim-timeline">
        {stages.map((s, i) => (
          <div className={i <= c.status ? "done" : ""} key={s}>
            <span>{i < c.status ? <Check size={12} /> : i + 1}</span>
            <p>{s}</p>
          </div>
        ))}
      </div>
      <details>
        <summary>Incident information & attachments</summary>
        <dl className="detail-list">
          {Object.entries(c.details)
            .filter(([, v]) => v)
            .map(([k, v]) => (
              <div key={k}>
                <dt>{k.replace(/([A-Z])/g, " $1")}</dt>
                <dd>{v}</dd>
              </div>
            ))}
        </dl>
        {c.files.map((f, i) => (
          <div className="file-row" key={i}>
            <FileText size={16} />
            {f}
            <span className="muted small">Demo reference</span>
          </div>
        ))}
      </details>
      {adviser && (
        <form
          className="claim-update"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            const note = String(f.get("note")).trim();
            save({
              ...c,
              status: Number(f.get("status")),
              details: {
                ...c.details,
                insurerReference: String(f.get("insurerReference")),
                handler: String(f.get("handler")),
                repairer: String(f.get("repairer")),
                repairDate: String(f.get("repairDate")),
                hireCar: String(f.get("hireCar")),
              },
              updates: [
                {
                  date: today(),
                  text:
                    note ||
                    `Status updated to ${stages[Number(f.get("status"))]}.`,
                },
                ...c.updates,
              ],
            });
          }}
        >
          <h3>Manage claim</h3>
          <Field label="Status">
            <select name="status" defaultValue={c.status} key={c.status}>
              {stages.map((s, i) => (
                <option value={i} key={s}>
                  {s}
                </option>
              ))}
            </select>
          </Field>
          <div className="form-grid">
            <Field label="Insurer claim number">
              <input
                name="insurerReference"
                defaultValue={c.details.insurerReference}
              />
            </Field>
            <Field label="Claims handler">
              <input name="handler" defaultValue={c.details.handler} />
            </Field>
            <Field label="Repairer / collection location">
              <input name="repairer" defaultValue={c.details.repairer} />
            </Field>
            <Field label="Repair booking date">
              <input
                name="repairDate"
                type="date"
                defaultValue={c.details.repairDate}
              />
            </Field>
          </div>
          <Field label="Hire car / delivery / return arrangements">
            <input name="hireCar" defaultValue={c.details.hireCar} />
          </Field>
          <Field label="Client update">
            <textarea
              name="note"
              placeholder="Add an assessment, repair or collection update"
            />
          </Field>
          <button className="button" type="submit">
            Save update
          </button>
        </form>
      )}
      <h3 className="activity-heading">Latest updates</h3>
      <div className="activity-list">
        {c.updates.map((u, i) => (
          <div key={i}>
            <i />
            <div>
              <strong>{u.text}</strong>
              <span>{dateLabel(u.date)}</span>
            </div>
          </div>
        ))}
      </div>
      {!adviser && c.status === 5 && !c.review && (
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            save({
              ...c,
              status: 6,
              review: String(f.get("review")),
              updates: [
                {
                  date: today(),
                  text: "Vehicle collected. Client review received and claim closed.",
                },
                ...c.updates,
              ],
            });
          }}
        >
          <Field label="How was your claims experience?">
            <textarea name="review" required />
          </Field>
          <button className="button">Confirm collection & close claim</button>
        </form>
      )}
      {c.review && <p className="notice neutral">Client review: {c.review}</p>}
    </div>
  );
}
function RequestForm({
  adviser,
  client,
  initial,
  save,
}: {
  adviser: boolean;
  client: string;
  initial: string;
  save: (v: { client: string; type: string; details: string }) => void;
}) {
  const [type, setType] = useState(initial);
  return (
    <form
      className="form"
      onSubmit={(e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        const extra = Array.from(f.entries())
          .filter(([k]) => !["client", "type", "details"].includes(k))
          .map(([k, v]) => `${k}: ${v}`)
          .join("\n");
        save({
          client: String(f.get("client") || client),
          type,
          details: [String(f.get("details")), extra].filter(Boolean).join("\n"),
        });
      }}
    >
      {adviser && <ClientField value={client} />}
      <Field label="Request type">
        <select
          name="type"
          value={type}
          onChange={(e) => setType(e.target.value)}
        >
          {requestTypes.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </Field>
      {type === "Change of address" && (
        <Field label="New address">
          <textarea name="Address" required />
        </Field>
      )}
      {type === "Change of bank details" && (
        <div className="notice neutral">
          <ShieldCheck size={18} />
          <p>
            Your adviser will arrange secure verification. Please do not enter
            account numbers here.
          </p>
        </div>
      )}
      {type === "Consultation" && (
        <div className="form-grid">
          <Field label="Preferred date">
            <input name="Preferred date" type="date" required min={today()} />
          </Field>
          <Field label="Meeting format">
            <select name="Format">
              <option>Video call</option>
              <option>Phone call</option>
              <option>In person</option>
            </select>
          </Field>
        </div>
      )}
      {["Policy document", "Border letter", "IRP5 certificate"].includes(
        type,
      ) && (
        <Field label="Policy / investment">
          <select name="Policy">
            {policies.map((p) => (
              <option key={p.id}>
                {p.provider} - {p.name}
              </option>
            ))}
          </select>
        </Field>
      )}
      {type === "Border letter" && (
        <div className="form-grid">
          <Field label="Destination country">
            <input name="Destination" required />
          </Field>
          <Field label="Travel date">
            <input type="date" name="Travel date" min={today()} required />
          </Field>
        </div>
      )}
      {type === "IRP5 certificate" && (
        <Field label="Tax year">
          <input
            type="number"
            name="Tax year"
            min="2000"
            max="2100"
            defaultValue={2026}
            required
          />
        </Field>
      )}
      {type === "Financial information" && (
        <div className="form-grid">
          {[
            "Total assets",
            "Total liabilities",
            "Monthly income",
            "Monthly expenses",
          ].map((s) => (
            <Field key={s} label={`${s} (R)`}>
              <input type="number" name={s} min="0" required />
            </Field>
          ))}
        </div>
      )}
      <Field label="Additional details">
        <textarea
          name="details"
          rows={3}
          required={["Change of bank details"].includes(type)}
          placeholder="Anything your adviser should know?"
        />
      </Field>
      <button className="button" type="submit">
        Submit request <ArrowRight size={16} />
      </button>
    </form>
  );
}
function GoalForm({ goal, save }: { goal?: Goal; save: (g: Goal) => void }) {
  return (
    <form
      className="form"
      onSubmit={(e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        save({
          id: goal?.id || uid("GOAL"),
          name: String(f.get("name")).trim(),
          client: String(f.get("client")),
          current: Number(f.get("current")),
          target: Number(f.get("target")),
          date: String(f.get("date")),
          shared: f.get("shared") === "on",
        });
      }}
    >
      <ClientField value={goal?.client} />
      <Field label="Goal name">
        <input name="name" required defaultValue={goal?.name} />
      </Field>
      <div className="form-grid">
        <Field label="Saved so far (R)">
          <input
            name="current"
            type="number"
            min="0"
            step="0.01"
            required
            defaultValue={goal?.current || 0}
          />
        </Field>
        <Field label="Target amount (R)">
          <input
            name="target"
            type="number"
            min="1"
            step="0.01"
            required
            defaultValue={goal?.target}
          />
        </Field>
      </div>
      <Field label="Target date">
        <input name="date" type="date" required defaultValue={goal?.date} />
      </Field>
      <label className="checkbox-label">
        <input name="shared" type="checkbox" defaultChecked={goal?.shared} />
        Shared household goal
      </label>
      <button className="button" type="submit">
        Save goal
      </button>
    </form>
  );
}

const demoSources = [
  {
    title: "Motor claims demo guide",
    page: 1,
    text: "After registration, the adviser records the insurer claim number and handler. The vehicle is assessed, quotes are submitted, and insurer authorisation is recorded before repairs begin.",
  },
  {
    title: "Motor claims demo guide",
    page: 2,
    text: "The adviser records the repair booking, arranges hire car and delivery, and provides weekly repair updates. At collection, the hire car return is arranged. The client then reviews the experience and closes the claim.",
  },
  {
    title: "Client service demo guide",
    page: 1,
    text: "Clients can request policy documents, border letters, IRP5 certificates, consultations, address changes, and bank detail verification. Financial information can be collected as assets, liabilities, income and expenses.",
  },
];
function Assistant() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<
    { question: string; answer: string; source?: number }[]
  >([]);
  const [source, setSource] = useState<number | null>(null);
  const ask = (q: string) => {
    if (!q.trim()) return;
    const lower = q.toLowerCase();
    const idx = /hire|repair|collection/.test(lower)
      ? 1
      : /claim|assessment/.test(lower)
        ? 0
        : /request|document|irp5|address|bank/.test(lower)
          ? 2
          : -1;
    setMessages((m) => [
      ...m,
      {
        question: q,
        answer:
          idx < 0
            ? "I could not find support for this question in the demo library. Please review an approved source with your adviser."
            : demoSources[idx].text,
        ...(idx < 0 ? {} : { source: idx }),
      },
    ]);
    setQuestion("");
  };
  return (
    <>
      <PageHeading title="Document assistant" />
      <div className="assistant-layout">
        <section className="chat">
          <div className="chat-label">
            <Sparkles size={17} />
            <strong>Royal Square assistant</strong>
            <Badge tone="gray">Demo responses</Badge>
          </div>
          <div className="chat-messages">
            {!messages.length && (
              <div className="chat-welcome">
                <span className="assistant-symbol">
                  <Sparkles size={28} />
                </span>
                <h2>What would you like to find?</h2>
                <p>Search the sample claims and client service guides.</p>
                {[
                  "What happens after a claim is submitted?",
                  "How is a hire car arranged?",
                  "Which documents can a client request?",
                ].map((q) => (
                  <button key={q} onClick={() => ask(q)}>
                    {q}
                    <ArrowUpRight size={16} />
                  </button>
                ))}
              </div>
            )}
            {messages.map((m, i) => (
              <div className="chat-exchange" key={i}>
                <p className="user-message">{m.question}</p>
                <div className="assistant-message">
                  <Sparkles size={19} />
                  <div>
                    <p>{m.answer}</p>
                    {m.source !== undefined && (
                      <button
                        className="citation"
                        onClick={() => setSource(m.source!)}
                      >
                        <FileText size={14} />
                        {demoSources[m.source].title} · p.{" "}
                        {demoSources[m.source].page}
                        <ArrowUpRight size={13} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <form
            className="chat-input"
            onSubmit={(e) => {
              e.preventDefault();
              ask(question);
            }}
          >
            <input
              aria-label="Ask the document assistant"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about a claim or client request..."
            />
            <button
              className="button"
              aria-label="Send question"
              disabled={!question.trim()}
            >
              <Send size={18} />
            </button>
          </form>
          <p className="chat-disclaimer">
            Sample documents only. Live document search is not connected.
          </p>
        </section>
        <aside className="source-library">
          <h3>Reference library</h3>
          <p className="muted small">2 demo guides · 3 reference pages</p>
          {demoSources.map((s, i) => (
            <button
              className={source === i ? "selected" : ""}
              key={i}
              onClick={() => setSource(i)}
            >
              <FileText size={20} />
              <span>
                <strong>{s.title}</strong>
                <small>Page {s.page}</small>
              </span>
            </button>
          ))}
          {source !== null && (
            <div className="source-excerpt">
              <Badge tone="gray">Demo source</Badge>
              <h3>{demoSources[source].title}</h3>
              <p>{demoSources[source].text}</p>
              <span className="muted small">
                Page {demoSources[source].page}
              </span>
            </div>
          )}
        </aside>
      </div>
    </>
  );
}
const emails = [
  {
    id: "e1",
    from: "Sarah Jacobs",
    company: "Santam claims",
    subject: "Repair authorisation · CLM-2026-014",
    body: "The repair quote for Thando Mokoena has been authorised. Please confirm the repair booking and hire car arrangements.",
    client: "Thando Mokoena",
    claim: "CLM-2026-014",
    time: "09:42",
    important: true,
  },
  {
    id: "e2",
    from: "Thando Mokoena",
    company: "Client",
    subject: "Our annual review",
    body: "Hi Qiniso, could we schedule a review of my policies and savings goals next week? A video call would work well for me.",
    client: "Thando Mokoena",
    claim: "",
    time: "08:30",
    important: false,
  },
  {
    id: "e3",
    from: "Claims team",
    company: "Discovery",
    subject: "Assessment required · CLM-2026-012",
    body: "Please arrange the windscreen assessment and share the report when available.",
    client: "Lerato Dlamini",
    claim: "CLM-2026-012",
    time: "Yesterday",
    important: true,
  },
];
function Inbox({
  data,
  update,
  notify,
}: {
  data: Store;
  update: (fn: (d: Store) => Store) => void;
  notify: (s: string) => void;
}) {
  const [selected, setSelected] = useState("e1");
  const [filter, setFilter] = useState("All");
  const email = emails.find((e) => e.id === selected)!;
  const [draft, setDraft] = useState(data.drafts[selected] || "");
  useEffect(() => setDraft(data.drafts[selected] || ""), [selected]);
  return (
    <>
      <PageHeading
        title="Your inbox, in focus"
        action={<Badge tone="gray">Sample inbox · Gmail not connected</Badge>}
      />
      <div className="inbox-layout">
        <section className="email-list">
          <div className="tabs">
            {["All", "Important"].map((f) => (
              <button
                className={filter === f ? "selected" : ""}
                key={f}
                onClick={() => setFilter(f)}
              >
                {f}
              </button>
            ))}
          </div>
          {emails
            .filter((e) => filter === "All" || e.important)
            .map((e) => (
              <button
                key={e.id}
                className={e.id === selected ? "selected" : ""}
                onClick={() => setSelected(e.id)}
              >
                <div className="row between">
                  <strong>{e.from}</strong>
                  <small>{e.time}</small>
                </div>
                <h3>{e.subject}</h3>
                <p>{e.body}</p>
                {e.important && (
                  <span className="important-label">Important</span>
                )}
              </button>
            ))}
        </section>
        <section className="email-detail">
          <h2>{email.subject}</h2>
          <p className="muted">
            {email.from} · {email.company}
          </p>
          <div className="email-context">
            <Users size={15} />
            {email.client}
            {email.claim && (
              <>
                <ClipboardList size={15} />
                {email.claim}
              </>
            )}
          </div>
          <p className="email-body">{email.body}</p>
          <div className="row between">
            <h3>Reply draft</h3>
            <button
              className="text-button"
              onClick={() =>
                setDraft(
                  `Hi ${email.from.split(" ")[0]},\n\nThank you for your message. ${email.id === "e1" ? "I will confirm the repair booking and hire car arrangements with Thando and follow up with the details." : email.id === "e2" ? "I would be happy to arrange your annual review. Please let me know your preferred day and time next week." : "I will coordinate the assessment with Lerato and share the report once available."}\n\nKind regards,\nQiniso Ntuli\nRoyal Square Financial`,
                )
              }
            >
              <Sparkles size={15} />
              Prepare demo draft
            </button>
          </div>
          <textarea
            aria-label="Reply draft"
            rows={9}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Write a reply..."
          />
          <div className="modal-actions">
            <span className="muted small">
              Drafts only. No emails are sent.
            </span>
            <button
              className="button"
              disabled={!draft.trim()}
              onClick={() => {
                update((d) => ({
                  ...d,
                  drafts: { ...d.drafts, [selected]: draft },
                }));
                notify("Draft saved");
              }}
            >
              Save draft
            </button>
          </div>
        </section>
      </div>
    </>
  );
}
