import React from "react";
import { ShieldCheck } from "lucide-react";
import { Card, DemoBadge, ErrorBanner, PageHeader, Skeleton } from "@/components/ui";
import { IdentityStateChip } from "@/components/identity/IdentityStateChip";
import { IdentityUpload } from "@/components/identity/IdentityUpload";
import { useGet } from "@/lib/hooks";
import { formatDate, formatDateTime } from "@/lib/utils";
import type { IdentityDocType, IdentityVault } from "@/lib/typesExt";

const TYPES: { type: IdentityDocType; title: string; help: string }[] = [
  { type: "id_document", title: "ID document", help: "Used for claims, requests and reviews." },
  { type: "drivers_licence", title: "Driver's licence", help: "Used when you register a motor claim, so you are not asked again." },
  { type: "proof_of_address", title: "Proof of address", help: "Used for address changes. It goes out of date after 90 days." },
];

/**
 * The client's identity vault: a document is added once, verified by the adviser, and then reused. The client can see exactly where
 * each one was used, and when it needs renewing.
 */
export default function Identity() {
  const q = useGet<IdentityVault>(["identity"], "/identity", { refetchMs: 10000 });
  if (q.isLoading) return <Skeleton className="h-96 w-full" />;
  if (q.error) return <ErrorBanner error={q.error} onRetry={() => void q.refetch()} />;
  const v = q.data;
  if (!v) return null;

  return (
    <div className="p-4 md:p-8 max-w-4xl space-y-6">
      <PageHeader title="Identity documents" badge={<DemoBadge>Demo verification</DemoBadge>}
        subtitle="Add each document once. Once your adviser has verified it, we reuse it for claims and requests, so you are not asked for it again while it is valid." />
      <p className="rounded-md bg-charcoal-50 dark:bg-charcoal-800 border border-charcoal-200 dark:border-charcoal-700 p-3 text-sm text-charcoal-700 dark:text-charcoal-300 flex gap-2">
        <ShieldCheck className="w-5 h-5 shrink-0 text-brand-500" aria-hidden="true" /><span>{v.verifier.note}</span>
      </p>
      {TYPES.map(({ type, title, help }) => {
        const s = v.summary[type];
        const docs = v.documents.filter((d) => d.doc_type === type);
        return (
          <Card key={type}>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div><h2 className="font-semibold text-charcoal-900 dark:text-white">{title}</h2><p className="text-sm text-charcoal-600 dark:text-charcoal-300">{help}</p></div>
              <IdentityStateChip state={s.state} />
            </div>
            {s.expiry_date && <p className="mt-2 text-sm">Expires <span className="font-medium">{formatDate(s.expiry_date)}</span>{s.state === "expiring" || s.state === "expired" ? " · please add the renewed document below" : ""}</p>}
            {s.state === "stale" && <p className="mt-2 text-sm">This proof of address is more than {v.rules.proof_of_address_max_age_days} days old. Please add a recent one.</p>}
            {docs.length > 0 && (
              <ul className="mt-3 text-sm divide-y divide-charcoal-100 dark:divide-charcoal-700">
                {docs.map((d) => (
                  <li key={d.id} className="py-2 flex flex-wrap justify-between gap-2">
                    <span>{d.filename} <span className="text-charcoal-500">· added {formatDate(d.uploaded_at)}</span></span>
                    <span className="text-charcoal-600 dark:text-charcoal-300 capitalize">{d.status}{d.status === "verified" && d.verified_by ? ` by ${d.verified_by.full_name}` : ""}{d.reuse_count ? ` · reused ${d.reuse_count}×` : ""}{d.rejected_reason ? ` · ${d.rejected_reason}` : ""}</span>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-4 border-t border-charcoal-100 dark:border-charcoal-700 pt-4"><IdentityUpload docType={type} /></div>
          </Card>
        );
      })}
      <Card>
        <h2 className="font-semibold text-charcoal-900 dark:text-white mb-2">Where your documents were reused</h2>
        {v.reuse_log.length === 0 ? <p className="text-sm text-charcoal-500">Not used yet. When you start a claim or a request, it will show up here instead of asking you again.</p> : (
          <ul className="text-sm space-y-1">{v.reuse_log.map((r) => <li key={r.id}>Your {r.label} was used for a {r.used_for} on {formatDateTime(r.used_at)}. You were not asked again.</li>)}</ul>
        )}
      </Card>
    </div>
  );
}
