import { useState, useEffect } from 'react';
import { useStaffBase } from '@/lib/staff';
import { itemsOf } from '@/lib/utils';
import type { Page } from '@/lib/types';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { Skeleton, ErrorBanner, EmptyState } from '@/components/ui';
import { Search } from 'lucide-react';

export default function AdvisorClients() {
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const navigate = useNavigate();
  const base = useStaffBase();

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, isLoading, error } = useQuery<any[]>({
    queryKey: ['advisorClients', debouncedSearch],
    queryFn: () => api.get<Page<any>>(`/clients?limit=100&search=${encodeURIComponent(debouncedSearch)}`).then(itemsOf),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-charcoal-900">Clients</h1>
      
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-charcoal-400" />
        <input
          type="text"
          placeholder="Search clients..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-charcoal-300 rounded-md shadow-sm focus:ring-brand-500 focus:border-brand-500 sm:text-sm"
        />
      </div>

      {error && <ErrorBanner error={error} />}
      
      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : data?.length === 0 ? (
        <EmptyState message="No clients found matching your search." />
      ) : (
        <div className="overflow-hidden bg-white shadow sm:rounded-lg">
          <table className="min-w-full divide-y divide-charcoal-200">
            <thead className="bg-charcoal-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-charcoal-500 uppercase tracking-wider">Client</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-charcoal-500 uppercase tracking-wider">Contact</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-charcoal-500 uppercase tracking-wider">Activity</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-charcoal-200">
              {data?.map((client: any) => (
                <tr 
                  key={client.id} 
                  onClick={() => navigate(`${base}/clients/${client.id}`)}
                  className="hover:bg-charcoal-50 cursor-pointer transition-colors"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-charcoal-900">{client.full_name}</div>
                    <div className="text-sm text-charcoal-500">ID: {client.id_number}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-charcoal-900">{client.email}</div>
                    <div className="text-sm text-charcoal-500">{client.phone}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-charcoal-500">
                    <div className="flex flex-wrap gap-2">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                        {client.counts.policies} Policies
                      </span>
                      {client.counts.open_claims > 0 && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                          {client.counts.open_claims} Open Claims
                        </span>
                      )}
                      {client.counts.pending_requests > 0 && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-brand-100 text-brand-500">
                          {client.counts.pending_requests} Requests
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
