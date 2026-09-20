import WorkspaceLayout from "./WorkspaceLayout";
import { Home, FileText, Target, Bell, HelpCircle, Shield, User, ShieldCheck, ScrollText } from "lucide-react";

const navItems = [
  { label: "Dashboard", path: "/dashboard", icon: <Home className="w-5 h-5" aria-hidden="true" />, end: true },
  { label: "Policies", path: "/policies", icon: <Shield className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Claims", path: "/claims", icon: <FileText className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Goals", path: "/goals", icon: <Target className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Reminders", path: "/reminders", icon: <Bell className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Requests", path: "/requests", icon: <HelpCircle className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Identity", path: "/identity", icon: <ShieldCheck className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "My record", path: "/my-record", icon: <ScrollText className="w-5 h-5" aria-hidden="true" />, end: false },
  { label: "Profile", path: "/profile", icon: <User className="w-5 h-5" aria-hidden="true" />, end: false },
];

/** Layout route for every client page: `<Route element={<ClientLayout />}>` renders the matched page in <Outlet />. */
export default function ClientLayout() {
  return <WorkspaceLayout items={navItems} home="/dashboard" />;
}
