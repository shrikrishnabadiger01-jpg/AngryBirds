import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import WorkspaceTab from './components/WorkspaceTab';
import EvaluationsTab from './components/EvaluationsTab';
import ScriptedTestsTab from './components/ScriptedTestsTab';
import GmailInboxTab from './components/GmailInboxTab';
import GmailSetupModal from './components/GmailSetupModal';
import AuditTab from './components/AuditTab';
import HomeTab from './components/HomeTab';
import DataSourcesTab from './components/DataSourcesTab';
import SecurityCenterTab from './components/SecurityCenterTab';
import AuthPage from './components/AuthPage';
import { api } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [health, setHealth] = useState(null);
  const [initialDataLoaded, setInitialDataLoaded] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [evaluations, setEvaluations] = useState(null);
  const [runs, setRuns] = useState([]);
  const [auditRecords, setAuditRecords] = useState([]);
  const [focusDocumentId, setFocusDocumentId] = useState(null);
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
  const canOperate = !authState.required || ['admin', 'operator'].includes(authState.user?.role);

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
      const [h, docs, evals, gStatus, runHistory, audit] = await Promise.all([
        api.getHealth().catch(() => ({ status: 'error', gemini_api_key_configured: false })),
        api.getDocuments().catch(() => []),
        api.getEvaluations().catch(() => null),
        api.getGmailStatus().catch(() => ({ connected: false, email: null, configured: false })),
        api.getRunsHistory().catch(() => []),
        api.getAudit({ page_size: 100 }).catch(() => ({ items: [] })),
      ]);
      setHealth(h);
      setDocuments(docs);
      setEvaluations(evals);
      setGmailStatus(gStatus);
      setRuns(runHistory);
      setAuditRecords(audit.items || []);
      setInitialDataLoaded(true);
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
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (gmailParam === 'error') {
      showError(`Google OAuth failed: ${reasonParam || 'Authentication was cancelled'}`);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    api.getAuthSession().then((session) => {
      setAuthState(session);
      if (!session.required || session.user) loadInitialData();
    }).catch(() => setAuthState({ required: true, method: 'otp', user: null }))
      .finally(() => setAuthLoading(false));
  }, []);

  const handleAuthenticated = async (user) => {
    setAuthState({ required: true, method: authState.method || 'otp', user });
    await loadInitialData();
  };

  const handleLogout = async () => {
    await api.logout().catch(() => {});
    setAuthState({ required: true, method: authState.method || 'otp', user: null });
    setGmailStatus({ connected: false, email: null, configured: false });
    setCurrentRun(null);
  };

  const handleConnectGmail = async () => {
    try {
      const res = await api.getGmailAuthUrl();
      if (res?.auth_url) window.location.href = res.auth_url;
    } catch (e) {
      if (e.message?.includes('not configured')) setShowSetupModal(true);
      else showError(e.message || 'Failed to start Google OAuth');
    }
  };

  const handleDisconnectGmail = async () => {
    try {
      await api.disconnectGmail();
      setGmailStatus(await api.getGmailStatus());
      showSuccess('Gmail account disconnected successfully.');
    } catch (e) {
      showError(e.message || 'Failed to disconnect Gmail');
    }
  };

  const handleStartRun = async (runSettings) => {
    setCurrentRun(null);
    setIsRunning(true);
    try {
      const run = await api.startRun(runSettings);
      setCurrentRun(run);
      api.getEvaluations().then(setEvaluations).catch(() => {});
      api.getRunsHistory().then(setRuns).catch(() => {});
      api.getAudit({ page_size: 100 }).then(result => setAuditRecords(result.items || [])).catch(() => {});
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
      api.getRunsHistory().then(setRuns).catch(() => {});
      api.getAudit({ page_size: 100 }).then(result => setAuditRecords(result.items || [])).catch(() => {});
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
      <AuthPage method={authState.method} onAuthenticated={handleAuthenticated} />
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
        authUser={authState.user}
        onLogout={handleLogout}
        onOpenGmail={() => setActiveTab('gmail')}
      />

      {/* Main Content Areas */}
      <main className="app-main">
        {activeTab === 'home' && <HomeTab loading={!initialDataLoaded} health={health} runs={runs} records={auditRecords} gmailStatus={gmailStatus} documents={documents} onNavigate={setActiveTab} />}
        {activeTab === 'sources' && <DataSourcesTab documents={documents} gmailStatus={gmailStatus} canOperate={canOperate} onConnectGmail={handleConnectGmail} onDisconnectGmail={handleDisconnectGmail} onOpenInbox={() => setActiveTab('gmail')} onUseDocument={id => { setFocusDocumentId(id); setActiveTab('workspace'); }} />}
        {activeTab === 'security' && <SecurityCenterTab onOpenTests={() => setActiveTab('scripted')} />}
        {activeTab === 'workspace' && (
          <WorkspaceTab
            documents={documents}
            currentRun={currentRun}
            isRunning={isRunning}
            onStartRun={handleStartRun}
            onApproveProposal={handleApproveProposal}
            onCancelRun={handleCancelRun}
            canOperate={canOperate}
            gmailStatus={gmailStatus}
            modelReady={Boolean(health?.gemini_api_key_configured)}
            onConnectGmail={handleConnectGmail}
            onDisconnectGmail={handleDisconnectGmail}
            focusDocumentId={focusDocumentId}
          />
        )}

        {activeTab === 'evaluations' && (
          <EvaluationsTab
            evaluations={evaluations}
            documents={documents}
            isComparing={isComparing}
            canOperate={canOperate}
            onRunComparison={handleRunComparison}
            onRefresh={() => api.getEvaluations().then(setEvaluations)}
          />
        )}

        {activeTab === 'scripted' && (
          <ScriptedTestsTab
            onRunScriptedTests={handleRunScriptedTests}
            isRunning={isTesting}
            canOperate={canOperate}
          />
        )}

        {activeTab === 'audit' && <AuditTab />}

        {activeTab === 'gmail' && (
          <GmailInboxTab
            gmailStatus={gmailStatus}
            onConnectGmail={handleConnectGmail}
            onDisconnectGmail={handleDisconnectGmail}
            onShowSetupModal={() => setShowSetupModal(true)}
            canOperate={canOperate}
          />
        )}

      </main>

      <GmailSetupModal isOpen={showSetupModal} onClose={() => setShowSetupModal(false)} />

      {/* Footer */}
      <footer className="app-footer">
        <p>IgnisGuard · Securing AI agents against indirect prompt injection</p>
      </footer>
    </div>
    )
  );
}
