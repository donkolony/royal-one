import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { Skeleton, ErrorBanner, EmptyState } from '@/components/ui';

export interface ClaimsPipelineColumn {
  status: string;
  label: string;
  claims: any[];
}

export default function AdvisorClaimsPipeline() {
  const [includeClosed, setIncludeClosed] = useState(false);
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery<{ columns: ClaimsPipelineColumn[] }>({
    queryKey: ['advisorClaimsPipeline', includeClosed],
    queryFn: () => api.get(`/claims/pipeline?include_closed=${includeClosed}`),
    refetchOnWindowFocus: true,
  });

  if (isLoading) return <Skeleton className="h-[600px] w-full" />;
  if (error) return <ErrorBanner error={error as any} />;

  const columns = data?.columns ?? [];

  return (
    <div className="h-full flex flex-col space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Claims Pipeline</h1>
        <label className="flex items-center gap-2 cursor-pointer">
          <input 
            type="checkbox" 
            checked={includeClosed} 
            onChange={(e) => setIncludeClosed(e.target.checked)}
            className="rounded border-slate-300 text-yellow-500 focus:ring-yellow-500"
          />
          <span className="text-sm font-medium text-slate-700">Include Closed</span>
        </label>
      </div>

      <div className="flex-1 flex gap-4 overflow-x-auto pb-4 items-start">
        {columns.map((col) => {
          return (
            <div key={col.status} className="w-80 flex-shrink-0 bg-slate-100 rounded-lg flex flex-col max-h-[80vh]">
              <div className="p-3 flex items-center justify-between border-b border-slate-200">
                <h3 className="font-semibold text-slate-800 capitalize">{col.label}</h3>
                <span className="bg-slate-200 text-slate-600 py-0.5 px-2 rounded-full text-xs font-medium">
                  {col.claims.length}
                </span>
              </div>
              <div className="p-3 overflow-y-auto space-y-3 flex-1">
                {col.claims.length === 0 ? (
                  <p className="text-sm text-slate-500 text-center py-4">No claims</p>
                ) : (
                  col.claims.map((claim) => (
                    <div 
                      key={claim.id} 
                      onClick={() => navigate(`/advisor/claims/${claim.id}`)}
                      className="bg-white p-3 rounded shadow-sm border border-slate-200 cursor-pointer hover:shadow-md transition-shadow"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-xs font-medium bg-slate-100 px-2 py-1 rounded text-slate-600">
                          {claim.reference || 'No Ref'}
                        </span>
                        {claim.days_in_status >= 7 && (
                          <span className="text-xs font-medium bg-red-100 text-red-700 px-2 py-1 rounded">
                            {claim.days_in_status}d
                          </span>
                        )}
                      </div>
                      <p className="font-medium text-slate-900 text-sm mb-1">{claim.client.full_name}</p>
                      <p className="text-xs text-slate-500 mb-2">{claim.insurer?.name}</p>
                      
                      {claim.hire_car_status && claim.hire_car_status !== 'not_required' && (
                        <div className="flex items-center gap-1 text-xs text-blue-600 font-medium">
                          🚗 Hire Car: {claim.hire_car_status.replace('_', ' ')}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
