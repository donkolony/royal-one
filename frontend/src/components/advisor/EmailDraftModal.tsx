import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Skeleton, ErrorBanner } from "@/components/ui";
import { X, AlertTriangle, Copy, CheckCircle } from "lucide-react";

interface EmailRecipient {
  name: string | null;
  email: string;
}

interface EmailDraftResponse {
  draft: {
    to: EmailRecipient[];
    cc: EmailRecipient[];
    subject: string;
    body_text: string;
  };
  context_used: Record<string, unknown>;
  warnings: string[];
  requires_human_review: true;
  generated_by: { provider: string; name: string };
}

interface Props {
  claimId?: string | null;
  threadId?: string | null;
  onClose: () => void;
}

export default function EmailDraftModal({ claimId, threadId, onClose }: Props) {
  const [purpose, setPurpose] = useState("initial_notification");
  const [instructions, setInstructions] = useState("");
  const [copied, setCopied] = useState(false);

  const generateDraft = useMutation<EmailDraftResponse, any, void>({
    mutationFn: () =>
      api.post<EmailDraftResponse>("/email/drafts/generate", {
        claim_id: claimId,
        thread_id: threadId ?? null,
        purpose,
        instructions: instructions || undefined,
      }),
  });

  const handleCopy = () => {
    if (generateDraft.data?.draft.body_text) {
      navigator.clipboard.writeText(generateDraft.data.draft.body_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-charcoal-900/50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        <div className="p-4 border-b border-charcoal-200 flex justify-between items-center">
          <h2 className="text-lg font-bold text-charcoal-900">
            Draft Insurer Email
          </h2>
          <button
            onClick={onClose}
            className="text-charcoal-400 hover:text-charcoal-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1">
          {!generateDraft.data &&
          !generateDraft.isPending &&
          !generateDraft.isError ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-charcoal-700 mb-1">
                  Purpose
                </label>
                <select
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  className="w-full rounded-md border-charcoal-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm"
                >
                  <option value="initial_notification">
                    Initial Notification
                  </option>
                  <option value="follow_up">Follow Up</option>
                  <option value="reply">Reply</option>
                  <option value="status_query">Status Query</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-charcoal-700 mb-1">
                  Additional Instructions (Optional, max 500 chars)
                </label>
                <textarea
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  maxLength={500}
                  rows={4}
                  placeholder="e.g., Mention that the client is frustrated with the delay..."
                  className="w-full rounded-md border-charcoal-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm resize-none"
                />
              </div>

              <div className="flex justify-end pt-4">
                <button
                  onClick={() => generateDraft.mutate()}
                  disabled={!claimId && !threadId}
                  className="px-4 py-2 bg-charcoal-800 text-white font-medium rounded hover:bg-charcoal-700 disabled:opacity-50"
                >
                  Generate Draft
                </button>
              </div>
              {!claimId && !threadId && (
                <p className="text-xs text-red-500 text-right">
                  Must provide a claim ID or thread ID to generate.
                </p>
              )}
            </div>
          ) : generateDraft.isPending ? (
            <div className="space-y-4">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          ) : generateDraft.isError ? (
            <ErrorBanner error={generateDraft.error as any} />
          ) : generateDraft.data ? (
            <div className="space-y-4">
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded text-sm font-bold flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 mr-2" /> REQUIRES HUMAN REVIEW
              </div>

              {generateDraft.data.warnings?.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded p-3">
                  <h4 className="text-sm font-semibold text-amber-800 mb-2">
                    AI Warnings:
                  </h4>
                  <ul className="list-disc pl-5 text-sm text-amber-700 space-y-1">
                    {generateDraft.data.warnings.map((w: string, i: number) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="space-y-2 text-sm text-charcoal-700">
                <div className="flex bg-charcoal-50 px-3 py-2 rounded border border-charcoal-200">
                  <span className="font-semibold w-20">To:</span>{" "}
                  {generateDraft.data.draft.to.map((r) => r.email).join(", ")}
                </div>
                {generateDraft.data.draft.cc.length > 0 && (
                  <div className="flex bg-charcoal-50 px-3 py-2 rounded border border-charcoal-200">
                    <span className="font-semibold w-20">CC:</span>{" "}
                    {generateDraft.data.draft.cc.map((r) => r.email).join(", ")}
                  </div>
                )}
                <div className="flex bg-charcoal-50 px-3 py-2 rounded border border-charcoal-200">
                  <span className="font-semibold w-20">Subject:</span>{" "}
                  {generateDraft.data.draft.subject}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-charcoal-700 mb-1">
                  Body (Edit if needed before copying)
                </label>
                <textarea
                  defaultValue={generateDraft.data.draft.body_text}
                  className="w-full h-64 font-mono text-sm rounded-md border-charcoal-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 p-3"
                  id="draft-body"
                />
              </div>
            </div>
          ) : null}
        </div>

        {generateDraft.data && (
          <div className="p-4 border-t border-charcoal-200 bg-charcoal-50 flex justify-between items-center">
            <button
              onClick={() => generateDraft.mutate()}
              className="px-4 py-2 bg-charcoal-200 text-charcoal-700 font-medium rounded hover:bg-charcoal-300 text-sm"
            >
              Re-generate
            </button>
            <div className="flex gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-charcoal-600 font-medium rounded hover:bg-charcoal-100 text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleCopy}
                className="flex items-center px-4 py-2 bg-charcoal-800 text-white font-medium rounded hover:bg-charcoal-700 text-sm"
              >
                {copied ? (
                  <CheckCircle className="w-4 h-4 mr-2" />
                ) : (
                  <Copy className="w-4 h-4 mr-2" />
                )}
                {copied ? "Copied!" : "Copy to clipboard"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
