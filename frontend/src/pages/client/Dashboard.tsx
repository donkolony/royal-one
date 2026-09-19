import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '@/lib/api';
import { formatZAR, formatDateTime } from '@/lib/utils';
import { Skeleton, ErrorBanner, EmptyState } from '@/components/ui';
import type { ClientDashboard } from '@/lib/types';

function Dashboard() {
  const { data, isLoading, error } = useQuery<ClientDashboard>({
    queryKey: ['dashboard'],
    queryFn: () => api.get<ClientDashboard>('/me/dashboard'),
    staleTime: 0,
    refetchOnWindowFocus: true,
  });

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error) return <ErrorBanner error={error as Error} />;
  if (!data) return <EmptyState message="No dashboard data found." />;

  const { client, net_worth, adviser, policies, open_claims, goals, reminders, pending_requests } = data;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-charcoal">My Dashboard | Royal Square Financial</h1>
      <h2 className="text-xl text-gray-700">Good morning, {client.full_name}</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-6 bg-white rounded-lg shadow border border-gray-100">
          <h3 className="text-sm text-gray-500 uppercase">Net Worth</h3>
          <p className="text-3xl font-bold text-charcoal mt-2">{formatZAR(net_worth.net_worth_cents)}</p>
          <p className="text-xs text-gray-400 mt-1">As of {formatDateTime(net_worth.as_of)}</p>
        </div>

        {adviser && (
          <div className="p-6 bg-charcoal text-white rounded-lg shadow">
            <h3 className="text-sm uppercase text-brand-500">Your Adviser</h3>
            <p className="text-xl font-bold mt-2">{adviser.full_name}</p>
            <div className="mt-4 space-x-4">
              {adviser.phone && <a href={`tel:${adviser.phone}`} className="text-brand-500 hover:underline">{adviser.phone}</a>}
              <a href={`mailto:${adviser.email}`} className="text-brand-500 hover:underline">{adviser.email}</a>
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-between items-center bg-gray-50 p-4 rounded-lg">
        <span className="font-semibold text-charcoal">Policies ({policies.count})</span>
        <div className="flex gap-4">
          {policies.items.slice(0, 4).map((p) => (
            <div key={p.id} className="text-sm bg-white p-2 rounded shadow-sm">
              {p.insurer.name} - <span className="text-brand-500">{p.category}</span>
            </div>
          ))}
        </div>
      </div>

      {open_claims?.items.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="font-bold text-lg mb-4 text-charcoal">Open Claims</h3>
          <div className="space-y-3">
            {open_claims.items.map((claim) => (
              <div key={claim.id} className="flex justify-between items-center border-b pb-2">
                <Link to={`/claims/${claim.id}`} className="text-blue-600 hover:underline">
                  Claim #{claim.reference || claim.id}
                </Link>
                <span className="px-2 py-1 text-xs rounded bg-brand-500 text-white">{claim.status_label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {goals?.items.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="font-bold text-lg mb-4 text-charcoal">Goals</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {goals.items.map((goal) => (
              <div key={goal.id} className="border p-4 rounded">
                <div className="flex justify-between">
                  <span className="font-semibold">{goal.title}</span>
                  <span className="text-xs">{formatZAR(goal.current_amount_cents)} / {formatZAR(goal.target_amount_cents)}</span>
                </div>
                <div className="w-full bg-gray-200 h-2 rounded mt-2">
                  <div className="bg-brand-500 h-2 rounded" style={{ width: `${(goal.current_amount_cents / goal.target_amount_cents) * 100}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-bold text-lg text-charcoal">Reminders</h3>
          <Link to="/reminders" className="text-sm text-brand-500 hover:underline">View All</Link>
        </div>
        <div className="space-y-2">
          {reminders?.upcoming.slice(0, 5).map((reminder) => (
            <div key={reminder.id} className="flex justify-between p-3 bg-gray-50 rounded">
              <span>{reminder.title}</span>
              <span className="text-xs text-red-500">{formatDateTime(reminder.due_date)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className="bg-brand-500 text-white px-3 py-1 rounded-full text-sm font-bold">{pending_requests.count}</span>
        <Link to="/requests" className="text-charcoal hover:underline">Pending requests</Link>
      </div>
    </div>
  );
}

export default Dashboard;
