import React, { useRef, useState } from "react";
import { Button, ErrorBanner } from "../ui";
import { api } from "../../lib/api";
import { useAct } from "../../lib/hooks";
import type { IdentityDocType } from "../../lib/typesExt";

interface Props {
  docType: IdentityDocType;
  /** Set when an adviser adds a document on behalf of a client. */
  clientId?: string;
  onDone?: () => void;
}

/** One small upload form: a file and an optional expiry date. The document waits for the adviser to verify it. */
export function IdentityUpload({ docType, clientId, onDone }: Props) {
  const file = useRef<HTMLInputElement>(null);
  const [expiry, setExpiry] = useState("");
  const [picked, setPicked] = useState<File | null>(null);
  const up = useAct(
    () => {
      const form = new FormData();
      form.append("doc_type", docType);
      if (clientId) form.append("client_id", clientId);
      if (expiry) form.append("expiry_date", expiry);
      form.append("file", picked as File, picked?.name);
      return api.postForm("/identity", form);
    },
    [["identity"], ["notifications"], ["client-compliance"], ["business-health"]],
    () => { setPicked(null); setExpiry(""); if (file.current) file.current.value = ""; onDone?.(); },
  );
  return (
    <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); if (picked) up.mutate(); }}>
      <label className="text-sm">
        <span className="block font-medium mb-1">File (photo or PDF)</span>
        <input ref={file} type="file" accept="image/jpeg,image/png,image/webp,application/pdf" onChange={(e) => setPicked(e.target.files?.[0] ?? null)} className="text-sm" />
      </label>
      {docType !== "proof_of_address" && (
        <label className="text-sm">
          <span className="block font-medium mb-1">Expiry date (optional)</span>
          <input type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} className="rounded-md border-charcoal-300 dark:bg-charcoal-900 dark:border-charcoal-600 text-sm" />
        </label>
      )}
      <Button type="submit" size="sm" disabled={!picked} loading={up.isPending}>Add</Button>
      {up.error ? <div className="w-full"><ErrorBanner error={up.error} /></div> : null}
    </form>
  );
}
