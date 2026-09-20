import React, { useState } from 'react';
import { itemsOf } from '@/lib/utils';
import type { Page } from '@/lib/types';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { formatZAR, formatDateTime } from '@/lib/utils';
import { Skeleton, ErrorBanner, EmptyState } from '@/components/ui';
import type { Goal } from '@/lib/types';

function Goals() {
  const [showAll, setShowAll] = useState(false);

  const { data: goals, isLoading, error } = useQuery<Goal[]>({
    queryKey: ['goals', showAll],
    queryFn: () => api.get<Page<Goal>>(`/goals?status=${showAll ? 'all' : 'active'}`).then(itemsOf),
  });

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error) return <ErrorBanner error={error as Error} />;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-charcoal">My Goals</h1>
        <button 
          onClick={() => setShowAll(!showAll)}
          className="text-sm px-4 py-2 border rounded hover:bg-gray-50 text-charcoal"
        >
          {showAll ? 'Show Active Only' : 'Show All'}
        </button>
      </div>

      {!goals || goals.length === 0 ? (
        <EmptyState message="No goals found." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {goals.map((goal) => {
            const progress = goal.target_amount_cents > 0 ? (goal.current_amount_cents / goal.target_amount_cents) * 100 : 0;
            return (
              <div key={goal.id} className="bg-white p-6 rounded-lg shadow border border-gray-100">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-bold text-lg text-charcoal">{goal.title}</h3>
                    <div className="flex gap-2 mt-2">
                      <span className="px-2 py-1 text-xs bg-gray-100 rounded text-charcoal">{goal.category}</span>
                      <span className="px-2 py-1 text-xs bg-brand-500 rounded text-charcoal">{goal.type}</span>
                    </div>
                  </div>
                  <span className="text-xs text-gray-500">Target: {formatDateTime(goal.target_date)}</span>
                </div>

                <div className="mt-4">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-semibold text-charcoal">{formatZAR(goal.current_amount_cents)}</span>
                    <span className="text-gray-500">{formatZAR(goal.target_amount_cents)}</span>
                  </div>
                  <div className="w-full bg-gray-200 h-2.5 rounded-full overflow-hidden">
                    <div 
                      className="bg-charcoal h-2.5 rounded-full transition-all" 
                      style={{ width: `${Math.min(progress, 100)}%` }}
                    ></div>
                  </div>
                  <p className="text-right text-xs text-gray-400 mt-1">{progress.toFixed(1)}%</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default Goals;
