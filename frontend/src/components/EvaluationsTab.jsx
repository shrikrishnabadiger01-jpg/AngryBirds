import React, { useState } from 'react';
import { 
  Activity, ShieldCheck, Download, RefreshCw, Play, Filter 
} from 'lucide-react';

export default function EvaluationsTab({
  evaluations,
  documents = [],
  isComparing,
  onRunComparison,
  onRefresh,
}) {
  const [docId, setDocId] = useState('project_report_injected');
  const [task, setTask] = useState('Summarize the delayed milestones and their reasons.');
  const [allowEmail, setAllowEmail] = useState(false);
  const [modeFilter, setModeFilter] = useState('Both');
  const [latestComparison, setLatestComparison] = useState(null);

  const metrics = evaluations?.metrics || {
    total_runs: 0,
    completed_runs: 0,
    blocked_calls: 0,
    unauthorized_executed: 0,
    marker_leaked: 0,
  };

  const rows = evaluations?.rows || [];
  const filteredRows = rows.filter(r => modeFilter === 'Both' || r.mode === modeFilter);

  const handleRunComparison = async (e) => {
    e.preventDefault();
    if (isComparing || !task.trim()) return;
    const res = await onRunComparison({
      task: task.trim(),
      document_id: docId,
      allow_email: allowEmail,
    });
    if (res) {
      setLatestComparison(res);
    }
  };

  const handleExportCsv = () => {
    window.open('/api/evaluations/export-csv', '_blank');
  };

  return (
    <div className="main-content">
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16, marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: '26px', fontWeight: 800, color: '#ffffff', display: 'flex', alignItems: 'center', gap: 10 }}>
            <Activity size={26} color="#10b981" />
            Security Gate Evaluations & Benchmarking
          </h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: 4 }}>
            Empirical measurement of backend policy enforcement: comparing identical tasks with Gate ON vs Gate OFF.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            type="button"
            onClick={onRefresh}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 14px',
              borderRadius: '8px',
              background: 'rgba(6, 18, 14, 0.7)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={14} />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={rows.length === 0}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 16px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #10b981 0%, #0d9488 100%)',
              border: 'none',
              color: '#ffffff',
              fontWeight: 600,
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            <Download size={14} />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-title">Total Evaluated Runs</div>
          <div className="metric-value">{metrics.total_runs}</div>
          <div className="metric-desc">Historical comparative runs</div>
        </div>

        <div className="metric-card">
          <div className="metric-title" style={{ color: '#34d399' }}>Completed Runs</div>
          <div className="metric-value" style={{ color: '#34d399' }}>{metrics.completed_runs}</div>
          <div className="metric-desc">Valid agent responses</div>
        </div>

        <div className="metric-card">
          <div className="metric-title" style={{ color: '#f43f5e' }}>Attacks Blocked (Gate ON)</div>
          <div className="metric-value" style={{ color: '#f43f5e' }}>{metrics.blocked_calls}</div>
          <div className="metric-desc">Intercepted unauthorized calls</div>
        </div>

        <div className="metric-card">
          <div className="metric-title" style={{ color: '#fbbf24' }}>Secret Leaks (Gate OFF)</div>
          <div className="metric-value" style={{ color: '#fbbf24' }}>{metrics.marker_leaked}</div>
          <div className="metric-desc">Exfiltrations when gate disabled</div>
        </div>
      </div>

      {/* Live Comparison Runner Form */}
      <div className="glass-panel" style={{ marginBottom: 28 }}>
        <div className="panel-header">
          <span className="panel-title">
            <Play size={16} color="#10b981" />
            Live Comparison: Gate ON vs Gate OFF
          </span>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Both modes receive identical prompts & document context.
          </span>
        </div>

        <form onSubmit={handleRunComparison} style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 1fr) 2fr auto', gap: 16, alignItems: 'end' }}>
          <div>
            <label className="form-label">Document Target</label>
            <select
              value={docId}
              onChange={(e) => setDocId(e.target.value)}
              className="form-select"
            >
              {(documents || []).map(d => (
                <option key={d.id} value={d.id}>
                  {d.title} ({d.id})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label">Task Prompt</label>
            <input
              type="text"
              value={task}
              onChange={(e) => setTask(e.target.value)}
              className="form-input"
              placeholder="Task for comparison..."
              required
            />
          </div>

          <div>
            <button
              type="submit"
              disabled={isComparing || !task.trim()}
              className="btn-approve"
              style={{ padding: '11px 20px', fontSize: '13px' }}
            >
              {isComparing ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  Comparing...
                </>
              ) : (
                <>
                  <Play size={14} />
                  Run Both Modes
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Live Comparison Result View */}
      {latestComparison && (
        <div style={{ marginBottom: 28 }}>
          <h3 style={{ fontSize: '14px', fontWeight: 800, color: '#ffffff', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <ShieldCheck size={18} color="#10b981" />
            Live Comparison Outcome: {latestComparison.document}
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
            {latestComparison.runs.map((run, i) => {
              const isGateOn = run.mode === 'Gate ON';
              return (
                <div
                  key={i}
                  className="glass-panel"
                  style={{
                    border: isGateOn ? '1.5px solid rgba(16, 185, 129, 0.45)' : '1.5px solid rgba(244, 63, 94, 0.45)',
                    background: isGateOn ? 'rgba(10, 28, 23, 0.85)' : 'rgba(28, 10, 14, 0.85)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                    <span style={{ fontSize: '15px', fontWeight: 800, color: isGateOn ? '#34d399' : '#fb7185' }}>
                      {run.mode} ({isGateOn ? 'Security Protected' : 'Enforcement Bypassed'})
                    </span>
                    <span className={`badge ${isGateOn ? 'badge-completed' : 'badge-error'}`}>
                      {run.status}
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14, fontFamily: 'var(--font-mono)' }}>
                    <div style={{ padding: '10px', borderRadius: '8px', background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border-subtle)' }}>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'block' }}>Unauthorized Executed</span>
                      <span style={{ fontSize: '18px', fontWeight: 800, color: run.unauthorized_actions_executed > 0 ? '#f43f5e' : '#10b981' }}>
                        {run.unauthorized_actions_executed}
                      </span>
                    </div>

                    <div style={{ padding: '10px', borderRadius: '8px', background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border-subtle)' }}>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'block' }}>Attacker Exfiltration</span>
                      <span style={{ fontSize: '18px', fontWeight: 800, color: run.secret_marker_sent_to_attacker ? '#f43f5e' : '#10b981' }}>
                        {run.secret_marker_sent_to_attacker ? 'YES (LEAKED)' : 'NO (PROTECTED)'}
                      </span>
                    </div>
                  </div>

                  <div style={{ fontSize: '12px' }}>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: 6 }}>Audit Trace:</span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {run.audit.map((ev, idx) => (
                        <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', borderRadius: '6px', background: 'rgba(0,0,0,0.3)', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                          <span style={{ color: '#ffffff' }}>{ev.tool} ({ev.arguments?.doc_id || ev.arguments?.recipient})</span>
                          <span className={
                            ev.decision === 'ALLOW' ? 'badge-decision-allow' :
                            ev.decision === 'BLOCK' ? 'badge-decision-block' : 'badge-decision-bypass'
                          }>
                            {ev.decision}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Saved Comparisons Table */}
      <div className="glass-panel">
        <div className="panel-header">
          <span className="panel-title">
            <ShieldCheck size={16} color="#10b981" />
            Saved Evaluation Logs ({filteredRows.length})
          </span>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Filter size={14} color="var(--text-muted)" />
            <select
              value={modeFilter}
              onChange={(e) => setModeFilter(e.target.value)}
              className="form-select"
              style={{ width: '130px', padding: '6px 10px', fontSize: '12px' }}
            >
              <option value="Both">Both Modes</option>
              <option value="Gate ON">Gate ON</option>
              <option value="Gate OFF">Gate OFF</option>
            </select>
          </div>
        </div>

        {filteredRows.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)', fontSize: '12px' }}>
            No evaluation records found. Run a comparison above to generate benchmarks.
          </div>
        ) : (
          <div className="audit-table-wrapper">
            <table className="audit-table">
              <thead>
                <tr>
                  <th>Recorded (UTC)</th>
                  <th>Document</th>
                  <th>Mode</th>
                  <th>Status</th>
                  <th>Unauthorized Executed</th>
                  <th>Blocked Calls</th>
                  <th style={{ textAlign: 'right' }}>Attacker Exfil</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row, idx) => (
                  <tr key={idx}>
                    <td style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                      {row.recorded_at ? new Date(row.recorded_at).toLocaleTimeString() : 'N/A'}
                    </td>
                    <td style={{ fontWeight: 600, color: '#34d399' }}>
                      {row.document}
                    </td>
                    <td>
                      <span className={row.mode === 'Gate ON' ? 'badge-decision-allow' : 'badge-decision-block'}>
                        {row.mode}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>
                      {row.status}
                    </td>
                    <td style={{ fontWeight: 700, color: row.unauthorized_executed > 0 ? '#f43f5e' : '#10b981' }}>
                      {row.unauthorized_executed}
                    </td>
                    <td style={{ color: '#5eead4', fontWeight: 700 }}>
                      {row.blocked_calls}
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>
                      {row.marker_sent_to_attacker ? (
                        <span style={{ color: '#f43f5e' }}>YES</span>
                      ) : (
                        <span style={{ color: '#10b981' }}>NO</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
