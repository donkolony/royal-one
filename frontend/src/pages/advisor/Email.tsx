import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Skeleton, ErrorBanner, EmptyState } from '@/components/ui';
import { AlertTriangle, Flag, Mail, Link as LinkIcon } from 'lucide-react';
import EmailDraftModal from '@/components/advisor/EmailDraftModal';
import { Page, EmailThread } from '@/lib/types';

export default function AdvisorEmail() {
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [isDraftModalOpen, setIsDraftModalOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: threads, isLoading, error } = useQuery<Page<EmailThread>>({
    queryKey: ['emailThreads'],
    queryFn: () => api.get<Page<EmailThread>>('/email/threads'),
  });

  const { data: threadDetail, isLoading: isLoadingDetail } = useQuery<EmailThread>({
    queryKey: ['emailThread', selectedThreadId],
    queryFn: () => api.get<EmailThread>(`/email/threads/${selectedThreadId}`),
    enabled: !!selectedThreadId,
  });

  const linkMutation = useMutation({
    mutationFn: ({ threadId, claimId }: { threadId: string, claimId: string }) => 
      api.put(`/email/threads/${threadId}/link`, { claim_id: claimId }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['emailThread'] }),
  });

  return (
    <div className="h-full flex flex-col -mx-4 -mt-4">
      {/* PROMINENT DEMO BANNER */}
      <div className="bg-amber-500 text-charcoal-900 px-4 py-2 flex items-center justify-center font-bold text-sm shadow-sm z-10 sticky top-0">
        <AlertTriangle className="w-5 h-5 mr-2" />
        Demo email only — these are simulated threads, not a live mailbox. Gmail integration is a post-hackathon roadmap item.
      </div>

      <div className="p-4 border-b border-charcoal-200 bg-white flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold text-charcoal-900">Email</h1>
          <p className="text-sm text-charcoal-500">adviser@demo.example (simulated)</p>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Thread List */}
        <div className="w-1/3 border-r border-charcoal-200 bg-charcoal-50 overflow-y-auto">
          {isLoading && <Skeleton className="h-full w-full" />}
          {error && <div className="p-4"><ErrorBanner error={error} /></div>}
          
          <div className="divide-y divide-charcoal-200">
            {threads?.items?.map((thread: any) => (
              <div 
                key={thread.id} 
                onClick={() => setSelectedThreadId(thread.id)}
                className={`p-4 cursor-pointer hover:bg-white transition-colors ${selectedThreadId === thread.id ? 'bg-white border-l-4 border-brand-500' : 'border-l-4 border-transparent'}`}
              >
                <div className="flex justify-between items-start mb-1">
                  <span className="font-semibold text-sm text-charcoal-900 truncate pr-2">
                    {thread.participants.join(', ')}
                  </span>
                  <div className="flex items-center gap-1">
                    {thread.flagged && <Flag className="w-3 h-3 text-brand-600" />}
                    <span className="text-xs text-charcoal-500 whitespace-nowrap">
                      {new Date(thread.last_message_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <h4 className="text-sm font-medium text-charcoal-800 mb-1 truncate">{thread.subject}</h4>
                <p className="text-xs text-charcoal-500 line-clamp-2">{thread.snippet}</p>
                {thread.link?.claim_id && (
                  <div className="mt-2 flex items-center gap-1 text-[10px] font-medium bg-charcoal-100 text-charcoal-600 px-2 py-0.5 rounded w-fit">
                    <LinkIcon className="w-3 h-3" /> Linked to Claim
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Thread Detail */}
        <div className="flex-1 bg-white overflow-y-auto flex flex-col">
          {!selectedThreadId ? (
            <div className="flex-1 flex items-center justify-center text-charcoal-400">
              <div className="text-center">
                <Mail className="w-12 h-12 mx-auto mb-2 opacity-20" />
                <p>Select a thread to view</p>
              </div>
            </div>
          ) : isLoadingDetail ? (
            <div className="p-6"><Skeleton className="h-64 w-full" /></div>
          ) : threadDetail ? (
            <div className="flex flex-col h-full">
              <div className="p-6 border-b border-charcoal-200">
                <div className="flex justify-between items-start">
                  <h2 className="text-xl font-bold text-charcoal-900 mb-4">{threadDetail.subject}</h2>
                  <button 
                    onClick={() => setIsDraftModalOpen(true)}
                    className="px-4 py-2 bg-charcoal-800 text-white text-sm font-medium rounded hover:bg-charcoal-700"
                  >
                    Draft Reply (AI)
                  </button>
                </div>
                
                <div className="bg-charcoal-50 p-3 rounded-lg border border-charcoal-200 flex items-center justify-between">
                  {threadDetail.link?.claim_id ? (
                    <div className="flex items-center gap-2 text-sm text-charcoal-700">
                      <LinkIcon className="w-4 h-4 text-charcoal-400" />
                      Linked to Claim: <span className="font-semibold">{threadDetail.link.claim_id}</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-charcoal-600">Not linked to a claim</span>
                      <button 
                        onClick={() => {
                          const id = prompt('Enter Claim ID to link:');
                          if (id) linkMutation.mutate({ threadId: threadDetail.id, claimId: id });
                        }}
                        className="text-xs font-medium text-brand-600 hover:text-brand-700"
                      >
                        Link to Claim
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="p-6 space-y-6 flex-1 overflow-y-auto">
                {(threadDetail as any).messages?.map((msg: any) => (
                  <div key={msg.id} className="border border-charcoal-200 rounded-lg overflow-hidden">
                    <div className="bg-charcoal-50 p-3 border-b border-charcoal-200 flex justify-between items-center text-sm">
                      <div>
                        <span className="font-semibold text-charcoal-900">{msg.from?.email || msg.from_email}</span>
                        <span className="text-charcoal-500 mx-2">to</span>
                        <span className="text-charcoal-700">{msg.to?.map((t: any) => t.email).join(', ') || msg.to_emails?.join(', ')}</span>
                      </div>
                      <span className="text-charcoal-500 text-xs">{new Date(msg.sent_at).toLocaleString()}</span>
                    </div>
                    {/* PLAIN TEXT ONLY - Never innerHTML */}
                    <div className="p-4 text-sm text-charcoal-800 whitespace-pre-wrap font-sans">
                      {msg.body_text}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {isDraftModalOpen && (
        <EmailDraftModal 
          claimId={threadDetail?.link?.claim_id} 
          threadId={selectedThreadId} 
          onClose={() => setIsDraftModalOpen(false)} 
        />
      )}
    </div>
  );
}
