import { useAuth } from "../context/AuthContext";

/** Advisers and the owner share one set of staff pages, mounted under /advisor and /owner. Links must keep the prefix. */
export type StaffBase = "/advisor" | "/owner";

export function useStaffBase(): StaffBase {
  const { profile } = useAuth();
  return profile?.role === "owner" ? "/owner" : "/advisor";
}

export function useIsOwner(): boolean {
  return useAuth().profile?.role === "owner";
}
