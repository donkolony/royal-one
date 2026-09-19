import { Briefcase, User } from "lucide-react";
import { isMock } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

/**
 * DevLoginBanner — only visible in offline mock mode (VITE_API_URL empty or "mock").
 * Renders a fixed bottom-right panel to quickly "sign in" as a client or an adviser.
 * Never appears with a real backend, and it holds no tokens.
 */
export default function DevLoginBanner() {
  const { session, devRole, setDevRole, signOut, profile } = useAuth();

  if (!isMock()) return null;

  return (
    <div className="fixed bottom-20 right-4 md:bottom-4 z-[9999] bg-charcoal-800 text-white rounded-xl shadow-2xl border border-brand-500/40 p-4 w-72 max-w-[calc(100vw-2rem)] text-sm font-sans">
      <div className="flex items-center gap-2 mb-3">
        {/* Pulsing dot */}
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-brand-500" />
        </span>
        <span className="font-semibold text-brand-400 tracking-wide uppercase text-xs">
          Dev Mode — Mock Data
        </span>
      </div>

      {session && devRole ? (
        <>
          <p className="text-charcoal-300 mb-3">
            Signed in as{" "}
            <span className="font-semibold text-white">{profile?.full_name}</span>
            <span className="ml-1.5 text-xs text-charcoal-400">({devRole})</span>
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setDevRole(devRole === "client" ? "advisor" : "client")}
              className="flex-1 px-3 py-1.5 bg-charcoal-700 hover:bg-charcoal-600 rounded-lg text-xs font-medium transition-colors"
            >
              Switch to {devRole === "client" ? "Adviser" : "Client"}
            </button>
            <button
              type="button"
              onClick={() => void signOut()}
              className="px-3 py-1.5 bg-danger/80 hover:bg-danger rounded-lg text-xs font-medium transition-colors"
            >
              Sign out
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="text-charcoal-300 mb-3">Choose a role to view the app:</p>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setDevRole("client")}
              className="flex flex-col items-center gap-1 px-3 py-3 bg-charcoal-700 hover:bg-brand-600 rounded-lg transition-colors"
            >
              <User className="w-5 h-5" aria-hidden="true" />
              <span className="font-semibold text-xs">Client</span>
              <span className="text-charcoal-400 text-[10px]">Thabo Mokoena</span>
            </button>
            <button
              type="button"
              onClick={() => setDevRole("advisor")}
              className="flex flex-col items-center gap-1 px-3 py-3 bg-charcoal-700 hover:bg-brand-600 rounded-lg transition-colors"
            >
              <Briefcase className="w-5 h-5" aria-hidden="true" />
              <span className="font-semibold text-xs">Adviser</span>
              <span className="text-charcoal-400 text-[10px]">Sarah van der Merwe</span>
            </button>
          </div>
        </>
      )}
    </div>
  );
}
