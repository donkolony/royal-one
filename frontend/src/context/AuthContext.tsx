import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { AUTH_CLEARED_EVENT, signOut as supabaseSignOut, supabase } from "../lib/supabase";
import { get, isMock } from "../lib/api";
import { queryClient } from "../lib/queryClient";
import { getMockProfile, getMockRole, setMockRole } from "../lib/mock";
import type { Profile, Role } from "../lib/types";

type ProfileStatus = "idle" | "loading" | "ready" | "error";

interface ProfileState {
  /** The auth user this state belongs to (a profile is never shown for a different user). */
  userId: string | null;
  status: ProfileStatus;
  profile: Profile | null;
  error: Error | null;
}

const IDLE: ProfileState = { userId: null, status: "idle", profile: null, error: null };

export interface AuthContextValue {
  /** The Supabase session (null when signed out). */
  session: Session | null;
  /** The caller's GET /me profile. null while loading, when signed out, or when /me failed (see profileError). */
  profile: Profile | null;
  /** True while the session or the profile is still being resolved. Do not redirect while true. */
  loading: boolean;
  /** Set when a session exists but GET /me failed (403 not provisioned, 502, network...). Show an error screen. */
  profileError: Error | null;
  /** Load the profile again ("Try again"). */
  refreshProfile: () => void;
  /** Sign out of this browser and clear cached data. */
  signOut: () => Promise<void>;
  /** Mock mode only (VITE_API_URL empty or "mock"): the role picked in the dev panel. Always null otherwise. */
  devRole: Role | null;
  /** Mock mode only: "sign in" as that role. No-op with a real backend. */
  setDevRole: (role: Role) => void;
}

const AuthContext = createContext<AuthContextValue>({
  session: null,
  profile: null,
  loading: true,
  profileError: null,
  refreshProfile: () => {},
  signOut: async () => {},
  devRole: null,
  setDevRole: () => {},
});

/** Stand-in session for mock mode. It is not a token and is never sent anywhere. */
function mockSession(profile: Profile): Session {
  return {
    access_token: "mock-mode",
    refresh_token: "mock-mode",
    expires_in: 3600,
    token_type: "bearer",
    user: { id: profile.id, email: profile.email },
  } as unknown as Session;
}

function toError(value: unknown): Error {
  return value instanceof Error ? value : new Error(typeof value === "string" ? value : "Could not load your profile.");
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const mock = isMock();

  const [session, setSession] = useState<Session | null>(null);
  const [sessionReady, setSessionReady] = useState(mock);
  const [profileState, setProfileState] = useState<ProfileState>(IDLE);
  const [reloadKey, setReloadKey] = useState(0);
  const [devRole, setDevRoleState] = useState<Role | null>(() => (mock ? getMockRole() : null));
  const lastUserId = useRef<string | null>(null);

  // A leftover "dev_role" from the old dev bypass must never influence a real session.
  useEffect(() => {
    if (mock) return;
    try {
      sessionStorage.removeItem("dev_role");
    } catch {
      // storage blocked: nothing to clean
    }
  }, [mock]);

  // 1. Session: read the stored one, then follow every change (sign in, sign out, refresh, other tabs).
  useEffect(() => {
    if (mock) return;
    let active = true;

    const { data } = supabase.auth.onAuthStateChange((event, next) => {
      if (!active) return;
      setSession(next);
      setSessionReady(true);
      if (event === "SIGNED_OUT") queryClient.clear();
    });
    supabase.auth
      .getSession()
      .then(({ data: current }) => {
        if (!active) return;
        setSession((prev) => prev ?? current.session);
        setSessionReady(true);
      })
      .catch(() => {
        if (active) setSessionReady(true);
      });

    // signOut() had to drop the stored session by hand (no SIGNED_OUT event fired)
    const onCleared = () => {
      if (!active) return;
      setSession(null);
      queryClient.clear();
    };
    window.addEventListener(AUTH_CLEARED_EVENT, onCleared);

    return () => {
      active = false;
      data.subscription.unsubscribe();
      window.removeEventListener(AUTH_CLEARED_EVENT, onCleared);
    };
  }, [mock]);

  // 2. Profile: GET /me whenever the signed-in user changes (not on every token refresh) or on "Try again".
  const userId = session?.user?.id ?? null;
  useEffect(() => {
    if (mock) return;

    // Never let one user's cached data reach the next user.
    if (lastUserId.current && lastUserId.current !== userId) queryClient.clear();
    lastUserId.current = userId;

    if (!userId) {
      setProfileState(IDLE);
      return;
    }

    let active = true;
    setProfileState((prev) => ({
      userId,
      status: "loading",
      profile: prev.userId === userId ? prev.profile : null,
      error: null,
    }));
    get<Profile>("/me").then(
      (profile) => {
        if (active) setProfileState({ userId, status: "ready", profile, error: null });
      },
      (error: unknown) => {
        if (active) setProfileState({ userId, status: "error", profile: null, error: toError(error) });
      },
    );
    return () => {
      active = false;
    };
  }, [mock, userId, reloadKey]);

  const refreshProfile = useCallback(() => setReloadKey((k) => k + 1), []);

  const signOut = useCallback(async () => {
    if (mock) {
      setMockRole(null);
      setDevRoleState(null);
      queryClient.clear();
      return;
    }
    await supabaseSignOut();
    setSession(null);
    queryClient.clear();
  }, [mock]);

  const setDevRole = useCallback(
    (role: Role) => {
      if (!mock) return;
      setMockRole(role);
      setDevRoleState(role);
      queryClient.clear();
    },
    [mock],
  );

  const value = useMemo<AuthContextValue>(() => {
    if (mock) {
      const profile = devRole ? getMockProfile(devRole) : null;
      return {
        session: profile ? mockSession(profile) : null,
        profile,
        loading: false,
        profileError: null,
        refreshProfile,
        signOut,
        devRole,
        setDevRole,
      };
    }
    // A profile only counts if it belongs to the current user; until /me answers, a signed-in user is "loading".
    const current: ProfileState =
      profileState.userId === userId ? profileState : { ...IDLE, userId, status: userId ? "loading" : "idle" };
    return {
      session,
      profile: current.status === "ready" ? current.profile : null,
      loading: !sessionReady || (userId !== null && current.status === "loading"),
      profileError: current.status === "error" ? current.error : null,
      refreshProfile,
      signOut,
      devRole: null,
      setDevRole,
    };
  }, [mock, devRole, session, sessionReady, profileState, userId, refreshProfile, signOut, setDevRole]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}
