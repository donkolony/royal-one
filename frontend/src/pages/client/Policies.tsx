import React, { useState } from 'react';
import { itemsOf, humanize } from '@/lib/utils';
import type { Page } from '@/lib/types';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { formatZAR, formatDateTime } from '@/lib/utils';
import { Skeleton, ErrorBanner, EmptyState } from '@/components/ui';
import type { Policy } from '@/lib/types';

function Policies() {
  const [category, setCategory] = useState<string>('');
  const [status, setStatus] = useState<string>('');

  const { data: meta } = useQuery<{ policy_categories: string[] }>({
    queryKey: ['meta'],
    queryFn: () => api.get<{ policy_categories: string[] }>('/meta'),
  });

  const { data: policies, isLoading, error } = useQuery<Policy[]>({
    queryKey: ['policies', category, status],
    queryFn: () => {
      const q = new URLSearchParams();
      if (category) q.set('category', category);
      if (status) q.set('status', status);
      const qs = q.toString();
      return api.get<Page<Policy>>(`/policies${qs ? `?${qs}` : ''}`).then(itemsOf);
    },
  });

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error) return <ErrorBanner error={error as Error} />;

  const filteredPolicies = policies || [];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-charcoal">My Policies</h1>
      
      <div className="flex gap-4 mb-6">
        <select 
          value={category} 
          onChange={e => setCategory(e.target.value)}
          className="p-2 border rounded bg-white text-charcoal focus:ring-brand-500"
        >
          <option value="">All Categories</option>
          {meta?.policy_categories?.map((c) => (
            <option key={c} value={c}>{humanize(c)}</option>
          ))}
        </select>

        <select 
          value={status} 
          onChange={e => setStatus(e.target.value)}
          className="p-2 border rounded bg-white text-charcoal focus:ring-brand-500"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="pending">Pending</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {filteredPolicies.length === 0 ? (
        <EmptyState message="No policies found." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredPolicies.map((p) => (
            <div key={p.id} className="bg-white p-6 rounded-lg shadow-md border border-gray-100 flex flex-col h-full">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center text-xs text-gray-500 overflow-hidden">
                  Logo
                </div>
                <div>
                  <h3 className="font-bold text-charcoal">{p.insurer.name}</h3>
                  <p className="text-sm text-gray-500">{p.product_name}</p>
                </div>
              </div>
              
              <div className="flex gap-2 mb-4">
                <span className="px-2 py-1 text-xs bg-gray-100 text-charcoal rounded">{p.category}</span>
                <span className="px-2 py-1 text-xs bg-brand-500 text-white rounded">{p.status}</span>
              </div>

              <div className="space-y-2 text-sm mt-auto">
                <div className="flex justify-between"><span className="text-gray-500">Policy No:</span> <span>{p.policy_number}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Premium:</span> <span>{formatZAR(p.premium_cents || 0)}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Cover:</span> <span>{formatZAR(p.cover_amount_cents || 0)}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Renewal:</span> <span>{formatDateTime(p.renewal_date)}</span></div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Policies;
