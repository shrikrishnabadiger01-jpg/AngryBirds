import React, { useEffect, useState } from 'react';
import { Download, FileSearch, RefreshCw } from 'lucide-react';
import { api } from '../services/api';

export default function AuditTab() {
  const [filters, setFilters] = useState({ q: '', source: '', decision: '' });
  const [applied, setApplied] = useState(filters);
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0, page_size: 25 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setData(await api.getAudit({ ...applied, page }));
    } catch (err) {
      setError(err.message || 'Could not load audit history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [applied, page]);

  const exportHistory = (format) => {
    const params = new URLSearchParams({ format });
    Object.entries(applied).forEach(([key, value]) => value && params.set(key, value));
    window.open(`/api/audit/export?${params.toString()}`, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="main-content">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 26, fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: 10 }}>
          <FileSearch size={24} color="#10b981" /> Persistent Audit History
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginTop: 5 }}>
          Run tool decisions, approval outcomes, and saved email security scans.
        </p>
      </div>

      <section className="glass-panel">
        <form onSubmit={(event) => { event.preventDefault(); setPage(1); setApplied({ ...filters }); }} style={{ display: 'grid', gridTemplateColumns: 'minmax(200px, 2fr) repeat(2, minmax(140px, 1fr)) auto', gap: 10, alignItems: 'end' }}>
          <label className="form-group"><span className="form-label">Search history</span><input className="form-input" value={filters.q} onChange={event => setFilters({ ...filters, q: event.target.value })} placeholder="Task, recipient, reason, subject..." /></label>
          <label className="form-group"><span className="form-label">Source</span><select className="form-select" value={filters.source} onChange={event => setFilters({ ...filters, source: event.target.value })}><option value="">All sources</option><option value="run">Agent runs</option><option value="email">Email scans</option></select></label>
          <label className="form-group"><span className="form-label">Decision</span><select className="form-select" value={filters.decision} onChange={event => setFilters({ ...filters, decision: event.target.value })}><option value="">All decisions</option><option>ALLOW</option><option>BLOCK</option><option>DENY</option><option>APPROVED</option><option>EXPIRED</option><option>SUSPICIOUS</option></select></label>
          <button type="submit" className="btn-approve" disabled={loading} style={{ padding: '10px 14px' }}>{loading ? <RefreshCw size={14} className="animate-spin" /> : 'Apply filters'}</button>
        </form>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, margin: '18px 0 12px' }}>
          <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{data.total} matching events</span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" className="btn-deny" onClick={() => exportHistory('json')}><Download size={13} /> JSON</button>
            <button type="button" className="btn-deny" onClick={() => exportHistory('csv')}><Download size={13} /> CSV</button>
          </div>
        </div>

        {error && <p role="alert" style={{ color: '#fb7185', padding: 12 }}>{error}</p>}
        <div className="audit-table-wrapper">
          <table className="audit-table">
            <thead><tr><th>Time</th><th>Source / Event</th><th>Decision</th><th>Task / Subject</th><th>Details</th></tr></thead>
            <tbody>
              {data.items.map(item => (
                <tr key={item.id}>
                  <td style={{ whiteSpace: 'nowrap' }}>{item.timestamp ? new Date(item.timestamp).toLocaleString() : '—'}</td>
                  <td>{item.source} / {item.event_type}</td>
                  <td><span className={item.decision === 'ALLOW' || item.decision === 'APPROVED' ? 'badge-decision-allow' : 'badge-decision-block'}>{item.decision}</span></td>
                  <td style={{ maxWidth: 260, overflowWrap: 'anywhere' }}>{item.subject}</td>
                  <td style={{ minWidth: 240, maxWidth: 440, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', fontSize: 11 }}>{JSON.stringify(item.details)}</td>
                </tr>
              ))}
              {!data.items.length && !loading && <tr><td colSpan="5" style={{ textAlign: 'center', padding: 24 }}>No matching audit events.</td></tr>}
            </tbody>
          </table>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 12, marginTop: 14 }}>
          <button type="button" className="btn-deny" disabled={page <= 1 || loading} onClick={() => setPage(page - 1)}>Previous</button>
          <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Page {page} of {Math.max(1, Math.ceil(data.total / data.page_size))}</span>
          <button type="button" className="btn-deny" disabled={page * data.page_size >= data.total || loading} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      </section>
    </div>
  );
}
