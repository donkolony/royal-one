import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';
import { Skeleton, ErrorBanner, EmptyState } from '@/components/ui';
import type { ClientRequest, RequestTypeDefinition } from '@/lib/types';

function Requests() {
  const [tab, setTab] = useState<'list' | 'new'>('list');
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: requests, isLoading: loadingList } = useQuery<ClientRequest[]>({
    queryKey: ['requests'],
    queryFn: () => api.get<ClientRequest[]>('/requests'),
  });

  const { data: types, isLoading: loadingTypes } = useQuery<RequestTypeDefinition[]>({
    queryKey: ['request-types'],
    queryFn: () => api.get<RequestTypeDefinition[]>('/requests/types'),
  });

  const submitRequest = useMutation({
    mutationFn: (data: { type: string; data: any }) => api.post('/requests', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requests'] });
      setTab('list');
      setSelectedType(null);
    }
  });

  if (loadingList || loadingTypes) return <Skeleton className="h-96 w-full" />;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center border-b border-gray-200 pb-4">
        <h1 className="text-3xl font-bold text-charcoal">Requests</h1>
        <div className="flex gap-2 bg-gray-100 p-1 rounded-lg">
          <button 
            onClick={() => setTab('list')}
            className={`px-4 py-2 rounded-md text-sm font-medium ${tab === 'list' ? 'bg-white shadow text-charcoal' : 'text-gray-500 hover:text-charcoal'}`}
          >
            My Requests
          </button>
          <button 
            onClick={() => setTab('new')}
            className={`px-4 py-2 rounded-md text-sm font-medium ${tab === 'new' ? 'bg-white shadow text-charcoal' : 'text-gray-500 hover:text-charcoal'}`}
          >
            New Request
          </button>
        </div>
      </div>

      {tab === 'list' && (
        <div className="space-y-4">
          {!requests || requests.length === 0 ? (
            <EmptyState message="You have no requests." />
          ) : (
            requests.map((req) => (
              <div key={req.id} className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 hover:border-brand-500 transition-colors cursor-pointer">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold text-charcoal text-lg">{req.type_label}</h3>
                  <span className="px-3 py-1 bg-gray-100 text-charcoal text-xs rounded-full font-medium">{req.status}</span>
                </div>
                <p className="text-sm text-gray-500 mb-4">Submitted: {formatDateTime(req.submitted_at)}</p>
                {req.adviser_response && (
                  <div className="bg-gray-50 p-3 rounded text-sm text-charcoal border-l-4 border-brand-500">
                    <p className="font-semibold mb-1">Adviser Response:</p>
                    <p>{req.adviser_response}</p>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {tab === 'new' && (
        <div className="space-y-6">
          {!selectedType ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {types?.map((t) => (
                <button 
                  key={t.type}
                  onClick={() => setSelectedType(t.type)}
                  className="p-6 bg-white border border-gray-200 rounded-lg hover:border-brand-500 hover:shadow-md text-left transition-all"
                >
                  <h3 className="font-bold text-charcoal text-lg mb-2">{t.label}</h3>
                  <p className="text-sm text-gray-500">{t.type} Request</p>
                </button>
              ))}
            </div>
          ) : (
            <div className="bg-white p-6 rounded-lg shadow border border-gray-100 max-w-2xl">
              <div className="flex justify-between items-center mb-6">
                <h3 className="font-bold text-xl text-charcoal">
                  {types?.find((t) => t.type === selectedType)?.label}
                </h3>
                <button onClick={() => setSelectedType(null)} className="text-sm text-gray-500 hover:text-charcoal">Change Type</button>
              </div>
              
              <div className="space-y-4">
                <div className="p-8 border-2 border-dashed border-gray-200 rounded text-center text-gray-500">
                  [ Dynamic Form Fields rendered here based on type.fields ]
                </div>
                <div>
                  <label className="block text-sm font-medium text-charcoal mb-1">Additional Notes</label>
                  <textarea className="w-full border rounded-md p-2 min-h-[100px]" placeholder="Optional details..."></textarea>
                </div>
                <div className="pt-4 border-t flex justify-end">
                  <button 
                    onClick={() => submitRequest.mutate({ type: selectedType, data: {} })}
                    className="px-6 py-2 bg-brand-500 text-white rounded-md font-bold hover:bg-gray-800"
                  >
                    Submit Request
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Requests;
