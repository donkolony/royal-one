import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';
import { Skeleton, ErrorBanner } from '@/components/ui';
import type { Claim } from '@/lib/types';

function ClaimTracking() {
  const { id } = useParams();

  const { data: claim, isLoading, error } = useQuery<Claim>({
    queryKey: ['claim', id],
    queryFn: () => api.get<Claim>(`/claims/${id}`),
    refetchInterval: 30000,
    refetchOnWindowFocus: true,
  });

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error) return <ErrorBanner error={error as Error} />;
  if (!claim) return null;

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-charcoal">Claim {claim.reference || `#${claim.id}`}</h1>
      
      {/* Stepper Placeholder */}
      <div className="p-6 bg-white rounded-lg shadow flex justify-between items-center overflow-x-auto gap-4">
        <div className="flex items-center gap-2 text-brand-500 font-bold">
          <span className="w-8 h-8 rounded-full bg-brand-500 text-white flex items-center justify-center">✓</span>
          <span>{claim.status_label}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="p-6 bg-white rounded-lg shadow border border-gray-100">
          <h3 className="font-bold text-charcoal mb-4 border-b pb-2">Status</h3>
          <p className="text-sm text-gray-500">Current:</p>
          <p className="font-medium text-lg text-charcoal">{claim.status_label}</p>
          <p className="text-sm text-gray-500 mt-4">Submitted:</p>
          <p className="font-medium">{formatDateTime(claim.submitted_at || claim.created_at)}</p>
        </div>

        <div className="p-6 bg-white rounded-lg shadow border border-gray-100">
          <h3 className="font-bold text-charcoal mb-4 border-b pb-2">Insurer Info</h3>
          <p className="font-medium">{claim.insurer?.name || 'Unknown'}</p>
          <p className="text-sm text-gray-500 mt-2">Claim Number:</p>
          <p className="font-medium">{claim.claim_number || 'Pending'}</p>
          {claim.insurer_details?.handler_name && (
            <>
              <p className="text-sm text-gray-500 mt-2">Handler:</p>
              <p className="font-medium">{claim.insurer_details.handler_name}</p>
            </>
          )}
        </div>

        <div className="p-6 bg-white rounded-lg shadow border border-gray-100">
          <h3 className="font-bold text-charcoal mb-4 border-b pb-2">Police Info</h3>
          <p className="text-sm text-gray-500">Case Number:</p>
          <p className="font-medium">{claim.police?.case_number || 'N/A'}</p>
        </div>
      </div>

      {claim.timeline && claim.timeline.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="font-bold text-charcoal mb-4">Timeline</h3>
          <div className="space-y-4">
            {claim.timeline.map((event, i) => (
              <div key={i} className="flex gap-4 items-start">
                <div className="w-2 h-2 mt-2 rounded-full bg-brand-500"></div>
                <div>
                  <p className="text-sm font-bold text-charcoal">{event.actor?.full_name || 'System'} <span className="text-gray-400 font-normal">({event.actor?.role || 'system'})</span></p>
                  <p className="text-xs text-gray-500">{formatDateTime(event.created_at)}</p>
                  <p className="text-sm mt-1">{event.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {claim.status === 'completed' && !claim.review && (
        <div className="bg-charcoal text-white p-6 rounded-lg shadow">
          <h3 className="font-bold text-brand-500 mb-2">How did we do?</h3>
          <p className="text-sm mb-4">Please rate your claims experience.</p>
          <textarea className="w-full p-2 text-charcoal rounded mb-4" placeholder="Leave a comment..."></textarea>
          <button className="bg-brand-500 text-white px-4 py-2 font-bold rounded">Submit Review</button>
        </div>
      )}
    </div>
  );
}

export default ClaimTracking;
