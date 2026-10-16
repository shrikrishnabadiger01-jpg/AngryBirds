import React, { useEffect, useState } from 'react';
import { Download, FileSearch, RefreshCw, Search } from 'lucide-react';
import { api } from '../services/api';
import { Decision, EmptyState } from './HomeTab';

export default function AuditTab() {
  const [filters, setFilters] = useState({ q: '', source: '', decision: '' });
  const [applied, setApplied] = useState(filters);
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0, page_size: 25 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => { setLoading(true); setError(''); try { setData(await api.getAudit({ ...applied, page })); } catch (err) { setError(err.message || 'Could not load audit history'); } finally { setLoading(false); } };
  useEffect(() => { load(); }, [applied, page]);
  const exportHistory = format => { const params = new URLSearchParams({ format }); Object.entries(applied).forEach(([key, value]) => value && params.set(key, value)); window.open(`/api/audit/export?${params.toString()}`, '_blank', 'noopener,noreferrer'); };
  const submit = event => { event.preventDefault(); setPage(1); setApplied({ ...filters }); };

  return <div className="page-shell"><div className="page-heading"><div><div className="eyebrow">AI Guard / Audit logs</div><h1>Audit logs</h1><p>Search recorded tool decisions, human approvals, and email security scans.</p></div><span className="subtle-count">{data.total} matching records</span></div>
    <section className="surface-card audit-page-card"><form className="audit-filters" onSubmit={submit}><label className="search-field"><Search size={15}/><input aria-label="Search audit logs" value={filters.q} onChange={event => setFilters({ ...filters, q: event.target.value })} placeholder="Search task, recipient, reason, or subject"/></label><label><span className="sr-only">Source</span><select value={filters.source} onChange={event => setFilters({ ...filters, source: event.target.value })}><option value="">All sources</option><option value="run">Agent runs</option><option value="email">Email scans</option></select></label><label><span className="sr-only">Decision</span><select value={filters.decision} onChange={event => setFilters({ ...filters, decision: event.target.value })}><option value="">All decisions</option>{['ALLOW','BLOCK','DENY','APPROVED','REJECTED','EXPIRED','SUSPICIOUS'].map(decision => <option key={decision}>{decision}</option>)}</select></label><button type="submit" className="button-primary" disabled={loading}>{loading ? <RefreshCw size={14} className="spin"/> : <Search size={14}/>}Apply</button></form>
      <div className="audit-tools"><span>Events from saved run traces and SQLite email scan records.</span><div><button className="button-secondary" onClick={() => exportHistory('csv')}><Download size={14}/> CSV</button><button className="button-secondary" onClick={() => exportHistory('json')}><Download size={14}/> JSON</button></div></div>
      {error && <div role="alert" className="inline-error">{error}</div>}
      <div className="table-scroll"><table className="data-table audit-page-table"><thead><tr><th>Timestamp</th><th>Task / Subject</th><th>Source</th><th>Attempted action</th><th>Decision</th><th>Reason / evidence</th><th>Severity</th></tr></thead><tbody>{data.items.map(item => { const details = item.details || {}; const indicators = details.indicators || []; const action = details.tool ? `${details.tool} ${JSON.stringify(details.arguments || {})}` : item.event_type; const reason = details.reason || details.message || (indicators.length ? indicators.map(ind => ind.description || ind.matched_text || ind.type).join('; ') : 'No additional reason recorded'); const severity = item.threat_level || (item.decision === 'BLOCK' ? 'High' : item.decision === 'SUSPICIOUS' ? 'Review' : '—'); return <tr key={item.id}><td className="audit-time">{item.timestamp ? new Date(item.timestamp).toLocaleString() : '—'}</td><td>{item.subject || '—'}</td><td>{item.source === 'email' ? `Email${item.actor ? ` · ${item.actor}` : ''}` : 'Agent run'}</td><td className="audit-action">{action}</td><td><Decision value={item.decision}/></td><td className="audit-reason">{reason}</td><td>{severity}</td></tr>; })}</tbody></table></div>
      {!data.items.length && !loading && <EmptyState title="No audit records found" detail="Try another search or run an agent task to create security records."/>}
      <div className="pagination"><button className="button-secondary" disabled={page <= 1 || loading} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page} of {Math.max(1, Math.ceil(data.total / data.page_size))}</span><button className="button-secondary" disabled={page * data.page_size >= data.total || loading} onClick={() => setPage(page + 1)}>Next</button></div>
    </section>
  </div>;
}
