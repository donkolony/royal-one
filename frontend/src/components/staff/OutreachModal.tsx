import React, { useEffect, useState } from "react";
import { Copy } from "lucide-react";
import { Modal, Button, ErrorBanner, Skeleton, Badge } from "../ui";
import { api } from "../../lib/api";
import type { Opportunity, OutreachDraft } from "../../lib/typesExt";

interface Props {
  opportunity: Opportunity;
  open: boolean;
  onClose: () => void;
  /** Called after the adviser confirms they sent it, so the opportunity can move to "actioned". */
  onSent: (channel: "email" | "whatsapp", note: string) => void;
}

/**
 * "Draft outreach": the adviser gets wording, edits it, and sends it THEMSELVES from their own email or WhatsApp.
 * Nothing is sent from here and nothing is stored until they confirm; the button only logs that they did it.
 */
export function OutreachModal({ opportunity, open, onClose, onSent }: Props) {
  const [channel, setChannel] = useState<"email" | "whatsapp">("email");
  const [draft, setDraft] = useState<OutreachDraft | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open) return;
    let live = true;
    setLoading(true);
    setError(null);
    api
      .post<OutreachDraft>(`/opportunities/${opportunity.id}/draft`, { channel })
      .then((d) => {
        if (!live) return;
        setDraft(d);
        setSubject(d.subject ?? "");
        setBody(d.body);
      })
      .catch((e) => live && setError(e))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [open, channel, opportunity.id]);

  const copy = () => {
    const text = channel === "email" && subject ? `Subject: ${subject}\n\n${body}` : body;
    void navigator.clipboard?.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Draft outreach: ${opportunity.client.full_name}`}
      size="lg"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Close</Button>
          <Button variant="secondary" onClick={copy} disabled={!body}><Copy className="w-4 h-4 mr-2" aria-hidden="true" />{copied ? "Copied" : "Copy"}</Button>
          <Button onClick={() => onSent(channel, "Sent from the draft")} disabled={!body}>I sent this</Button>
        </>
      }
    >
      <div className="space-y-4">
        <div role="tablist" aria-label="Channel" className="inline-flex rounded-md border border-charcoal-200 dark:border-charcoal-600 p-0.5">
          {(["email", "whatsapp"] as const).map((c) => (
            <button
              key={c}
              role="tab"
              aria-selected={channel === c}
              onClick={() => setChannel(c)}
              className={`px-3 py-1.5 text-sm rounded ${channel === c ? "bg-brand-500 text-white" : "text-charcoal-600 dark:text-charcoal-300"}`}
            >
              {c === "email" ? "Email" : "WhatsApp"}
            </button>
          ))}
        </div>

        {loading && <Skeleton lines={4} />}
        {!loading && error ? <ErrorBanner error={error} /> : null}
        {!loading && draft && (
          <>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge variant={draft.source === "ai" ? "info" : "default"}>{draft.source === "ai" ? "AI-polished wording" : "Standard wording"}</Badge>
              <span className="text-charcoal-500 dark:text-charcoal-400">{draft.note}</span>
            </div>
            {draft.warnings.map((w) => (
              <p key={w} role="status" className="text-xs rounded bg-amber-50 text-amber-900 dark:bg-amber-900/30 dark:text-amber-100 p-2">{w}</p>
            ))}
            {channel === "email" && (
              <label className="block text-sm">
                <span className="font-medium text-charcoal-700 dark:text-charcoal-200">Subject</span>
                <input value={subject} onChange={(e) => setSubject(e.target.value)} className="mt-1 w-full rounded-md border-charcoal-300 dark:bg-charcoal-900 dark:border-charcoal-600" />
              </label>
            )}
            <label className="block text-sm">
              <span className="font-medium text-charcoal-700 dark:text-charcoal-200">Message (edit before sending)</span>
              <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={channel === "email" ? 9 : 5} className="mt-1 w-full rounded-md border-charcoal-300 dark:bg-charcoal-900 dark:border-charcoal-600" />
            </label>
            <p className="text-xs text-charcoal-500 dark:text-charcoal-400">
              Royal Square does not send messages from this screen. Copy it into your own email or WhatsApp, then tap "I sent this" so the outreach is logged.
            </p>
          </>
        )}
      </div>
    </Modal>
  );
}
