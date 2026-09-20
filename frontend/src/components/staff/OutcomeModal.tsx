import React, { useState } from "react";
import { Modal, Button } from "../ui";
import type { Opportunity } from "../../lib/typesExt";

interface Props {
  opportunity: Opportunity;
  outcome: "won" | "lost";
  open: boolean;
  onClose: () => void;
  onSave: (outcome: "won" | "lost", reason: string, actualValueRand: number | null) => void;
  saving?: boolean;
}

const LOST_REASONS = ["Client declined", "Cannot afford it", "Went to another provider", "Not the right time", "Could not reach the client"];

/** Won or lost, with a reason. The reason is required: it is what makes the conversion numbers worth reading. */
export function OutcomeModal({ opportunity, outcome, open, onClose, onSave, saving }: Props) {
  const [reason, setReason] = useState("");
  const [actual, setActual] = useState("");
  const ok = reason.trim().length >= 3;
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={outcome === "won" ? `Mark as won: ${opportunity.client.full_name}` : `Mark as lost: ${opportunity.client.full_name}`}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant={outcome === "won" ? "primary" : "danger"} disabled={!ok} loading={saving} onClick={() => onSave(outcome, reason.trim(), actual ? Number(actual) : null)}>
            {outcome === "won" ? "Save as won" : "Save as lost"}
          </Button>
        </>
      }
    >
      <div className="space-y-4 text-sm">
        <p className="text-charcoal-600 dark:text-charcoal-300">{opportunity.title}</p>
        <label className="block">
          <span className="font-medium text-charcoal-700 dark:text-charcoal-200">Reason (required)</span>
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} maxLength={300} placeholder={outcome === "won" ? "What did the client agree to?" : "Why did it not go ahead?"} className="mt-1 w-full rounded-md border-charcoal-300 dark:bg-charcoal-900 dark:border-charcoal-600" />
        </label>
        {outcome === "lost" && (
          <div className="flex flex-wrap gap-2">
            {LOST_REASONS.map((r) => (
              <button key={r} type="button" onClick={() => setReason(r)} className="rounded-full border border-charcoal-300 dark:border-charcoal-600 px-2.5 py-1 text-xs hover:bg-charcoal-100 dark:hover:bg-charcoal-700">{r}</button>
            ))}
          </div>
        )}
        {outcome === "won" && (
          <label className="block">
            <span className="font-medium text-charcoal-700 dark:text-charcoal-200">Actual annual value in rand (optional)</span>
            <input value={actual} onChange={(e) => setActual(e.target.value.replace(/[^0-9]/g, ""))} inputMode="numeric" placeholder="Leave empty to use the estimate" className="mt-1 w-full rounded-md border-charcoal-300 dark:bg-charcoal-900 dark:border-charcoal-600" />
          </label>
        )}
      </div>
    </Modal>
  );
}
