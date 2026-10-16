import React, { useState, useEffect } from 'react';
import { 
  Mail, Shield, ShieldCheck, ShieldAlert, AlertTriangle, RefreshCw, 
  ExternalLink, LogOut, CheckCircle2, XCircle, Search, Clock, User, ChevronRight
} from 'lucide-react';
import { api } from '../services/api';

export default function GmailInboxTab({
  gmailStatus,
  onConnectGmail,
  onDisconnectGmail,
  onShowSetupModal,
  canOperate = true,
}) {
  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedEmailId, setSelectedEmailId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

  const isConnected = gmailStatus?.connected;
  const userEmail = gmailStatus?.email;

  const loadEmails = async () => {
    if (!isConnected) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getEmails(20);
      setEmails(res.emails || []);
      if (res.emails?.length > 0 && !selectedEmailId) {
        setSelectedEmailId(res.emails[0].id);
      }
    } catch (e) {
      setError(e.message || 'Failed to fetch Gmail inbox messages');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isConnected) {
      loadEmails();
    } else {
      setEmails([]);
      setSelectedEmailId(null);
    }
  }, [isConnected]);

  const selectedEmail = emails.find(e => e.id === selectedEmailId) || emails[0] || null;

  const handleAnalyzeSelected = async () => {
    if (!selectedEmail || analyzing) return;
    setAnalyzing(true);
    try {
      const res = await api.analyzeEmail({
        email_id: selectedEmail.id,
        subject: selectedEmail.subject,
        body: selectedEmail.body || selectedEmail.snippet,
        sender: selectedEmail.sender,
        recipient: selectedEmail.recipient,
      });
      setAnalysisResult(res);
    } catch (e) {
      setError(e.message || 'Failed to analyze email');
    } finally {
      setAnalyzing(false);
    }
  };

  const filteredEmails = emails.filter(e => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (e.subject && e.subject.toLowerCase().includes(q)) ||
      (e.sender && e.sender.toLowerCase().includes(q)) ||
      (e.senderName && e.senderName.toLowerCase().includes(q)) ||
      (e.snippet && e.snippet.toLowerCase().includes(q))
    );
  });

  return (
    <div className="main-content">
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16, marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '26px', fontWeight: 800, color: '#ffffff', display: 'flex', alignItems: 'center', gap: 10 }}>
            <Mail size={26} color="#10b981" />
            Real Gmail Inbox · Read Only
          </h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: 4 }}>
            This tab only reads inbox messages. Agent messages are sent separately through Gmail after you approve the exact proposal.
          </p>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {isConnected ? (
            <>
              <button
                type="button"
                onClick={loadEmails}
                disabled={loading}
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
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                <span>Refresh Inbox</span>
              </button>

              <button
                type="button"
                onClick={onDisconnectGmail}
                disabled={!canOperate}
                className="btn-deny"
                style={{ padding: '8px 14px', fontSize: '12px' }}
              >
                <LogOut size={13} />
                <span>Disconnect</span>
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={onConnectGmail}
              disabled={!canOperate}
              className="btn-approve"
              style={{ padding: '9px 18px', fontSize: '13px' }}
            >
              <Mail size={15} />
              <span>Connect Gmail (OAuth)</span>
            </button>
          )}
        </div>
      </div>

      {/* Untrusted Data Guardrail Banner */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 12,
        padding: '14px 18px',
        borderRadius: '12px',
        background: 'rgba(16, 185, 129, 0.08)',
        border: '1px solid rgba(16, 185, 129, 0.22)',
        marginBottom: 24,
      }}>
        <Shield size={20} color="#10b981" style={{ flexShrink: 0, marginTop: 2 }} />
        <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          <strong style={{ color: '#ffffff' }}>Strict Runtime Security Policy: </strong>
          All incoming emails are classified as <code>untrusted_external_content</code>. Embedded requests to send messages, read documents, or bypass policies are intercepted by the runtime gate. No emails can execute system commands or modify mailbox records.
        </div>
      </div>

      {/* Connection State Handling */}
      {!isConnected ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '60px 24px' }}>
          <div style={{
            width: 64,
            height: 64,
            borderRadius: '16px',
            background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 18px auto',
            color: '#10b981',
          }}>
            <Mail size={32} />
          </div>

          <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#ffffff' }}>
            Gmail Is Currently Disconnected
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '480px', margin: '8px auto 24px auto', lineHeight: 1.5 }}>
            Connect your Google account to inspect inbox messages with read-only permissions.
          </p>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
            <button
              type="button"
              onClick={onConnectGmail}
              disabled={!canOperate}
              className="btn-approve"
              style={{ padding: '11px 24px', fontSize: '13px' }}
            >
              <Mail size={16} />
              <span>Connect with Google</span>
            </button>
            <button
              type="button"
              onClick={onShowSetupModal}
              style={{
                padding: '11px 18px',
                borderRadius: '8px',
                background: 'rgba(6, 18, 14, 0.8)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                fontSize: '13px',
                cursor: 'pointer',
              }}
            >
              Setup Guide (.env)
            </button>
          </div>
        </div>
      ) : (
        /* Connected View: Two-Column Mailbox & Analysis Console */
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 420px) 1fr', gap: '24px', alignItems: 'start' }}>
          {/* Left Column: Email List */}
          <div className="panel-stack">
            {/* Search Box */}
            <div className="glass-panel" style={{ padding: '16px' }}>
              <div style={{ position: 'relative' }}>
                <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: 12 }} />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search real emails..."
                  className="form-input"
                  style={{ paddingLeft: 34, fontSize: '12px' }}
                />
              </div>
            </div>

            {/* Email Stream Card */}
            <div className="glass-panel" style={{ padding: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Inbox Messages ({filteredEmails.length})
                </span>
                <span style={{ fontSize: '11px', color: '#34d399', fontFamily: 'var(--font-mono)' }}>
                  {userEmail}
                </span>
              </div>

              {loading ? (
                <div style={{ textAlign: 'center', padding: '36px', color: '#34d399', fontSize: '13px' }}>
                  <RefreshCw size={18} className="animate-spin" style={{ margin: '0 auto 8px auto' }} />
                  Loading real emails from Gmail API...
                </div>
              ) : error ? (
                <div style={{ padding: '14px', borderRadius: '8px', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.35)', color: '#fb7185', fontSize: '12px' }}>
                  <strong>Error: </strong> {error}
                </div>
              ) : filteredEmails.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)', fontSize: '12.5px' }}>
                  No messages found in your Gmail inbox.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: '680px', overflowY: 'auto' }}>
                  {filteredEmails.map((email) => {
                    const isSelected = selectedEmail?.id === email.id;
                    return (
                      <div
                        key={email.id}
                        onClick={() => {
                          setSelectedEmailId(email.id);
                          setAnalysisResult(null);
                        }}
                        style={{
                          padding: '12px 14px',
                          borderRadius: '10px',
                          background: isSelected ? 'rgba(16, 185, 129, 0.12)' : 'rgba(4, 12, 10, 0.65)',
                          border: isSelected ? '1.5px solid var(--accent-emerald)' : '1px solid var(--border-subtle)',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                          <span style={{ fontSize: '12.5px', fontWeight: 700, color: '#ffffff' }}>
                            {email.senderName || email.sender}
                          </span>
                          <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                            {email.date ? new Date(email.date).toLocaleDateString() : ''}
                          </span>
                        </div>

                        <div style={{ fontSize: '12px', fontWeight: 600, color: isSelected ? '#34d399' : '#e2e8f0', marginBottom: 4 }}>
                          {email.subject || '(No Subject)'}
                        </div>

                        <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                          {email.snippet}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Selected Email Details & Security Analysis */}
          <div className="panel-stack">
            {selectedEmail ? (
              <>
                {/* Email Viewer Card */}
                <div className="glass-panel">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16, paddingBottom: 14, borderBottom: '1px solid var(--border-subtle)' }}>
                    <div>
                      <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#ffffff', marginBottom: 6 }}>
                        {selectedEmail.subject || '(No Subject)'}
                      </h2>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', flexWrap: 'wrap', gap: 12 }}>
                        <div><strong style={{ color: '#ffffff' }}>From: </strong>{selectedEmail.sender}</div>
                        {selectedEmail.recipient && <div><strong style={{ color: '#ffffff' }}>To: </strong>{selectedEmail.recipient}</div>}
                      </div>
                    </div>

                    {/* Action Button: Analyze Email */}
                    <button
                      type="button"
                      onClick={handleAnalyzeSelected}
                      disabled={analyzing}
                      className="btn-approve"
                      style={{ padding: '10px 18px', fontSize: '12.5px', flexShrink: 0 }}
                    >
                      {analyzing ? (
                        <>
                          <RefreshCw size={14} className="animate-spin" />
                          <span>Scanning Email...</span>
                        </>
                      ) : (
                        <>
                          <ShieldCheck size={15} />
                          <span>Analyze Email</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Body Content */}
                  <div style={{
                    background: '#020605',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '16px',
                    fontSize: '12.5px',
                    lineHeight: 1.6,
                    color: '#e2e8f0',
                    whiteSpace: 'pre-wrap',
                    fontFamily: 'var(--font-sans)',
                    maxHeight: '400px',
                    overflowY: 'auto',
                  }}>
                    {selectedEmail.body || selectedEmail.snippet || '(No body content)'}
                  </div>
                </div>

                {/* Real-time Security Analysis Card */}
                {analysisResult && (
                  <div className="glass-panel-elevated" style={{
                    border: analysisResult.decision === 'ALLOW' ? '1.5px solid rgba(16, 185, 129, 0.4)' : '1.5px solid rgba(244, 63, 94, 0.4)',
                    background: analysisResult.decision === 'ALLOW' ? 'rgba(10, 28, 23, 0.95)' : 'rgba(28, 10, 14, 0.95)',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <ShieldCheck size={20} color={analysisResult.decision === 'ALLOW' ? '#10b981' : '#f43f5e'} />
                        <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#ffffff', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                          Security Gate Inspection Report
                        </h3>
                      </div>
                      <span className={
                        analysisResult.decision === 'ALLOW' ? 'badge badge-completed' :
                        analysisResult.decision === 'SUSPICIOUS' ? 'badge badge-awaiting' : 'badge badge-error'
                      }>
                        {analysisResult.decision} · {analysisResult.threat_level?.toUpperCase()}
                      </span>
                    </div>

                    <p style={{ fontSize: '13px', color: '#ffffff', marginBottom: 14, lineHeight: 1.4 }}>
                      {analysisResult.reason}
                    </p>

                    {/* Indicators list */}
                    {analysisResult.indicators && analysisResult.indicators.length > 0 && (
                      <div style={{ marginBottom: 14 }}>
                        <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>
                          Detected Indicators:
                        </span>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {analysisResult.indicators.map((ind, i) => (
                            <div key={i} style={{ padding: '8px 12px', borderRadius: '6px', background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border-subtle)', fontSize: '11.5px', color: '#fbbf24' }}>
                              <strong>{ind.type}: </strong> {ind.description}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: 10 }}>
                      Logged into SQLite Security Audit Table at {new Date(analysisResult.scanned_at).toLocaleTimeString()}.
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="glass-panel" style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-muted)' }}>
                Select a message on the left to inspect and run security analysis.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
