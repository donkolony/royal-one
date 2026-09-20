import type { ReactNode } from "react";
import { LayoutDashboard, Users, FileText, HelpCircle, Bell, MessageSquare, Mail, Gauge, Target, ShieldCheck, ScrollText, Lock, type LucideIcon } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import type { Role } from "../lib/types";
import WorkspaceLayout from "./WorkspaceLayout";

const ICON = "w-5 h-5";
type NavItem = { label: string; path: string; icon: ReactNode; end: boolean };

/** One layout for both staff roles. The owner starts on Business Health; an adviser starts on their dashboard. */
function navFor(role: Role): NavItem[] {
  const base = role === "owner" ? "/owner" : "/advisor";
  const i = (C: LucideIcon) => <C className={ICON} aria-hidden="true" />;
  if (role === "owner") {
    return [
      { label: "Business health", path: base, icon: i(Gauge), end: true },
      { label: "Opportunities", path: `${base}/radar`, icon: i(Target), end: false },
      { label: "Clients", path: `${base}/clients`, icon: i(Users), end: false },
      { label: "Claims", path: `${base}/claims`, icon: i(FileText), end: false },
      { label: "Compliance", path: `${base}/compliance`, icon: i(ShieldCheck), end: false },
      { label: "Audit log", path: `${base}/audit`, icon: i(ScrollText), end: false },
      { label: "Privacy", path: `${base}/privacy`, icon: i(Lock), end: false },
    ];
  }
  return [
    { label: "Dashboard", path: base, icon: i(LayoutDashboard), end: true },
    { label: "Opportunities", path: `${base}/radar`, icon: i(Target), end: false },
    { label: "Clients", path: `${base}/clients`, icon: i(Users), end: false },
    { label: "Claims", path: `${base}/claims`, icon: i(FileText), end: false },
    { label: "Requests", path: `${base}/requests`, icon: i(HelpCircle), end: false },
    { label: "Reminders", path: `${base}/reminders`, icon: i(Bell), end: false },
    { label: "Assistant", path: `${base}/assistant`, icon: i(MessageSquare), end: false },
    { label: "Email", path: `${base}/email`, icon: i(Mail), end: false },
    { label: "Compliance", path: `${base}/compliance`, icon: i(ShieldCheck), end: false },
    { label: "Audit log", path: `${base}/audit`, icon: i(ScrollText), end: false },
    { label: "Privacy", path: `${base}/privacy`, icon: i(Lock), end: false },
  ];
}

/** Layout route for every staff page (adviser or owner): `<Route element={<StaffLayout />}>` renders the matched page in <Outlet />. */
export default function StaffLayout() {
  const { profile } = useAuth();
  const role: Role = profile?.role ?? "advisor";
  return <WorkspaceLayout items={navFor(role)} home={role === "owner" ? "/owner" : "/advisor"} />;
}
