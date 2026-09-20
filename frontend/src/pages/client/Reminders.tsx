import React, { useState } from 'react';
import { itemsOf } from '@/lib/utils';
import type { Page } from '@/lib/types';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';
import { Skeleton, ErrorBanner, EmptyState } from '@/components/ui';
import type { Reminder } from '@/lib/types';

function Reminders() {
  const [filter, setFilter] = useState<'pending' | 'done' | 'all'>('pending');
  const queryClient = useQueryClient();

  const { data: reminders, isLoading, error } = useQuery<Reminder[]>({
    queryKey: ['reminders', filter],
    queryFn: () => api.get<Page<Reminder>>(`/reminders?audience=client&status=${filter}&limit=100`).then(itemsOf),
  });

  const markDone = useMutation({
    mutationFn: (id: string) => api.post(`/reminders/${id}/complete`),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['reminders', filter] });
      const previous = queryClient.getQueryData<Reminder[]>(['reminders', filter]);
      
      queryClient.setQueryData<Reminder[]>(['reminders', filter], (old) => {
        if (!old) return old;
        if (filter === 'pending') return old.filter((r) => r.id !== id);
        return old.map((r) => r.id === id ? { ...r, status: 'done' as const } : r);
      });
      return { previous };
    },
    onError: (err, id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['reminders', filter], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['reminders', filter] });
    }
  });

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error) return <ErrorBanner error={error as Error} />;

  const grouped = (reminders || []).reduce((acc: Record<'overdue' | 'soon' | 'upcoming', Reminder[]>, reminder) => {
    const isOverdue = new Date(reminder.due_date) < new Date() && reminder.status !== 'done';
    const isSoon = new Date(reminder.due_date) < new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) && reminder.status !== 'done';
    
    if (isOverdue) acc.overdue.push(reminder);
    else if (isSoon) acc.soon.push(reminder);
    else acc.upcoming.push(reminder);
    return acc;
  }, { overdue: [], soon: [], upcoming: [] });

  const renderGroup = (title: string, list: Reminder[], colorClass: string) => {
    if (list.length === 0) return null;
    return (
      <div className="mb-8">
        <h3 className={`font-bold mb-4 ${colorClass}`}>{title}</h3>
        <div className="space-y-3">
          {list.map((r) => (
            <div key={r.id} className="flex justify-between items-center p-4 bg-white rounded-lg shadow-sm border border-gray-100">
              <div>
                <p className="font-medium text-charcoal">{r.title}</p>
                <p className="text-sm text-gray-500">Due: {formatDateTime(r.due_date)}</p>
              </div>
              {r.status !== 'done' && (
                <button 
                  onClick={() => markDone.mutate(r.id)}
                  className="px-4 py-2 bg-brand-500 text-white text-sm font-medium rounded hover:bg-brand-500 transition-colors"
                >
                  Mark Done
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-charcoal">Reminders</h1>
      
      <div className="flex gap-2 mb-6">
        {['pending', 'done', 'all'].map(t => (
          <button 
            key={t}
            onClick={() => setFilter(t as any)}
            className={`px-4 py-2 rounded capitalize text-sm font-medium ${filter === t ? 'bg-brand-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          >
            {t}
          </button>
        ))}
      </div>

      {!reminders || reminders.length === 0 ? (
        <EmptyState message="No reminders found." />
      ) : (
        <div>
          {renderGroup('OVERDUE', grouped.overdue, 'text-red-600')}
          {renderGroup('DUE SOON', grouped.soon, 'text-amber-600')}
          {renderGroup('UPCOMING / OTHER', grouped.upcoming, 'text-charcoal')}
        </div>
      )}
    </div>
  );
}

export default Reminders;
