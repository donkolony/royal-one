import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Skeleton, ErrorBanner, EmptyState } from '@/components/ui';

export default function AdvisorRequests() {
  const [filter, setFilter] = useState('open');
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery<any[]>({
    queryKey: ['advisorRequests', filter],
    queryFn: () => api.get<any[]>(`/requests?status=${filter === 'open' ? 'submitted,in_progress' : filter}`),
  });

  const updateRequest = useMutation({
    mutationFn: ({ id, status, adviser_response }: any) => 
      api.patch(`/requests/${id}`, { status, adviser_response }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['advisorRequests'] }),
  });

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [responseTexts, setResponseTexts] = useState<Record<string, string>>({});

  if (isLoading) return <Skeleton className="h-[600px] w-full" />;
  if (error) return <ErrorBanner error={error} />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Client Requests</h1>

      <div className="flex space-x-2 border-b border-slate-200">
        {['all', 'open', 'completed', 'declined'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 text-sm font-medium border-b-2 ${
              filter === f 
                ? 'border-yellow-500 text-yellow-600' 
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {!data || data.length === 0 ? (
        <EmptyState message="No requests found for this filter." />
      ) : (
        <div className="space-y-4">
          {data.map((req: any) => {
            const isExpanded = expandedId === req.id;
            
            return (
              <div key={req.id} className="bg-white shadow rounded-lg border border-slate-200 overflow-hidden">
                <div 
                  className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50"
                  onClick={() => setExpandedId(isExpanded ? null : req.id)}
                >
                  <div className="flex items-center gap-4">
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800">
                      {req.type_label || req.type.replace('_', ' ')}
                    </span>
                    <span className="font-medium text-slate-900">{req.client_name}</span>
                    <span className="text-sm text-slate-500">{new Date(req.submitted_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {req.requires_verification && (
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                        Requires Verification
                      </span>
                    )}
                    <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize
                      ${req.status === 'completed' ? 'bg-green-100 text-green-800' : 
                        req.status === 'declined' ? 'bg-red-100 text-red-800' : 
                        'bg-yellow-100 text-yellow-800'}`}
                    >
                      {req.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="p-4 border-t border-slate-200 bg-slate-50">
                    <h4 className="text-sm font-semibold text-slate-900 mb-2">Request Details</h4>
                    <div className="bg-white p-3 rounded border border-slate-200 mb-4 overflow-auto">
                      <pre className="text-xs text-slate-700 whitespace-pre-wrap">
                        {JSON.stringify(req.payload, null, 2)}
                      </pre>
                    </div>

                    <div className="space-y-3">
                      <label className="block text-sm font-medium text-slate-700">Adviser Response</label>
                      <textarea
                        className="w-full rounded-md border-slate-300 shadow-sm focus:border-yellow-500 focus:ring-yellow-500 sm:text-sm"
                        rows={3}
                        value={responseTexts[req.id] ?? (req.adviser_response || '')}
                        onChange={(e) => setResponseTexts({...responseTexts, [req.id]: e.target.value})}
                        placeholder="Add a response for the client..."
                      />
                      
                      <div className="flex gap-3">
                        {req.status !== 'in_progress' && req.status !== 'completed' && (
                          <button 
                            onClick={() => updateRequest.mutate({ id: req.id, status: 'in_progress' })}
                            className="px-4 py-2 bg-slate-100 text-slate-700 text-sm font-medium rounded hover:bg-slate-200"
                          >
                            Mark In Progress
                          </button>
                        )}
                        {req.status !== 'completed' && (
                          <button 
                            onClick={() => updateRequest.mutate({ id: req.id, status: 'completed', adviser_response: responseTexts[req.id] })}
                            className="px-4 py-2 bg-yellow-500 text-white text-sm font-medium rounded hover:bg-yellow-600"
                          >
                            Complete
                          </button>
                        )}
                        {req.status !== 'declined' && (
                          <button 
                            onClick={() => updateRequest.mutate({ id: req.id, status: 'declined', adviser_response: responseTexts[req.id] })}
                            disabled={!responseTexts[req.id]}
                            className="px-4 py-2 bg-red-100 text-red-700 text-sm font-medium rounded hover:bg-red-200 disabled:opacity-50"
                            title={!responseTexts[req.id] ? "Response required to decline" : ""}
                          >
                            Decline
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
