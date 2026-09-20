import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { useStaffBase } from "@/lib/staff";
import { api } from "@/lib/api";
import { Claim, Page, EmailThread } from "@/lib/types";
import { Skeleton, ErrorBanner } from "@/components/ui";
import EmailDraftModal from "@/components/advisor/EmailDraftModal";
import { Mail, AlertCircle } from "lucide-react";

export default function AdvisorClaimDetail() {
  const { claimId } = useParams<{ claimId: string }>();
  const base = useStaffBase();
  const queryClient = useQueryClient();
  const [isDraftModalOpen, setIsDraftModalOpen] = useState(false);

  const {
    data: claim,
    isLoading,
    error,
  } = useQuery<Claim>({
    queryKey: ["claim", claimId],
    queryFn: () => api.get<Claim>(`/claims/${claimId}`),
    refetchInterval: 30000,
    enabled: !!claimId,
  });

  const { data: threads } = useQuery<Page<EmailThread>>({
    queryKey: ["claimThreads", claimId],
    queryFn: () =>
      api.get<Page<EmailThread>>(`/email/threads?claim_id=${claimId}`),
    enabled: !!claimId,
  });

  const postTransition = useMutation({
    mutationFn: (targetStatus: string) =>
      api.post(`/claims/${claimId}/transitions`, {
        target_status: targetStatus,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["claim"] }),
  });

  const postUpdate = useMutation({
    mutationFn: (payload: any) =>
      api.post(`/claims/${claimId}/updates`, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["claim"] }),
  });

  const [updateMsg, setUpdateMsg] = useState("");
  const [updateType, setUpdateType] = useState("note");
  const [visibleToClient, setVisibleToClient] = useState(false);
  const [timelineClientFilter, setTimelineClientFilter] = useState(false);

  if (isLoading) return <Skeleton className="h-[600px] w-full" />;
  if (error) return <ErrorBanner error={error} />;
  if (!claim) return <div>Claim not found</div>;

  return (
    <div className="space-y-6 pb-20">
      {/* Header */}
      <div>
        <Link
          to={`${base}/claims`}
          className="text-sm text-charcoal-500 hover:text-charcoal-800 mb-2 inline-block"
        >
          ← Back to Pipeline
        </Link>
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-charcoal-900">
              Claim {claim.reference || "Draft"}
            </h1>
            <p className="text-charcoal-600 mt-1">
              Client:{" "}
              <Link
                to={`${base}/clients/${claim.client.id}`}
                className="text-brand-600 hover:underline"
              >
                {claim.client.full_name}
              </Link>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="px-3 py-1 bg-charcoal-800 text-white text-sm font-medium rounded-full">
              {claim.status_label ||
                claim.status.replace("_", " ").toUpperCase()}
            </span>
            {claim.days_in_status >= 7 && (
              <span className="px-2 py-1 bg-red-100 text-red-800 text-xs font-bold rounded flex items-center">
                <AlertCircle className="w-3 h-3 mr-1" /> {claim.days_in_status}d
                in status
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Action Bar (Transitions) */}
      {claim.allowed_transitions?.length > 0 && (
        <div className="bg-charcoal-50 p-4 border border-charcoal-200 rounded-lg flex flex-wrap gap-2 items-center">
          <span className="text-sm font-medium text-charcoal-700 mr-2">
            Actions:
          </span>
          {claim.allowed_transitions.map((t: any) => {
            const needsClaimNum =
              t.target_status === "registered" && !claim.claim_number;
            return (
              <button
                key={t.target_status}
                onClick={() => {
                  if (needsClaimNum) return;
                  if (confirm(`Move claim to ${t.label}?`))
                    postTransition.mutate(t.target_status);
                }}
                disabled={needsClaimNum || postTransition.isPending}
                title={needsClaimNum ? "Claim number required" : ""}
                className={`px-4 py-2 text-sm font-medium rounded ${needsClaimNum ? "bg-charcoal-200 text-charcoal-400 cursor-not-allowed" : "bg-brand-500 text-white hover:bg-brand-600"}`}
              >
                {t.label}
              </button>
            );
          })}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Incident Details */}
          <section className="bg-white p-5 shadow rounded-lg border border-charcoal-100">
            <h2 className="text-lg font-bold text-charcoal-900 border-b border-charcoal-100 pb-2 mb-4">
              Incident Details
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-charcoal-500 mb-1 flex items-center gap-1">
                  Occurred At
                </p>
                <p className="font-medium text-charcoal-900">
                  {claim.incident.occurred_at
                    ? new Date(claim.incident.occurred_at).toLocaleString()
                    : "Unknown"}
                </p>
              </div>
              <div>
                <p className="text-charcoal-500 mb-1 flex items-center gap-1">
                  Location
                </p>
                <p className="font-medium text-charcoal-900">
                  {claim.incident.location_text}
                </p>
              </div>
              <div className="md:col-span-2">
                <p className="text-charcoal-500 mb-1">Description</p>
                <p className="font-medium text-charcoal-900 whitespace-pre-wrap bg-charcoal-50 p-3 rounded">
                  {claim.incident.description}
                </p>
              </div>
            </div>
          </section>

          {/* Insurer Details */}
          <section className="bg-white p-5 shadow rounded-lg border border-charcoal-100">
            <h2 className="text-lg font-bold text-charcoal-900 border-b border-charcoal-100 pb-2 mb-4">
              Insurer & Repair Details
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-y-4 gap-x-6 text-sm">
              <div>
                <p className="text-charcoal-500 mb-1">Claim Number</p>
                <p className="font-medium text-charcoal-900">
                  {claim.claim_number || "Pending"}
                </p>
              </div>
              <div>
                <p className="text-charcoal-500 mb-1">Insurer</p>
                <p className="font-medium text-charcoal-900">
                  {claim.insurer?.name}
                </p>
              </div>
              <div>
                <p className="text-charcoal-500 mb-1">Handler Name</p>
                <p className="font-medium text-charcoal-900">
                  {claim.insurer_details.handler_name || "Unassigned"}
                </p>
              </div>
              <div>
                <p className="text-charcoal-500 mb-1">Repairer</p>
                <p className="font-medium text-charcoal-900">
                  {claim.repair.repairer_name || "Not selected"}
                </p>
              </div>
              <div>
                <p className="text-charcoal-500 mb-1">Hire Car Status</p>
                <p className="font-medium text-charcoal-900 capitalize">
                  {(claim.hire_car.status || "not_required").replace("_", " ")}
                </p>
              </div>
            </div>
            <div className="mt-4 flex justify-end">
              <button className="text-xs font-medium text-brand-600 hover:text-brand-700">
                Edit Details
              </button>
            </div>
          </section>

          {/* Linked Email Strip */}
          <section className="bg-white p-5 shadow rounded-lg border border-charcoal-100">
            <div className="flex justify-between items-center border-b border-charcoal-100 pb-2 mb-4">
              <h2 className="text-lg font-bold text-charcoal-900 flex items-center gap-2">
                <Mail className="w-5 h-5" /> Linked Emails
              </h2>
              <button
                onClick={() => setIsDraftModalOpen(true)}
                className="px-3 py-1.5 bg-charcoal-800 text-white text-xs font-medium rounded hover:bg-charcoal-700"
              >
                Draft Email (AI)
              </button>
            </div>
            {!threads || threads.items.length === 0 ? (
              <p className="text-sm text-charcoal-500 text-center py-4">
                No linked emails found.
              </p>
            ) : (
              <div className="space-y-2">
                {threads.items.slice(0, 3).map((t: any) => (
                  <div
                    key={t.id}
                    className="p-3 bg-charcoal-50 rounded border border-charcoal-200"
                  >
                    <p className="text-sm font-semibold text-charcoal-900">
                      {t.subject}
                    </p>
                    <p className="text-xs text-charcoal-500 line-clamp-1">
                      {t.snippet}
                    </p>
                  </div>
                ))}
                {threads.items.length > 3 && (
                  <Link
                    to="/advisor/email"
                    className="text-xs font-medium text-brand-600 hover:underline block text-center mt-2"
                  >
                    View all {threads.items.length} threads
                  </Link>
                )}
              </div>
            )}
          </section>
        </div>

        <div className="space-y-6">
          {/* Timeline & Updates */}
          <section className="bg-white p-5 shadow rounded-lg border border-charcoal-100 flex flex-col h-[600px]">
            <div className="flex justify-between items-center border-b border-charcoal-100 pb-2 mb-4">
              <h2 className="text-lg font-bold text-charcoal-900">Timeline</h2>
              <label className="flex items-center gap-2 text-xs text-charcoal-600">
                <input
                  type="checkbox"
                  checked={timelineClientFilter}
                  onChange={(e) => setTimelineClientFilter(e.target.checked)}
                  className="rounded text-brand-500"
                />
                Client visible only
              </label>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4 pr-2">
              {claim.timeline
                ?.filter((u: any) =>
                  timelineClientFilter ? u.visible_to_client : true,
                )
                .map((u: any, idx: number) => (
                  <div
                    key={u.id || idx}
                    className="relative pl-6 pb-4 border-l-2 border-charcoal-200 last:pb-0 last:border-0"
                  >
                    <div
                      className={`absolute -left-[5px] top-1 w-2 h-2 rounded-full ${u.type === "status_changed" ? "bg-brand-500" : "bg-charcoal-400"}`}
                    ></div>
                    <div className="bg-charcoal-50 p-3 rounded text-sm">
                      <div className="flex justify-between mb-1">
                        <span className="font-semibold text-charcoal-800 capitalize">
                          {u.type.replace("_", " ")}
                        </span>
                        <span className="text-xs text-charcoal-500">
                          {new Date(u.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-charcoal-700 whitespace-pre-wrap">
                        {u.message}
                      </p>
                      {u.visible_to_client && (
                        <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded mt-2 inline-block">
                          Visible to Client
                        </span>
                      )}
                    </div>
                  </div>
                ))}
            </div>

            <div className="mt-4 pt-4 border-t border-charcoal-100">
              <div className="space-y-2">
                <textarea
                  value={updateMsg}
                  onChange={(e) => setUpdateMsg(e.target.value)}
                  placeholder="Post an update or internal note..."
                  className="w-full text-sm rounded-md border-charcoal-300 shadow-sm focus:border-brand-500 p-2"
                  rows={2}
                />
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <select
                      value={updateType}
                      onChange={(e) => setUpdateType(e.target.value)}
                      className="text-xs rounded border-charcoal-300 py-1"
                    >
                      <option value="note">Internal Note</option>
                      <option value="repair_update">Repair Update</option>
                      <option value="general_update">General Update</option>
                    </select>
                    <label className="flex items-center gap-1 text-xs text-charcoal-600">
                      <input
                        type="checkbox"
                        checked={visibleToClient}
                        onChange={(e) => setVisibleToClient(e.target.checked)}
                        className="rounded text-brand-500"
                      />
                      Show Client
                    </label>
                  </div>
                  <button
                    onClick={() => {
                      if (!updateMsg.trim()) return;
                      postUpdate.mutate({
                        type: updateType,
                        message: updateMsg,
                        visible_to_client: visibleToClient,
                      });
                      setUpdateMsg("");
                    }}
                    disabled={postUpdate.isPending || !updateMsg.trim()}
                    className="px-3 py-1.5 bg-brand-500 text-white text-xs font-medium rounded hover:bg-brand-600 disabled:opacity-50"
                  >
                    Post
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>

      {isDraftModalOpen && (
        <EmailDraftModal
          claimId={claimId}
          threadId={threads?.items?.[0]?.id || null}
          onClose={() => setIsDraftModalOpen(false)}
        />
      )}
    </div>
  );
}
