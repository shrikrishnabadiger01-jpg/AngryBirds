import React, { useState } from 'react';
import { Layers, Play, CheckCircle2, Shield, RefreshCw } from 'lucide-react';

export default function ScriptedTestsTab({ onRunScriptedTests, isRunning, canOperate = true }) {
  const [resultsData, setResultsData] = useState(null);

  const handleRun = async () => {
    const data = await onRunScriptedTests();
    if (data) {
      setResultsData(data);
    }
  };

  return (
    <div className="main-content">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16, marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '26px', fontWeight: 800, color: '#ffffff', display: 'flex', alignItems: 'center', gap: 10 }}>
            <Layers size={26} color="#10b981" />
            Deterministic security-gate checks
          </h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: 4 }}>
            Deterministic benchmark suite executing authorized and prohibited tool calls with enforcement ON vs OFF.
          </p>
        </div>

        <button
          type="button"
          onClick={handleRun}
            disabled={!canOperate || isRunning}
          className="btn-approve"
          style={{ padding: '10px 20px', fontSize: '13px' }}
        >
          {isRunning ? (
            <>
              <RefreshCw size={14} className="animate-spin" />
              <span>Executing Tests...</span>
            </>
          ) : (
            <>
              <Play size={14} />
              <span>Run Scripted Tests</span>
            </>
          )}
        </button>
      </div>

      {/* Info Notice */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 12,
        padding: '14px 18px',
        borderRadius: '12px',
        background: 'rgba(16, 185, 129, 0.1)',
        border: '1px solid rgba(16, 185, 129, 0.25)',
        marginBottom: 24,
      }}>
        <Shield size={20} color="#10b981" style={{ flexShrink: 0, marginTop: 2 }} />
        <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          <strong style={{ color: '#ffffff' }}>Zero External Model Dependency: </strong>
          These benchmark calls are scripted and verify the low-level TaskPolicy gate mechanism in the simulated workspace. No API requests, model credits, or real emails are utilized.
        </div>
      </div>

      {/* Results Overview */}
      {resultsData && (
        <div className="glass-panel" style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, paddingBottom: 16, borderBottom: '1px solid var(--border-subtle)', marginBottom: 20 }}>
            <div>
              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Benchmark Verification Status
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '24px', fontWeight: 800, color: '#34d399' }}>
                  {resultsData.passed_cases} / {resultsData.total_cases} Passed
                </span>
                <span className="badge badge-completed">
                  {resultsData.passed_cases === resultsData.total_cases ? 'All checks passed' : 'Some checks failed'}
                </span>
              </div>
            </div>

          </div>

          {/* Test Cases List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {resultsData.results.map((res, i) => (
              <div
                key={i}
                style={{
                  background: 'rgba(4, 12, 10, 0.65)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '12px',
                  padding: '16px 18px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{
                      width: 24,
                      height: 24,
                      borderRadius: '50%',
                      background: 'rgba(16, 185, 129, 0.15)',
                      color: '#34d399',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                    }}>
                      {i + 1}
                    </span>
                    <span style={{ fontSize: '14px', fontWeight: 700, color: '#ffffff' }}>
                      {res.label}
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                      ({res.tool})
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Expected:</span>
                    <span className={res.expected_authorized ? 'badge-decision-allow' : 'badge-decision-block'}>
                      {res.expected_authorized ? 'AUTHORIZED' : 'PROHIBITED'}
                    </span>
                    <span style={{ fontSize: '12px', color: res.passed_enforcement ? '#34d399' : '#f43f5e', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 4 }}>
                      <CheckCircle2 size={15} /> {res.passed_enforcement ? 'Passed' : 'Failed'}
                    </span>
                  </div>
                </div>

                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: 12 }}>
                  {res.description}
                </p>

                {/* Gate ON vs OFF execution comparisons */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 12 }}>
                  {/* Gate ON */}
                  <div style={{
                    padding: '12px 14px',
                    borderRadius: '8px',
                    background: 'rgba(6, 20, 16, 0.8)',
                    border: '1px solid rgba(16, 185, 129, 0.25)',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: '11px', fontWeight: 800, color: '#34d399' }}>GATE ON (PROTECTED)</span>
                      <span className={res.gate_on.decision === 'ALLOW' ? 'badge-decision-allow' : 'badge-decision-block'}>
                        {res.gate_on.decision}
                      </span>
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                      Reason: {res.gate_on.reason}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: 4, fontFamily: 'var(--font-mono)' }}>
                      Executed: <strong style={{ color: res.gate_on.executed ? '#10b981' : '#f43f5e' }}>{res.gate_on.executed ? 'TRUE' : 'FALSE'}</strong>
                    </div>
                  </div>

                  {/* Gate OFF */}
                  <div style={{
                    padding: '12px 14px',
                    borderRadius: '8px',
                    background: 'rgba(24, 8, 12, 0.7)',
                    border: '1px solid rgba(244, 63, 94, 0.25)',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: '11px', fontWeight: 800, color: '#fb7185' }}>GATE OFF (BYPASSED)</span>
                      <span className="badge-decision-bypass">
                        {res.gate_off.decision}
                      </span>
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                      Reason: {res.gate_off.reason}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: 4, fontFamily: 'var(--font-mono)' }}>
                      Executed: <strong style={{ color: '#fbbf24' }}>TRUE (UNCHECKED)</strong>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
