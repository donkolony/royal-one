import React, { useState } from "react";
import { RotateCcw } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Modal, ErrorBanner, DemoBadge } from "../ui";
import { api } from "../../lib/api";
import { useMeta } from "../../lib/meta";

/** DEMO ONLY (the API refuses it unless DEMO_MODE is on): put every data table back to the seeded state before a run-through. */
export function ResetDemoButton() {
  const { data: meta } = useMeta();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  if (!meta?.demo_mode) return null;

  const reset = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/demo/reset");
      await qc.invalidateQueries();
      setOpen(false);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <Button variant="secondary" size="sm" onClick={() => setOpen(true)}><RotateCcw className="w-4 h-4 mr-1.5" aria-hidden="true" />Reset demo data</Button>
      <Modal open={open} onClose={() => setOpen(false)} title="Reset the demo data?" size="sm"
        footer={<><Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button><Button variant="danger" loading={busy} onClick={() => void reset()}>Reset</Button></>}>
        <div className="space-y-3 text-sm text-charcoal-700 dark:text-charcoal-200">
          <p><DemoBadge>Demo</DemoBadge></p>
          <p>Every claim, request, opportunity outcome, identity document and audit entry goes back to the seeded starting point. The approved-document library is kept.</p>
          {error ? <ErrorBanner error={error} /> : null}
        </div>
      </Modal>
    </>
  );
}
