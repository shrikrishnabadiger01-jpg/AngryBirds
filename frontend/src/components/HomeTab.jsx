import React from 'react';
import { Activity, ArrowRight, Shield, ShieldAlert, Clock3 } from 'lucide-react';

const prettyTime = value => value ? new Date(value).toLocaleString() : '—';

export default function HomeTab({ loading = false, health, runs = [], records = [], gmailStatus, documents = [], onNavigate }) {
  const completed = runs.filter(run => run.status === 'completed').length;
  const blocked = records.filter(item => ['BLOCK', 'DENY', 'BLOCKED'].includes(String(item.decision).toUpperCase())).length;
  const threats = records.filter(item => item.threat_level && !['low', 'none'].includes(String(item.threat_level).toLowerCase())).length;
  const sources = Number(documents.length > 0) + Number(Boolean(gmailStatus?.connected));
  const recent = records.slice(0, 6);

  return <div className="page-shell home-page">
    <div className="page-heading home-heading">
      <div><div className="eyebrow">AI Guard / Overview</div><h1>Security operations</h1><p>Live status and recent decisions from this workspace.</p></div>
      <div className="system-state"><span className={`state-dot ${!health ? 'is-neutral' : health.status === 'healthy' ? 'is-good' : 'is-bad'}`} />{!health ? 'Checking system' : health.status === 'healthy' ? 'System online' : 'System unavailable'}</div>
    </div>

    <section className="metric-grid" aria-label="Workspace metrics">
      <article className="metric-card"><span>Tasks completed</span><strong>{loading ? '—' : completed}</strong><small>{loading ? 'Loading run records' : `Among the latest ${runs.length} saved runs`}</small></article>
      <article className="metric-card"><span>Threat findings</span><strong>{loading ? '—' : threats}</strong><small>{loading ? 'Loading audit records' : `Among ${records.length} loaded audit records`}</small></article>
      <article className="metric-card metric-warn"><span>Actions blocked</span><strong>{loading ? '—' : blocked}</strong><small>{loading ? 'Loading audit records' : `Among ${records.length} loaded audit records`}</small></article>
      <article className="metric-card"><span>Connected sources</span><strong>{loading ? '—' : sources}</strong><small>{loading ? 'Checking connections' : `${documents.length ? 'Documents' : 'No documents'}${gmailStatus?.connected ? ' · Gmail' : ''}`}</small></article>
    </section>

    <div className="home-layout">
      <section className="surface-card">
        <div className="section-heading"><div><div className="eyebrow">Decision record</div><h2>Recent security decisions</h2></div><button className="text-action" onClick={() => onNavigate('audit')}>View audit logs <ArrowRight size={14}/></button></div>
        {recent.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Time</th><th>Source</th><th>Action / task</th><th>Decision</th><th>Reason</th></tr></thead><tbody>{recent.map(row => <tr key={row.id}><td>{prettyTime(row.timestamp)}</td><td>{row.source}</td><td>{row.subject || row.details?.tool || row.event_type}</td><td><Decision value={row.decision}/></td><td>{row.details?.reason || row.details?.reason_text || row.event_type}</td></tr>)}</tbody></table></div> : <EmptyState title="No security decisions recorded" detail="Run a task or inspect an email to see decisions here."/>}
      </section>
      <aside className="home-aside">
        <section className="surface-card quick-actions"><div className="eyebrow">Get started</div><h2>Quick actions</h2><button className="quick-action" onClick={() => onNavigate('workspace')}><span><Activity size={17}/></span><div><strong>Run an agent task</strong><small>Use scoped documents and review proposed actions.</small></div><ArrowRight size={16}/></button><button className="quick-action" onClick={() => onNavigate('security')}><span><Shield size={17}/></span><div><strong>Review security findings</strong><small>Inspect blocked actions and matched evidence.</small></div><ArrowRight size={16}/></button></section>
        <section className="surface-card status-card"><div className="eyebrow">System status</div><h2>Connected services</h2><StatusLine label="Agent runtime" value={health?.status === 'healthy' ? 'Available' : 'Unavailable'} good={health?.status === 'healthy'}/><StatusLine label="Document store" value={documents.length ? `${documents.length} documents` : 'No documents'} good={documents.length > 0}/><StatusLine label="Gmail inbox" value={gmailStatus?.connected ? 'Connected · read-only' : 'Not connected'} good={gmailStatus?.connected}/><button className="text-action status-link" onClick={() => onNavigate('sources')}>Manage data sources <ArrowRight size={14}/></button></section>
        <section className="surface-card activity-note"><Clock3 size={16}/><p>Activity shown here is loaded from saved run logs and security scan records.</p></section>
      </aside>
    </div>
  </div>;
}

export function Decision({ value }) {
  const normalized = String(value || 'UNKNOWN').toUpperCase();
  const kind = ['ALLOW', 'APPROVED'].includes(normalized) ? 'allow' : ['REVIEW', 'SUSPICIOUS', 'PENDING', 'AWAITING_APPROVAL'].includes(normalized) ? 'review' : ['BLOCK', 'BLOCKED', 'DENY', 'REJECTED'].includes(normalized) ? 'block' : 'neutral';
  return <span className={`decision-label decision-${kind}`}>{normalized.replaceAll('_', ' ')}</span>;
}

export function EmptyState({ title, detail }) { return <div className="empty-state"><ShieldAlert size={20}/><strong>{title}</strong><span>{detail}</span></div>; }
function StatusLine({ label, value, good }) { return <div className="status-line"><span><i className={`state-dot ${good ? 'is-good' : 'is-neutral'}`}/>{label}</span><strong>{value}</strong></div>; }
