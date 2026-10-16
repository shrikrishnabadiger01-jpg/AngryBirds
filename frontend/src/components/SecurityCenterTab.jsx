import React, { useEffect, useState } from 'react';
import { AlertTriangle, ArrowRight, RefreshCw, ShieldCheck, ShieldAlert } from 'lucide-react';
import { api } from '../services/api';
import { Decision, EmptyState } from './HomeTab';

export default function SecurityCenterTab({ onOpenTests }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');
  const load = async () => { setLoading(true); setError(''); try { const response = await api.getAudit({ page_size: 100 }); setRecords(response.items || []); } catch (e) { setError(e.message || 'Could not load security records'); } finally { setLoading(false); } };
  useEffect(() => { load(); }, []);
  const findings = records.filter(item => {
    const blocked = ['BLOCK', 'DENY', 'BLOCKED'].includes(String(item.decision).toUpperCase());
    const indicators = item.details?.indicators || [];
    const suspicious = indicators.length > 0 || ['SUSPICIOUS', 'REVIEW'].includes(String(item.decision).toUpperCase()) || item.threat_level && !['low', 'none'].includes(String(item.threat_level).toLowerCase());
    return filter === 'all' || (filter === 'blocked' ? blocked : suspicious);
  });

  return <div className="page-shell"><div className="page-heading"><div><div className="eyebrow">AI Guard / Security center</div><h1>Security investigation</h1><p>Review policy decisions and evidence captured from agent runs and email scans.</p></div><div className="button-row"><button className="button-secondary" onClick={load} disabled={loading}>{loading ? <RefreshCw size={14} className="spin"/> : <RefreshCw size={14}/>} Refresh</button><button className="button-primary" onClick={onOpenTests}>Run deterministic checks <ArrowRight size={15}/></button></div></div>
    <div className="finding-summary"><div><ShieldAlert size={19}/><span><strong>{records.filter(r => ['BLOCK', 'DENY', 'BLOCKED'].includes(String(r.decision).toUpperCase())).length}</strong> blocked decisions in loaded records</span></div><div><AlertTriangle size={19}/><span><strong>{records.filter(r => (r.details?.indicators || []).length > 0 || r.threat_level && !['low', 'none'].includes(String(r.threat_level).toLowerCase())).length}</strong> records with threat evidence</span></div><div><ShieldCheck size={19}/><span>Decisions are loaded from persisted audit data</span></div></div>
    <section className="surface-card investigation-list"><div className="section-heading"><div><div className="eyebrow">Saved records</div><h2>Findings and policy decisions</h2></div><label className="filter-control"><span className="sr-only">Filter security records</span><select value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All records</option><option value="blocked">Blocked actions</option><option value="suspicious">Threat evidence</option></select></label></div>
      {error && <div role="alert" className="inline-error">{error}</div>}{loading ? <div className="loading-state"><RefreshCw className="spin" size={18}/> Loading saved security records…</div> : findings.length ? <div className="finding-list">{findings.map(item => <Finding key={item.id} item={item}/>)}</div> : <EmptyState title="No matching security records" detail="No findings match this filter in the saved audit data."/>}
    </section>
  </div>;
}

function Finding({ item }) {
  const details = item.details || {};
  const indicators = details.indicators || [];
  const proposal = details.arguments || details.proposal || {};
  const reason = details.reason || details.reason_text || details.message || item.event_type;
  const source = item.source === 'email' ? `Email · ${item.actor || 'sender unavailable'}` : `Agent run · ${item.run_id || 'reference unavailable'}`;
  return <article className="finding-card"><div className="finding-top"><div><div className="eyebrow">{source}</div><h3>{item.subject || details.tool || item.event_type}</h3></div><Decision value={item.decision}/></div><div className="finding-fields"><Field label="Timestamp" value={item.timestamp ? new Date(item.timestamp).toLocaleString() : 'Not recorded'}/><Field label="Original task / subject" value={item.subject || 'Not recorded'}/><Field label="Proposed action" value={details.tool ? `${details.tool} ${JSON.stringify(proposal)}` : item.event_type}/><Field label="Policy reason" value={reason}/><Field label="Audit reference" value={item.id}/></div>{indicators.length > 0 && <div className="evidence-box"><strong>Matched evidence</strong>{indicators.map((indicator, index) => <p key={index}><b>{indicator.type || indicator.signal || 'Signal'}:</b> {indicator.description || indicator.matched_text || JSON.stringify(indicator)}</p>)}</div>}</article>;
}
function Field({ label, value }) { return <div className="finding-field"><span>{label}</span><strong>{value || 'Not recorded'}</strong></div>; }
