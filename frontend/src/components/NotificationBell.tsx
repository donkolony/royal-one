import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useGet } from "../lib/hooks";
import { useAuth } from "../context/AuthContext";
import { relativeTime } from "../lib/utils";
import type { AppNotification, NotificationList } from "../lib/typesExt";

/** Where a notification's link goes for this role. Staff pages live under /advisor or /owner; the client app has no prefix. */
function pathFor(n: AppNotification, role: string): string | null {
  if (!n.link) return null;
  const staff = role === "owner" ? "/owner" : "/advisor";
  if (role === "client") return n.link.resource === "claim" ? `/claims/${n.link.id}` : n.link.resource === "request" ? "/requests" : null;
  if (n.link.resource === "claim") return `${staff}/claims/${n.link.id}`;
  if (n.link.resource === "request") return role === "owner" && n.client_id ? `${staff}/clients/${n.client_id}` : `${staff}/requests`;
  if (n.link.resource === "client") return `${staff}/clients/${n.link.id}`;
  return null;
}

/**
 * The bell: unread count, the latest updates, and a toast the moment a new one arrives. It polls every 8 seconds, which is how a
 * status change made by the adviser (or the simulated insurer) reaches the client's screen with nobody chasing anybody.
 */
export function NotificationBell() {
  const { profile } = useAuth();
  const role = profile?.role ?? "client";
  const nav = useNavigate();
  const qc = useQueryClient();
  const q = useGet<NotificationList>(["notifications"], "/notifications?limit=15", { refetchMs: 8000 });
  const [open, setOpen] = useState(false);
  const [toast, setToast] = useState<AppNotification | null>(null);
  const seen = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    const top = q.data?.items[0];
    if (!q.data) return;
    if (seen.current === undefined) {
      seen.current = top?.id ?? null; // the first load is history, not news
      return;
    }
    if (top && top.id !== seen.current) {
      seen.current = top.id;
      if (!top.read_at) {
        setToast(top);
        const t = setTimeout(() => setToast(null), 7000);
        return () => clearTimeout(t);
      }
    }
  }, [q.data]);

  const refresh = () => void qc.invalidateQueries({ queryKey: ["notifications"] });
  const go = (n: AppNotification) => {
    setOpen(false);
    setToast(null);
    void api.post(`/notifications/${n.id}/read`).then(refresh);
    const path = pathFor(n, role);
    if (path) nav(path);
  };
  const unread = q.data?.unread_count ?? 0;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="true"
        aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
        className="relative grid place-items-center w-9 h-9 rounded-full text-charcoal-600 dark:text-charcoal-300 hover:bg-charcoal-100 dark:hover:bg-charcoal-700"
      >
        <Bell className="w-5 h-5" aria-hidden="true" />
        {unread > 0 && <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-accent-500 text-white text-[11px] font-bold grid place-items-center">{unread > 9 ? "9+" : unread}</span>}
      </button>
      {open && (
        <div className="absolute right-0 z-[70] mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-lg border border-charcoal-200 dark:border-charcoal-700 bg-white dark:bg-charcoal-800 shadow-xl">
          <div className="flex items-center justify-between px-4 py-2 border-b border-charcoal-100 dark:border-charcoal-700">
            <p className="text-sm font-semibold text-charcoal-900 dark:text-white">Updates</p>
            {unread > 0 && <button className="text-xs text-brand-600 dark:text-brand-300 hover:underline" onClick={() => void api.post("/notifications/read-all").then(refresh)}>Mark all read</button>}
          </div>
          <ul className="max-h-96 overflow-y-auto divide-y divide-charcoal-100 dark:divide-charcoal-700">
            {(q.data?.items ?? []).length === 0 && <li className="px-4 py-6 text-sm text-center text-charcoal-500">Nothing yet. Updates appear here by themselves.</li>}
            {q.data?.items.map((n) => (
              <li key={n.id}>
                <button onClick={() => go(n)} className={`w-full text-left px-4 py-3 hover:bg-charcoal-50 dark:hover:bg-charcoal-700/60 ${n.read_at ? "" : "bg-brand-50/60 dark:bg-brand-900/20"}`}>
                  <p className="text-sm font-medium text-charcoal-900 dark:text-white">{n.title}</p>
                  {n.body && <p className="text-xs text-charcoal-600 dark:text-charcoal-300 mt-0.5">{n.body}</p>}
                  <p className="text-[11px] text-charcoal-400 mt-1">{relativeTime(n.created_at)}</p>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {toast && createPortal(
        <div role="status" aria-live="polite" className="fixed bottom-20 md:bottom-6 right-4 z-[80] w-80 max-w-[calc(100vw-2rem)] rounded-lg border-l-4 border-brand-500 bg-white dark:bg-charcoal-800 shadow-2xl p-4">
          <p className="text-xs uppercase tracking-wide text-brand-600 dark:text-brand-300 font-semibold">Just now</p>
          <p className="text-sm font-semibold text-charcoal-900 dark:text-white mt-0.5">{toast.title}</p>
          {toast.body && <p className="text-xs text-charcoal-600 dark:text-charcoal-300 mt-0.5">{toast.body}</p>}
          <div className="mt-2 flex gap-3 text-xs"><button className="text-brand-600 dark:text-brand-300 hover:underline" onClick={() => go(toast)}>Open</button><button className="text-charcoal-500 hover:underline" onClick={() => setToast(null)}>Dismiss</button></div>
        </div>,
        document.body,
      )}
    </div>
  );
}
