import React, { ReactNode, useId, useState } from "react";
import { Info } from "lucide-react";

interface InfoPopoverProps {
  /** Button text, for example "How is this calculated?" */
  label?: string;
  children: ReactNode;
}

/** A disclosure, not a floating tooltip: it opens in the page flow, so it works with a keyboard and on a phone. */
export function InfoPopover({ label = "How is this calculated?", children }: InfoPopoverProps) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div className="text-xs">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={id}
        className="inline-flex items-center gap-1 text-brand-600 dark:text-brand-300 hover:underline"
      >
        <Info className="w-3.5 h-3.5" aria-hidden="true" /> {label}
      </button>
      {open && (
        <div id={id} className="mt-2 rounded-md bg-charcoal-50 dark:bg-charcoal-900 border border-charcoal-200 dark:border-charcoal-700 p-3 text-charcoal-700 dark:text-charcoal-300 leading-relaxed">
          {children}
        </div>
      )}
    </div>
  );
}

/** "Demo estimate": every rand figure that comes from assumptions carries this, so it is never mistaken for real data. */
export function DemoBadge({ children = "Demo estimate" }: { children?: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-accent-300 bg-accent-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-accent-700 dark:bg-accent-900/30 dark:text-accent-200 dark:border-accent-700">
      {children}
    </span>
  );
}
