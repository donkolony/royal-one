import React, { createContext, useContext, useEffect, useState } from "react";
import { Session } from "@supabase/supabase-js";
import { supabase } from "../lib/supabase";
import { get } from "../lib/api";
import { isMock } from "../lib/api";
import { Profile } from "../lib/types";
import { mockHandlers } from "../lib/mock";

interface AuthContextType {
  session: Session | null;
  profile: Profile | null;
  loading: boolean;
  devRole: "client" | "advisor" | null;
  setDevRole: (role: "client" | "advisor") => void;
}

const AuthContext = createContext<AuthContextType>({
  session: null,
  profile: null,
  loading: true,
  devRole: null,
  setDevRole: () => {},
});

/** Sentinel session object used in dev-bypass mode */
const DEV_SESSION = {
  access_token: "dev-mock-token",
  user: { id: "dev" },
} as unknown as Session;

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [devRole, setDevRoleState] = useState<"client" | "advisor" | null>(
    () => {
      // Persist chosen dev role across hot-reloads
      const saved = sessionStorage.getItem("dev_role");
      return (saved as "client" | "advisor" | null) ?? null;
    },
  );

  const CLIENT_TOKEN =
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzYjg0MTI4NS03ZTNjLTVlMDUtOTQwMC1lNjZlZDM3Yzc2NDAiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJpYXQiOjE3ODk4MzQzMTIsImV4cCI6MTc4OTg2MzExMn0.RrWEps62qrYcS3mUk2L-TaA3ATxtIlOEWJJRXj1FAlI";
  const ADVISOR_TOKEN =
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlMTVhMzRkNi00ZDlmLTUzNTMtOTdmNC0xMmM0MWVhODM3N2QiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJpYXQiOjE3ODk4MzQzMTMsImV4cCI6MTc4OTg2MzExM30.EJfn9KlkrOnTnQBbtt6dJ4lKVV2t5PJs0TF7yDulnQU";

  /** Called by the DevLoginBanner to pick a role */
  function setDevRole(role: "client" | "advisor") {
    sessionStorage.setItem("dev_role", role);
    setDevRoleState(role);

    const token = role === "client" ? CLIENT_TOKEN : ADVISOR_TOKEN;
    const realSession = {
      access_token: token,
      user: { id: "dev" },
    } as unknown as Session;
    setSession(realSession);

    if (isMock()) {
      const key = role === "advisor" ? "/me-advisor" : "/me";
      setProfile(mockHandlers[key] as Profile);
      setLoading(false);
    } else {
      // In real backend mode, let the useEffect fetch the profile using the new session
      setLoading(true);
    }
  }

  useEffect(() => {
    // ── Dev bypass: if devRole was previously picked, restore it immediately
    if (devRole) {
      const token = devRole === "client" ? CLIENT_TOKEN : ADVISOR_TOKEN;
      const realSession = {
        access_token: token,
        user: { id: "dev" },
      } as unknown as Session;
      setSession(realSession);

      if (isMock()) {
        const key = devRole === "advisor" ? "/me-advisor" : "/me";
        setProfile(mockHandlers[key] as Profile);
        setLoading(false);
        return;
      }
      // If NOT mock, we fall through and let normal fetchProfile() happen with the injected token
    }

    // ── Normal Supabase auth
    let mounted = true;

    async function initializeAuth() {
      try {
        const {
          data: { session: currentSession },
        } = await supabase.auth.getSession();
        if (mounted) {
          setSession(currentSession);
          if (currentSession) {
            await fetchProfile();
          } else {
            setLoading(false);
          }
        }
      } catch (err) {
        console.error("Auth init error", err);
        if (mounted) setLoading(false);
      }
    }

    async function fetchProfile() {
      try {
        const data = await get<Profile>("/me");
        if (mounted) setProfile(data);
      } catch (err) {
        console.error("Profile fetch error", err);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    initializeAuth();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, newSession) => {
      setSession(newSession);
      if (newSession) {
        setLoading(true);
        try {
          const data = await get<Profile>("/me");
          setProfile(data);
        } catch (err) {
          console.error("Profile refetch error", err);
        } finally {
          setLoading(false);
        }
      } else {
        setProfile(null);
        setLoading(false);
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [devRole]);

  return (
    <AuthContext.Provider
      value={{ session, profile, loading, devRole, setDevRole }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
