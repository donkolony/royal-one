import { useState } from 'react';
import { itemsOf } from '@/lib/utils';
import type { Page } from '@/lib/types';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { useStaffBase } from '@/lib/staff';
import { api } from '@/lib/api';
import { formatZAR } from '@/lib/utils';
import { Skeleton, ErrorBanner, EmptyState } from '@/components/ui';
import { ClientDetail, ClientDashboard } from '@/lib/types';

export default function AdvisorClientDetail() {
  const { clientId } = useParams<{ clientId: string }>();
  const navigate = useNavigate();
  const base = useStaffBase();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('overview');

  const { data: client, isLoading, error } = useQuery<ClientDetail>({
    queryKey: ['client', clientId],
    queryFn: () => api.get<ClientDetail>(`/clients/${clientId}`),
    enabled: !!clientId,
  });

  const { data: dashboard } = useQuery<ClientDashboard>({
    queryKey: ['clientDashboard', clientId],
    queryFn: () => api.get<ClientDashboard>(`/clients/${clientId}/dashboard`),
    enabled: !!clientId && activeTab === 'overview',
  });

  const { data: goals } = useQuery<any[]>({
    queryKey: ['goals', clientId],
    queryFn: () => api.get<Page<any>>(`/goals?limit=100&client_id=${clientId}`).then(itemsOf),
    enabled: !!clientId && activeTab === 'goals',
  });

  const { data: finItems } = useQuery<any[]>({
    queryKey: ['financialItems', clientId],
    queryFn: () => api.get<Page<any>>(`/financial-items?limit=100&client_id=${clientId}`).then(itemsOf),
    enabled: !!clientId && activeTab === 'financial',
  });

  const { data: reminders } = useQuery<any[]>({
    queryKey: ['reminders', clientId],
    queryFn: () => api.get<Page<any>>(`/reminders?limit=100&client_id=${clientId}`).then(itemsOf),
    enabled: !!clientId && activeTab === 'reminders',
  });

  if (isLoading) return <Skeleton className="h-[600px] w-full" />;
  if (error) return <ErrorBanner error={error as any} />;
  if (!client) return <EmptyState message="Client not found" />;

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'goals', label: 'Goals' },
    { id: 'financial', label: 'Financial Items' },
    { id: 'reminders', label: 'Reminders' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(`${base}/clients`)} className="text-charcoal-500 hover:text-charcoal-700">
          ← Back
        </button>
        <h1 className="text-2xl font-bold text-charcoal-900">{client.full_name}</h1>
      </div>

      <div className="border-b border-charcoal-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-brand-500 text-brand-600'
                  : 'border-transparent text-charcoal-500 hover:text-charcoal-700 hover:border-charcoal-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white p-6 shadow rounded-lg space-y-4">
            <h2 className="text-lg font-bold text-charcoal-900">Client Details</h2>
            <div className="space-y-2 text-sm text-charcoal-700">
              <p><span className="font-medium w-32 inline-block">Email:</span> {client.email}</p>
              <p><span className="font-medium w-32 inline-block">Phone:</span> {client.phone}</p>
            </div>
            
            <h3 className="text-md font-semibold text-charcoal-800 pt-4 border-t border-charcoal-100 mt-4">Important Dates</h3>
            <div className="space-y-2 text-sm text-charcoal-700">
              <p><span className="font-medium w-48 inline-block">Client Since:</span> {client.client_since ? new Date(client.client_since).toLocaleDateString() : 'N/A'}</p>
              <p><span className="font-medium w-48 inline-block">Date of Birth:</span> {client.date_of_birth ? new Date(client.date_of_birth).toLocaleDateString() : 'N/A'}</p>
              <p><span className="font-medium w-48 inline-block">Last Annual Review:</span> {client.last_annual_review_date ? new Date(client.last_annual_review_date).toLocaleDateString() : 'N/A'}</p>
              <p><span className="font-medium w-48 inline-block">Driver's Licence Expiry:</span> {client.drivers_licence_expiry ? new Date(client.drivers_licence_expiry).toLocaleDateString() : 'N/A'}</p>
            </div>
          </div>

          <div className="bg-white p-6 shadow rounded-lg space-y-4">
            <h2 className="text-lg font-bold text-charcoal-900">Overview Dashboard</h2>
            {!dashboard ? <Skeleton className="h-32" /> : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-charcoal-50 p-3 rounded">
                    <p className="text-xs text-charcoal-500 font-medium">Net Worth</p>
                    <p className="text-xl font-bold text-charcoal-900">{formatZAR(dashboard.net_worth.net_worth_cents)}</p>
                  </div>
                  <div className="bg-charcoal-50 p-3 rounded">
                    <p className="text-xs text-charcoal-500 font-medium">Monthly Premium</p>
                    <p className="text-xl font-bold text-charcoal-900">{formatZAR(dashboard.policies.items.reduce((sum, p) => sum + (p.premium_cents || 0), 0))}</p>
                  </div>
                </div>
                
                {dashboard.open_claims.items?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-charcoal-800 mb-2">Recent Claims</h3>
                    <div className="space-y-2">
                      {dashboard.open_claims.items.map((c: any) => (
                        <div key={c.id} className="text-sm flex justify-between p-2 bg-charcoal-50 rounded">
                          <span>{c.insurer?.name || 'No Insurer'}</span>
                          <span className="font-medium">{c.status_label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'goals' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold text-charcoal-900">Financial Goals</h2>
            <button className="px-4 py-2 bg-brand-500 text-white text-sm font-medium rounded hover:bg-brand-600">
              Add Goal
            </button>
          </div>
          {!goals?.length ? <EmptyState message="No goals set" /> : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {goals.map((g: any) => {
                const progress = g.target_amount_cents ? Math.min(100, Math.round((g.current_amount_cents / g.target_amount_cents) * 100)) : 0;
                return (
                  <div key={g.id} className="bg-white p-4 shadow rounded-lg">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-semibold text-charcoal-900">{g.title}</h3>
                      <span className="text-xs bg-charcoal-100 px-2 py-1 rounded text-charcoal-600 capitalize">{g.category.replace('_', ' ')}</span>
                    </div>
                    <p className="text-xs text-charcoal-500 mb-4">{g.description}</p>
                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="font-medium">{formatZAR(g.current_amount_cents)}</span>
                        <span className="text-charcoal-500">Target: {formatZAR(g.target_amount_cents)}</span>
                      </div>
                      <div className="w-full bg-charcoal-200 rounded-full h-2">
                        <div className="bg-brand-500 h-2 rounded-full" style={{ width: `${progress}%` }}></div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {activeTab === 'financial' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold text-charcoal-900">Financial Items</h2>
            <button className="px-4 py-2 bg-charcoal-800 text-white text-sm font-medium rounded hover:bg-charcoal-700">
              Add Item
            </button>
          </div>
          {!finItems?.length ? <EmptyState message="No financial items" /> : (
            <div className="bg-white shadow rounded-lg overflow-hidden">
              <table className="min-w-full divide-y divide-charcoal-200">
                <thead className="bg-charcoal-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-charcoal-500 uppercase tracking-wider">Item</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-charcoal-500 uppercase tracking-wider">Kind</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-charcoal-500 uppercase tracking-wider">Category</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-charcoal-500 uppercase tracking-wider">Amount</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-charcoal-200">
                  {finItems.map((item: any) => (
                    <tr key={item.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-charcoal-900">{item.label}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-charcoal-500 capitalize">
                        <span className={`px-2 py-1 rounded text-xs ${item.kind === 'asset' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                          {item.kind}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-charcoal-500 capitalize">{item.category.replace('_', ' ')}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-charcoal-900">{formatZAR(item.amount_cents)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'reminders' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold text-charcoal-900">Client Reminders</h2>
            <button className="px-4 py-2 bg-brand-500 text-white text-sm font-medium rounded hover:bg-brand-600">
              Add Reminder
            </button>
          </div>
          {!reminders?.length ? <EmptyState message="No reminders for this client" /> : (
            <div className="bg-white shadow rounded-lg divide-y divide-charcoal-100">
              {reminders.map((r: any) => (
                <div key={r.id} className="p-4 flex items-center justify-between hover:bg-charcoal-50">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs bg-charcoal-100 text-charcoal-600 px-2 py-0.5 rounded capitalize">{r.type.replace('_', ' ')}</span>
                      {r.audience !== 'advisor_only' && <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">Client Visible</span>}
                      <span className={`text-xs px-2 py-0.5 rounded capitalize ${r.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-brand-100 text-brand-500'}`}>{r.status}</span>
                    </div>
                    <p className="text-sm font-medium text-charcoal-900">{r.title}</p>
                    <p className="text-xs text-charcoal-500">Due: {new Date(r.due_date).toLocaleDateString()}</p>
                  </div>
                  {r.status === 'pending' && (
                    <button className="px-3 py-1.5 text-xs font-medium text-charcoal-700 border border-charcoal-300 rounded hover:bg-charcoal-50">
                      Mark Done
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
