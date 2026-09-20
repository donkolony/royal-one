import { Suspense, useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { ChevronRight, LogOut, Menu, MoreHorizontal, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { NotificationBell } from "../components/NotificationBell";
import { ErrorBoundary, PageLoader } from "../components/ui";

type Item = { label: string; path: string; icon: ReactNode; end: boolean };
export default function WorkspaceLayout({ items, home }: { items: Item[]; home: string }) {
  const { profile, signOut } = useAuth();
  const location = useLocation();
  const [mobile, setMobile] = useState(false);
  const [more, setMore] = useState(false);
  const primaryLabels = profile?.role === "client"
    ? ["Dashboard", "Claims", "Goals", "Reminders"]
    : profile?.role === "owner" ? ["Business health", "Opportunities", "Clients", "Claims"]
    : ["Dashboard", "Claims", "Clients", "Reminders"];
  const primary = primaryLabels.flatMap(label => items.filter(item => item.label === label));
  const secondary = items.filter(item => !primary.includes(item));
  const current = [...items].sort((a,b) => b.path.length-a.path.length).find(item => location.pathname === item.path || (!item.end && location.pathname.startsWith(item.path + "/")));
  useEffect(() => { setMobile(false); }, [location.pathname]);
  useEffect(() => {
    if (!mobile) return;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") setMobile(false); };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [mobile]);
  const navLink = (item: Item) => <NavLink key={item.path} to={item.path} end={item.end}>{item.icon}<span>{item.label === "Dashboard" ? "Overview" : item.label}</span></NavLink>;
  return <div className="app-shell">
    <a className="sr-only focus:not-sr-only" href="#main-content">Skip to content</a>
    <aside className={`sidebar ${mobile ? "open" : ""}`} id="workspace-navigation">
      <Link className="brand" to={home}><img className="brand-logo" src="/brand/royal-square-logo.png" alt="Royal Square Financial" /></Link>
      <div className="workspace-label">YOUR WORKSPACE</div>
      <nav aria-label="Main navigation">
        {primary.map(navLink)}
        <button className={`more-nav-button ${secondary.includes(current!) ? "active" : ""}`} aria-expanded={more} onClick={() => setMore(!more)}><MoreHorizontal size={19}/><span>More</span><ChevronRight className={`more-chevron ${more ? "open" : ""}`} size={16}/></button>
        {more && <div className="more-nav-items">{secondary.map(navLink)}</div>}
      </nav>
      <div className="sidebar-bottom">
        <button className="support-link" onClick={() => void signOut()}><LogOut size={18}/>Sign out</button>
        <div className="sidebar-footer">Royal Square Financial <span>FSP 29370</span></div>
      </div>
    </aside>
    {mobile && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setMobile(false)}/>}
    <div className="main-shell">
      <header className="topbar">
        <div className="row"><button className="icon-button mobile-menu" aria-label={mobile ? "Close navigation" : "Open navigation"} aria-expanded={mobile} aria-controls="workspace-navigation" onClick={() => setMobile(!mobile)}>{mobile ? <X size={22}/> : <Menu size={22}/>}</button><span className="breadcrumb"><span className="breadcrumb-prefix">Workspace</span><ChevronRight size={14}/><strong>{current?.label === "Dashboard" ? "Overview" : current?.label ?? "Workspace"}</strong></span></div>
        <div className="topbar-right"><NotificationBell/><span className="avatar" title={profile?.full_name}>{profile?.full_name.split(" ").map(p => p[0]).slice(0,2).join("")}</span></div>
      </header>
      <main id="main-content" className="content feature-content" tabIndex={-1}>
        <ErrorBoundary resetKey={location.pathname}><Suspense fallback={<PageLoader fullScreen={false}/>}><Outlet/></Suspense></ErrorBoundary>
      </main>
    </div>
  </div>;
}
