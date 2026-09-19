import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '@/lib/api';
import { Skeleton, ErrorBanner, EmptyState } from '@/components/ui';
import { format } from 'date-fns';
import { AlertCircle, Clock, FileText, Mail } from 'lucide-react';
import { AdvisorDashboard as AdvisorDashboardType } from '@/lib/types';

export default function AdvisorDashboard() {
  const { data, isLoading, error } = useQuery<AdvisorDashboardType>({
    queryKey: ['advisorDashboard'],
    queryFn: () => api.get<AdvisorDashboardType>('/advisor/dashboard'),
    staleTime: 0,
  });

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error) return <ErrorBanner error={error as any} />;
  if (!data) return <EmptyState message="No dashboard data found" />;

  const { counts, claims_by_status, needs_attention, upcoming_reminders } = data;
  const totalClaims = claims_by_status.reduce((acc, curr) => acc + curr.count, 0);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Dashboard | Royal Square Adviser Portal</h1>

      {/* Count tiles */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-slate-900">
          <p className="text-sm font-medium text-slate-500">Clients</p>
          <p className="text-2xl font-semibold text-slate-900">{counts.clients}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-slate-900">
          <p className="text-sm font-medium text-slate-500">Open Claims</p>
          <p className="text-2xl font-semibold text-slate-900">{counts.open_claims}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-slate-900">
          <p className="text-sm font-medium text-slate-500">Pending Requests</p>
          <p className="text-2xl font-semibold text-slate-900">{counts.pending_requests}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-yellow-500">
          <p className="text-sm font-medium text-slate-500">Reminders Due (7d)</p>
          <p className="text-2xl font-semibold text-slate-900">{counts.reminders_due_7d}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-red-500">
          <p className="text-sm font-medium text-slate-500">Overdue Reminders</p>
          <p className="text-2xl font-semibold text-slate-900">{counts.overdue_reminders}</p>
        </div>
      </div>

      {/* Claims by status chart */}
      <div className="bg-white p-6 shadow rounded-lg">
        <h2 className="text-lg font-medium text-slate-900 mb-4">Open Claims by Status</h2>
        <div className="flex h-8 rounded-full overflow-hidden bg-slate-100">
          {claims_by_status.map((item, i) => {
            const width = totalClaims ? (item.count / totalClaims) * 100 : 0;
            const colors = ['bg-slate-800', 'bg-yellow-500', 'bg-blue-600', 'bg-slate-400'];
            return width > 0 ? (
              <div
                key={item.status}
                style={{ width: `${width}%` }}
                className={`${colors[i % colors.length]} flex items-center justify-center text-xs text-white font-medium`}
                title={`${item.label}: ${item.count}`}
              >
                {item.count}
              </div>
            ) : null;
          })}
        </div>
        <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-600">
          {claims_by_status.map((item, i) => {
            const colors = ['text-slate-800', 'text-yellow-500', 'text-blue-600', 'text-slate-400'];
            return (
              <div key={item.status} className="flex items-center gap-1">
                <span className={`w-3 h-3 rounded-full bg-current ${colors[i % colors.length]}`} />
                <span>{item.label}: {item.count}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Needs Attention */}
        <div className="bg-white p-6 shadow rounded-lg">
          <h2 className="text-lg font-medium text-slate-900 mb-4">Needs Attention</h2>
          {needs_attention.length === 0 ? (
            <p className="text-sm text-slate-500">All caught up.</p>
          ) : (
            <div className="space-y-4">
              {needs_attention.map((item: any, idx: number) => {
                let Icon = FileText;
                let color = 'text-slate-500';
                if (item.kind === 'overdue_reminder') { Icon = Clock; color = 'text-red-500'; }
                if (item.kind === 'submitted_claim') { Icon = AlertCircle; color = 'text-blue-600'; }
                if (item.kind === 'submitted_request') { Icon = FileText; color = 'text-yellow-500'; }
                if (item.kind === 'flagged_email') { Icon = Mail; color = 'text-yellow-600'; }

                return (
                  <Link key={idx} to={`/${item.link.resource}/${item.link.id}`} className="flex items-start gap-3 p-3 hover:bg-slate-50 rounded-md transition-colors border border-slate-100">
                    <Icon className={`w-5 h-5 mt-0.5 ${color}`} />
                    <div>
                      <p className="text-sm font-medium text-slate-900">{item.title}</p>
                      <p className="text-xs text-slate-500">{item.subtitle}</p>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Upcoming Reminders */}
        <div className="bg-white p-6 shadow rounded-lg">
          <h2 className="text-lg font-medium text-slate-900 mb-4">Upcoming Reminders</h2>
          {upcoming_reminders.length === 0 ? (
            <p className="text-sm text-slate-500">No upcoming reminders.</p>
          ) : (
            <div className="space-y-3">
              {upcoming_reminders.slice(0, 10).map((reminder: any) => (
                <div key={reminder.id} className="flex justify-between items-center p-3 border-b border-slate-100 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-slate-900">{reminder.client.full_name}</p>
                    <p className="text-xs text-slate-500">{reminder.title}</p>
                  </div>
                  <div className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-1 rounded">
                    {format(new Date(reminder.due_date), 'dd MMM yyyy')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
