import React from "react";
import { formatDateTime } from "../../lib/utils";
import type { TimelineEvent } from "../../lib/typesExt";

/** One timeline for claims and requests. Anything said by the demo insurer is marked, so nobody mistakes it for a real reply. */
export function Timeline({ events, empty = "Nothing yet." }: { events: TimelineEvent[]; empty?: string }) {
  if (events.length === 0) return <p className="text-sm text-charcoal-500">{empty}</p>;
  return (
    <ol className="relative border-l-2 border-charcoal-200 dark:border-charcoal-700 ml-2 space-y-4" aria-label="Timeline">
      {events.map((e) => {
        const simulated = /\(simulated\)/i.test(e.title) || /\(simulated\)/i.test(e.message ?? "");
        const who = e.actor ? `${e.actor.full_name ?? "Someone"} (${e.actor.role})` : simulated ? "Insurer (simulated)" : "Royal Square system";
        return (
          <li key={e.id} className="pl-4 relative">
            <span className={`absolute -left-[7px] top-1.5 w-3 h-3 rounded-full ${simulated ? "bg-accent-500" : "bg-brand-500"}`} aria-hidden="true" />
            <p className="text-sm font-semibold text-charcoal-900 dark:text-white">
              {e.title}
              {simulated && <span className="ml-2 rounded-full bg-accent-50 text-accent-700 dark:bg-accent-900/30 dark:text-accent-200 px-2 py-0.5 text-[10px] font-bold uppercase align-middle">Demo</span>}
              {!e.visible_to_client && <span className="ml-2 rounded-full bg-charcoal-100 dark:bg-charcoal-700 px-2 py-0.5 text-[10px] font-semibold uppercase align-middle">Adviser only</span>}
            </p>
            {e.message && <p className="text-sm text-charcoal-700 dark:text-charcoal-300 mt-0.5">{e.message}</p>}
            <p className="text-xs text-charcoal-500 mt-0.5">{who} · {formatDateTime(e.created_at)}</p>
          </li>
        );
      })}
    </ol>
  );
}
