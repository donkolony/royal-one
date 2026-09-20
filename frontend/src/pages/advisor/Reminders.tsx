import { useState } from 'react';
import { itemsOf } from '@/lib/utils';
import type { Page } from '@/lib/types';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { api } from '@/lib/api';
import { Skeleton, ErrorBanner, EmptyState } from '@/components/ui';

export default function AdvisorReminders() {
  const [filter, setFilter] = useState('pending');
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery<any[]>({
    queryKey: ['advisorReminders', filter],
    queryFn: () => api.get<Page<any>>(`/reminders?limit=100`).then(itemsOf),
  });

  const markDone = useMutation({
    mutationFn: (id: string) => api.post(`/reminders/${id}/complete`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['advisorReminders'] }),
  });

  const runCheck = useMutation({
    mutationFn: () => api.post('/reminders/run-check', {}),
    onSuccess: (res: any) => {
      alert(`${res.created_count} new reminders created for ${res.clients_affected} clients`);
      queryClient.invalidateQueries({ queryKey: ['advisorReminders'] });
    },
  });

  if (isLoading) return <Skeleton className="h-[600px] w-full" />;
  if (error) return <ErrorBanner error={error} />;

  const reminders = data || [];
  const displayReminders = filter === 'pending' ? reminders.filter((r: any) => r.status === 'pending') : reminders;

  const grouped = {
    overdue: displayReminders.filter((r: any) => r.urgency === 'overdue'),
    due_soon: displayReminders.filter((r: any) => r.urgency === 'due_soon'),
    upcoming: displayReminders.filter((r: any) => r.urgency === 'upcoming'),
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-charcoal-900">Reminders</h1>
        <div className="flex gap-3">
          <button 
            onClick={() => runCheck.mutate()}
            className="px-4 py-2 bg-charcoal-100 text-charcoal-700 text-sm font-medium rounded hover:bg-charcoal-200"
          >
            Run Automated Check
          </button>
          <button className="px-4 py-2 bg-brand-500 text-white text-sm font-medium rounded hover:bg-brand-600">
            Add Reminder
          </button>
        </div>
      </div>

      <div className="flex gap-2 border-b border-charcoal-200 pb-2">
        <button onClick={() => setFilter('pending')} className={`px-3 py-1 rounded-full text-sm font-medium ${filter === 'pending' ? 'bg-charcoal-800 text-white' : 'bg-charcoal-100 text-charcoal-700'}`}>Pending</button>
        <button onClick={() => setFilter('all')} className={`px-3 py-1 rounded-full text-sm font-medium ${filter === 'all' ? 'bg-charcoal-800 text-white' : 'bg-charcoal-100 text-charcoal-700'}`}>All</button>
      </div>

      {displayReminders.length === 0 ? (
        <EmptyState message="No reminders found." />
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped).map(([urgency, items]) => {
            if (items.length === 0) return null;
            return (
              <div key={urgency} className="space-y-4">
                <h3 className="text-lg font-semibold text-charcoal-800 capitalize border-b border-charcoal-200 pb-2">
                  {urgency.replace('_', ' ')}
                </h3>
                <div className="bg-white shadow rounded-lg divide-y divide-charcoal-100">
                  {items.map((r: any) => (
                    <div key={r.id} className="p-4 flex items-center justify-between hover:bg-charcoal-50">
                      <div className="flex items-center gap-4">
                        <span className="bg-charcoal-100 text-charcoal-700 px-2.5 py-0.5 rounded-full text-xs font-medium truncate max-w-[150px]">
                          {r.client_name}
                        </span>
                        <div>
                          <p className="text-sm font-medium text-charcoal-900">{r.title}</p>
                          <p className="text-xs text-charcoal-500">Due: {new Date(r.due_date).toLocaleDateString()} | Type: {r.type.replace('_', ' ')}</p>
                        </div>
                      </div>
                      {r.status === 'pending' && (
                        <button 
                          onClick={() => markDone.mutate(r.id)}
                          className="px-3 py-1.5 text-xs font-medium text-charcoal-700 border border-charcoal-300 rounded hover:bg-charcoal-50"
                        >
                          Mark Done
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
