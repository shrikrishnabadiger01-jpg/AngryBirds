import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import WorkspaceTab from './components/WorkspaceTab';
import EvaluationsTab from './components/EvaluationsTab';
import ScriptedTestsTab from './components/ScriptedTestsTab';
import GmailInboxTab from './components/GmailInboxTab';
import GmailSetupModal from './components/GmailSetupModal';
import AuditTab from './components/AuditTab';
import { api } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('workspace');
  const [health, setHealth] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [evaluations, setEvaluations] = useState(null);
  const [gmailStatus, setGmailStatus] = useState({ connected: false, email: null, configured: false });
  const [currentRun, setCurrentRun] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isComparing, setIsComparing] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [errorToast, setErrorToast] = useState(null);
  const [successToast, setSuccessToast] = useState(null);
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [authState, setAuthState] = useState({ required: false, user: null });
  const [authLoading, setAuthLoading] = useState(true);
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');

  const showError = (msg) => {
    setErrorToast(msg);
    setTimeout(() => setErrorToast(null), 5000);
  };

  const showSuccess = (msg) => {
    setSuccessToast(msg);
    setTimeout(() => setSuccessToast(null), 5000);
  };

  const loadInitialData = async () => {
    try {
      const [h, docs, evals, gStatus] = await Promise.all([
        api.getHealth().catch(() => ({ status: 'error', minimoth_api_key_configured: false, gemini_api_key_configured: false })),
        api.getDocuments().catch(() => []),
        api.getEvaluations().catch(() => null),
        api.getGmailStatus().catch(() => ({ connected: false, email: null, configured: false })),
      ]);
      setHealth(h);
      setDocuments(docs);
      setEvaluations(evals);
      setGmailStatus(gStatus);
    } catch (e) {
      console.error('Failed to load initial data:', e);
    }
  };

  // Load the auth session before requesting protected application data.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const gmailParam = params.get('gmail');
    const emailParam = params.get('email');
    const reasonParam = params.get('reason');

    if (gmailParam === 'connected') {
      showSuccess(`Gmail connected successfully! Authorized as: ${emailParam || 'authenticated user'}`);
      setActiveTab('gmail');
      // Clean query parameters from URL
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (gmailParam === 'error') {
      showError(`Google OAuth failed: ${reasonParam || 'Authentication was cancelled'}`);
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    api.getAuthSession().then((session) => {
      setAuthState(session);
      if (!session.required || session.user) loadInitialData();
    }).catch((error) => setLoginError(error.message || 'Could not check sign-in status'))
      .finally(() => setAuthLoading(false));
  }, []);

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoginError('');
    try {
      const user = await api.login(loginUsername, loginPassword);
      setAuthState({ required: true, user });
      setLoginPassword('');
      await loadInitialData();
    } catch (error) {
      setLoginError(error.message || 'Sign-in failed');
    }
  };

  const handleLogout = async () => {
    await api.logout().catch(() => {});
    setAuthState({ ...authState, user: null });
    setGmailStatus({ connected: false, email: null, configured: false });
    setCurrentRun(null);
  };

  const handleConnectGmail = async () => {
    try {
      const res = await api.getGmailAuthUrl();
      if (res?.auth_url) {
        window.location.href = res.auth_url;
      }
    } catch (e) {
      // If server returns credentials not configured, open the setup guide modal
      if (e.message?.includes('not configured')) {
        setShowSetupModal(true);
      } else {
        showError(e.message || 'Failed to start Google OAuth');
      }
    }
  };

  const handleDisconnectGmail = async () => {
    try {
      await api.disconnectGmail();
      const updatedStatus = await api.getGmailStatus();
      setGmailStatus(updatedStatus);
      showSuccess('Gmail account disconnected successfully.');
      setActiveTab('workspace');
    } catch (e) {
      showError(e.message || 'Failed to disconnect Gmail');
    }
  };

  const handleStartRun = async (runSettings) => {
    setIsRunning(true);
    try {
      const run = await api.startRun(runSettings);
      setCurrentRun(run);
      api.getEvaluations().then(setEvaluations).catch(() => {});
    } catch (e) {
      showError(e.message || 'Failed to start agent run');
    } finally {
      setIsRunning(false);
    }
  };

  const handleApproveProposal = async (run_id, token, approved) => {
    setIsRunning(true);
    try {
      const updatedRun = await api.submitApproval(run_id, token, approved);
      setCurrentRun(updatedRun);
      api.getEvaluations().then(setEvaluations).catch(() => {});
    } catch (e) {
      showError(e.message || 'Failed to submit approval');
    } finally {
      setIsRunning(false);
    }
  };

  const handleCancelRun = async (run_id) => {
    try {
      const updated = await api.cancelRun(run_id);
      setCurrentRun(updated);
    } catch (e) {
      showError(e.message || 'Failed to cancel run');
    }
  };

  const handleRunComparison = async ({ task, document_id, allow_email }) => {
    setIsComparing(true);
    try {
      const result = await api.runComparison({ task, document_id, allow_email });
      const refreshedEvals = await api.getEvaluations();
      setEvaluations(refreshedEvals);
      return result;
    } catch (e) {
      showError(e.message || 'Failed to execute gate comparison');
      return null;
    } finally {
      setIsComparing(false);
    }
  };

  const handleRunScriptedTests = async () => {
    setIsTesting(true);
    try {
      const results = await api.runScriptedTests();
      return results;
    } catch (e) {
      showError(e.message || 'Failed to run scripted tests');
      return null;
    } finally {
      setIsTesting(false);
    }
  };

  return (
    authLoading ? (
      <main className="main-content"><div className="glass-panel">Checking sign-in status…</div></main>
    ) : authState.required && !authState.user ? (
      <main className="main-content" style={{ maxWidth: 480, margin: '12vh auto' }}>
        <form className="glass-panel" onSubmit={handleLogin}>
          <h1 style={{ color: '#fff', fontSize: 22, marginBottom: 8 }}>Sign in</h1>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 20 }}>Use your organization account to access the security workspace.</p>
          <label className="form-group"><span className="form-label">Username</span><input autoComplete="username" className="form-input" value={loginUsername} onChange={event => setLoginUsername(event.target.value)} required /></label>
          <label className="form-group"><span className="form-label">Password</span><input autoComplete="current-password" type="password" className="form-input" value={loginPassword} onChange={event => setLoginPassword(event.target.value)} required /></label>
          {loginError && <p role="alert" style={{ color: '#fb7185', marginBottom: 12 }}>{loginError}</p>}
          <button type="submit" className="btn-approve">Sign in</button>
        </form>
      </main>
    ) : (
    <div className="app-shell">
      {/* Toast Notifications */}
      {errorToast && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 9999,
          padding: '14px 18px',
          borderRadius: '12px',
          background: 'rgba(28, 10, 14, 0.95)',
          border: '1px solid rgba(244, 63, 94, 0.45)',
          color: '#fb7185',
          fontSize: '13px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          backdropFilter: 'blur(12px)',
        }}>
          <span>{errorToast}</span>
          <button
            onClick={() => setErrorToast(null)}
            style={{
              background: 'none',
              border: 'none',
              color: '#fb7185',
              fontWeight: 700,
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            ✕
          </button>
        </div>
      )}

      {successToast && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 9999,
          padding: '14px 18px',
          borderRadius: '12px',
          background: 'rgba(10, 28, 23, 0.95)',
          border: '1px solid rgba(16, 185, 129, 0.45)',
          color: '#34d399',
          fontSize: '13px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          backdropFilter: 'blur(12px)',
        }}>
          <span>{successToast}</span>
          <button
            onClick={() => setSuccessToast(null)}
            style={{
              background: 'none',
              border: 'none',
              color: '#34d399',
              fontWeight: 700,
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Top Header */}
      <Header
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        health={health}
        gmailStatus={gmailStatus}
        onConnectGmail={handleConnectGmail}
        authUser={authState.user}
        onLogout={handleLogout}
        canOperate={['admin', 'operator'].includes(authState.user?.role)}
      />

      {/* Main Content Areas */}
      <main style={{ flex: 1 }}>
        {activeTab === 'workspace' && (
          <WorkspaceTab
            documents={documents}
            currentRun={currentRun}
            isRunning={isRunning}
            onStartRun={handleStartRun}
            onApproveProposal={handleApproveProposal}
            onCancelRun={handleCancelRun}
            canOperate={['admin', 'operator'].includes(authState.user?.role)}
          />
        )}

        {activeTab === 'evaluations' && (
          <EvaluationsTab
            evaluations={evaluations}
            documents={documents}
            isComparing={isComparing}
            canOperate={['admin', 'operator'].includes(authState.user?.role)}
            onRunComparison={handleRunComparison}
            onRefresh={() => api.getEvaluations().then(setEvaluations)}
          />
        )}

        {activeTab === 'scripted' && (
          <ScriptedTestsTab
            onRunScriptedTests={handleRunScriptedTests}
            isRunning={isTesting}
            canOperate={['admin', 'operator'].includes(authState.user?.role)}
          />
        )}

        {activeTab === 'audit' && <AuditTab />}

        {activeTab === 'gmail' && (
          <GmailInboxTab
            gmailStatus={gmailStatus}
            onConnectGmail={handleConnectGmail}
            onDisconnectGmail={handleDisconnectGmail}
            onShowSetupModal={() => setShowSetupModal(true)}
            canOperate={['admin', 'operator'].includes(authState.user?.role)}
          />
        )}
      </main>

      {/* Google Cloud Setup Guide Modal */}
      <GmailSetupModal
        isOpen={showSetupModal}
        onClose={() => setShowSetupModal(false)}
      />

      {/* Footer */}
      <footer className="app-footer">
        <p>AI Agent Security (Genesis 2.0) · Team Angry Birds · React + FastAPI Architecture with Gmail OAuth</p>
      </footer>
    </div>
    )
  );
}
