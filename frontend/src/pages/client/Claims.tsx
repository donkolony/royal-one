import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { api } from '@/lib/api';
import { itemsOf, formatDate } from '@/lib/utils';
import { EmptyState, ErrorBanner, Skeleton, StatusPill } from '@/components/ui';
import type { ClaimSummary, Page } from '@/lib/types';

export default function Claims() {
  const query = useQuery({ queryKey: ['claims'], queryFn: () => api.get<Page<ClaimSummary>>('/claims?limit=100') });
  return <>
    <div className="page-heading"><h1>Your claims</h1><Link to="/claims/new" className="button"><Plus size={17}/>Register a claim</Link></div>
    {query.isLoading ? <Skeleton className="h-64"/> : query.error ? <ErrorBanner error={query.error}/> : <div className="table-scroll"><table><thead><tr><th>Claim</th><th>Insurer</th><th>Submitted</th><th>Status</th></tr></thead><tbody>{itemsOf(query.data).map(claim => <tr key={claim.id}><td><Link className="table-link" to={claim.status === "draft" ? `/claims/new?draft=${claim.id}` : `/claims/${claim.id}`}>{claim.reference || 'Draft claim'}</Link></td><td>{claim.insurer?.name ?? 'Not selected'}</td><td>{claim.submitted_at ? formatDate(claim.submitted_at) : 'Draft'}</td><td><StatusPill status={claim.status}/></td></tr>)}</tbody></table>{!itemsOf(query.data).length && <EmptyState message="No claims yet."/>}</div>}
  </>;
}
