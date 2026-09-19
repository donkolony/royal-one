import { createClient, type Session } from "@supabase/supabase-js";

// Only the PUBLIC project URL and the publishable (anon) key belong in the browser.
// Set them in frontend/.env.local (see .env.example). Nothing secret lives in this file.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

/** False when the env vars are missing (fine in mock mode; sign-in cannot work without them). */
export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

// Placeholders keep the app importable in mock mode; no request is made with them.
export const supabase = createClient(
  supabaseUrl || "https://placeholder.supabase.co",
  supabaseAnonKey || "placeholder",
);

/** Dispatched on window when the stored session had to be dropped without a SIGNED_OUT event. */
export const AUTH_CLEARED_EVENT = "rs:auth-cleared";

export const getSession = async (): Promise<Session | null> => {
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  return data.session;
};

/** The current Supabase access token, or null when signed out. supabase-js refreshes it when it is about to expire. */
export const getAccessToken = async (): Promise<string | null> => {
  const session = await getSession();
  return session?.access_token ?? null;
};

/** Ask Supabase for a fresh session (used once after a 401 token_expired). Returns false when that failed. */
export const refreshSession = async (): Promise<boolean> => {
  try {
    const { data, error } = await supabase.auth.refreshSession();
    return !error && Boolean(data.session);
  } catch {
    return false;
  }
};

function storedSessionKey(): string | null {
  if (!supabaseUrl) return null;
  try {
    return `sb-${new URL(supabaseUrl).hostname.split(".")[0]}-auth-token`;
  } catch {
    return null;
  }
}

/** Remove the persisted session by hand. Used only when supabase.auth.signOut() could not finish (offline). */
function clearStoredSession(): void {
  const key = storedSessionKey();
  try {
    if (key) localStorage.removeItem(key);
  } catch {
    // storage blocked: nothing persisted anyway
  }
  window.dispatchEvent(new Event(AUTH_CLEARED_EVENT));
}

/**
 * Sign out of this browser. Local scope: it never depends on the network, and the auth state listener in
 * AuthContext then clears the profile and the query cache, so the router sends the user to /sign-in.
 * No hard page reload.
 */
export const signOut = async (): Promise<void> => {
  try {
    const { error } = await supabase.auth.signOut({ scope: "local" });
    if (!error) return;
  } catch {
    // fall through to the manual clean-up
  }
  clearStoredSession();
};
