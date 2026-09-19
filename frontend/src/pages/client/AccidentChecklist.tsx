import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '@/lib/api';
import { Skeleton, ErrorBanner } from '@/components/ui';
import type { ClaimChecklistItem } from '@/lib/types';

function AccidentChecklist() {
  const { data: checklist, isLoading, error } = useQuery<ClaimChecklistItem[]>({
    queryKey: ['accident-checklist'],
    queryFn: () => api.get<ClaimChecklistItem[]>('/claims/checklist'),
    staleTime: 3600000,
  });

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error) return <ErrorBanner error={error as Error} />;

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-charcoal mb-2">Report an Accident</h1>
        <h2 className="text-xl font-medium text-amber-600 bg-amber-50 p-4 rounded-lg border border-amber-200">
          Stay calm. Here is what to collect at the scene.
        </h2>
      </div>

      <div className="space-y-4">
        {checklist?.map((item, index) => {
          const isPolice = item.title.toLowerCase().includes('police') || index === 7;
          return (
            <div key={index} className={`p-4 rounded-lg border ${isPolice ? 'bg-amber-50 border-amber-300' : 'bg-white border-gray-200'} flex gap-4`}>
              <div className={`w-8 h-8 flex-shrink-0 flex items-center justify-center rounded-full font-bold text-sm ${isPolice ? 'bg-amber-600 text-white' : 'bg-brand-500 text-white'}`}>
                {index + 1}
              </div>
              <div>
                <h3 className={`font-bold ${isPolice ? 'text-amber-800' : 'text-charcoal'}`}>
                  {item.title} {item.upload_kind && '📷'}
                </h3>
                <p className={`text-sm mt-1 ${isPolice ? 'text-amber-700 font-medium' : 'text-gray-600'}`}>
                  {isPolice ? 'Report to the police within 48 hours. ' : ''}
                  {item.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-gray-50 p-6 rounded-lg text-center space-y-4 border border-gray-200">
        <p className="text-gray-600">You can register your claim from the safety of home if needed.</p>
        <Link 
          to="/claims/new" 
          className="inline-block px-8 py-4 bg-brand-500 text-white font-bold rounded-lg shadow-lg hover:bg-gray-800 transition-colors w-full sm:w-auto"
        >
          Register a Claim
        </Link>
      </div>
    </div>
  );
}

export default AccidentChecklist;
