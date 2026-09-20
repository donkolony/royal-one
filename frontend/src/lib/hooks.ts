import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { get } from "./api";

/**
 * A GET that refreshes itself while the tab is visible. This is how "one shared source of truth" stays live without
 * WebSockets: every screen that two people can look at at once re-reads every few seconds (docs/AUDIT.md section 0).
 */
export function useGet<T>(key: QueryKey, path: string, options?: { refetchMs?: number; enabled?: boolean }) {
  return useQuery<T>({
    queryKey: key,
    queryFn: () => get<T>(path),
    refetchInterval: options?.refetchMs,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    enabled: options?.enabled ?? true,
  });
}

/** A write that refreshes the named reads afterwards. */
export function useAct<TIn = void, TOut = unknown>(fn: (input: TIn) => Promise<TOut>, invalidate: QueryKey[], onDone?: (out: TOut) => void) {
  const qc = useQueryClient();
  return useMutation<TOut, Error, TIn>({
    mutationFn: fn,
    onSuccess: (out) => {
      invalidate.forEach((k) => void qc.invalidateQueries({ queryKey: k }));
      onDone?.(out);
    },
  });
}


/** True while the viewport matches. Used to mount ONE copy of a widget that appears in both a phone header and a desktop sidebar. */
export function useMediaQuery(query: string): boolean {
  const get = () => (typeof window !== "undefined" && typeof window.matchMedia === "function" ? window.matchMedia(query).matches : false);
  const [matches, setMatches] = useState(get);
  useEffect(() => {
    const m = window.matchMedia(query);
    const on = () => setMatches(m.matches);
    on();
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, [query]);
  return matches;
}
