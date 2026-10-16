import React from 'react';
import { Shield, Cpu, Activity, Layers, Mail, FileSearch } from 'lucide-react';

export default function Header({
  activeTab,
  onSelectTab,
  health,
  gmailStatus,
  onConnectGmail,
  authUser,
  onLogout,
  canOperate = true,
}) {
  const isHealthy = health?.status === 'healthy';
  const isMiniMothLive = Boolean(health?.minimoth_api_key_configured || health?.gemini_api_key_configured);
  const isGmailConnected = gmailStatus?.connected;
  const gmailEmail = gmailStatus?.email;

  const handleGmailButtonClick = () => {
    if (isGmailConnected) {
      // When connected, open the Gmail Inbox tab
      onSelectTab('gmail');
    } else {
      // When disconnected, start OAuth flow
      onConnectGmail();
    }
  };

  return (
    <header className="app-header">
      <div className="header-container">
        {/* Brand Section */}
        <div className="brand-section">
          <div className="brand-logo">
            <Shield size={22} />
          </div>
          <div>
            <div className="brand-text-title">
              <span>AI AGENT SECURITY</span>
              <span className="brand-tag">GENESIS 2.0</span>
            </div>
            <div className="brand-subtitle">
              Team Angry Birds · Runtime Permission Gate
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="nav-tab-list">
          <button
            type="button"
            onClick={() => onSelectTab('workspace')}
            className={`nav-tab-btn ${activeTab === 'workspace' ? 'active' : ''}`}
          >
            <Cpu size={15} />
            <span>Workspace</span>
          </button>
          <button
            type="button"
            onClick={() => onSelectTab('evaluations')}
            className={`nav-tab-btn ${activeTab === 'evaluations' ? 'active' : ''}`}
          >
            <Activity size={15} />
            <span>Evaluations</span>
          </button>
          <button
            type="button"
            onClick={() => onSelectTab('scripted')}
            className={`nav-tab-btn ${activeTab === 'scripted' ? 'active' : ''}`}
          >
            <Layers size={15} />
            <span>Scripted Gate Tests</span>
          </button>

          <button
            type="button"
            onClick={() => onSelectTab('audit')}
            className={`nav-tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
          >
            <FileSearch size={15} />
            <span>Audit History</span>
          </button>
          <button
            id="nav-tab-gmail"
            type="button"
            onClick={() => onSelectTab('gmail')}
            className={`nav-tab-btn ${activeTab === 'gmail' ? 'active' : ''}`}
          >
            <Mail size={15} />
            <span>Gmail Inbox</span>
            {isGmailConnected && (
              <span style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: '#10b981',
                boxShadow: '0 0 6px #10b981',
              }} />
            )}
          </button>
        </nav>

        {/* Right Section: Gmail Integration Button & Backend Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Gmail Integration Button */}
          <button
            id="gmail-integration-btn"
            type="button"
            onClick={handleGmailButtonClick}
            disabled={!isGmailConnected && !canOperate}
            title={isGmailConnected ? `Connected as ${gmailEmail}. Click to view inbox.` : 'Click to connect Google OAuth'}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '7px 14px',
              borderRadius: '10px',
              background: isGmailConnected ? 'rgba(16, 185, 129, 0.12)' : 'rgba(6, 18, 14, 0.9)',
              border: isGmailConnected ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid var(--border-subtle)',
              color: isGmailConnected ? '#34d399' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 600,
              transition: 'all 0.2s ease',
            }}
          >
            <Mail size={15} color={isGmailConnected ? '#10b981' : '#94a3b8'} />
            <span>
              {isGmailConnected ? (gmailEmail ? `Gmail: ${gmailEmail}` : 'Gmail Connected') : 'Gmail Disconnected'}
            </span>
            <span style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: isGmailConnected ? '#10b981' : '#f59e0b',
              boxShadow: isGmailConnected ? '0 0 8px #10b981' : 'none',
            }} />
          </button>

          {/* Backend Status indicator */}
          <div className="status-pill">
            <span className={`status-dot ${isHealthy ? '' : 'error'}`} />
            <span>
              {isMiniMothLive ? 'MiniMoth Live' : 'High-Fidelity Simulator'}
            </span>
          </div>
          {authUser && (
            <button type="button" onClick={onLogout} className="nav-tab-btn" title={`Sign out ${authUser.username}`}>
              <span>{authUser.username} · {authUser.role}</span>
              <span>Sign out</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
