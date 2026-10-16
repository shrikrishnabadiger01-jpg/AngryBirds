const API_BASE = '/api';

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const data = await response.json();
      errorDetail = data.detail || JSON.stringify(data);
    } catch (e) {
      // Keep default errorDetail
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export const api = {
  async getAuthSession() {
    const res = await fetch(`${API_BASE}/auth/session`);
    return handleResponse(res);
  },

  async login(username, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    return handleResponse(res);
  },

  async logout() {
    const res = await fetch(`${API_BASE}/auth/logout`, { method: 'POST' });
    return handleResponse(res);
  },

  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse(res);
  },

  async getDocuments() {
    const res = await fetch(`${API_BASE}/workspace/documents`);
    return handleResponse(res);
  },

  async startRun({ task, document_id, allow_email, recipient, allowed_documents, allowed_recipients, max_emails, required_subject }) {
    const res = await fetch(`${API_BASE}/workspace/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task, document_id, allow_email, recipient, allowed_documents, allowed_recipients, max_emails, required_subject }),
    });
    return handleResponse(res);
  },

  async getRunStatus(run_id) {
    const res = await fetch(`${API_BASE}/workspace/run/${run_id}`);
    return handleResponse(res);
  },

  async submitApproval(run_id, token, approved) {
    const res = await fetch(`${API_BASE}/workspace/run/${run_id}/approval`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, approved }),
    });
    return handleResponse(res);
  },

  async cancelRun(run_id) {
    const res = await fetch(`${API_BASE}/workspace/run/${run_id}/cancel`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async getRunsHistory() {
    const res = await fetch(`${API_BASE}/workspace/runs`);
    return handleResponse(res);
  },

  async getAudit({ q = '', source = '', decision = '', page = 1, page_size = 25 } = {}) {
    const params = new URLSearchParams({ page, page_size });
    if (q) params.set('q', q);
    if (source) params.set('source', source);
    if (decision) params.set('decision', decision);
    const res = await fetch(`${API_BASE}/audit?${params}`);
    return handleResponse(res);
  },

  async getEvaluations() {
    const res = await fetch(`${API_BASE}/evaluations`);
    return handleResponse(res);
  },

  async runComparison({ task, document_id, allow_email }) {
    const res = await fetch(`${API_BASE}/evaluations/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task, document_id, allow_email }),
    });
    return handleResponse(res);
  },

  async getScriptedTestCases() {
    const res = await fetch(`${API_BASE}/scripted-tests/cases`);
    return handleResponse(res);
  },

  async runScriptedTests({ policy_doc = 'project_report', allowed_recipient = 'manager@example.com' } = {}) {
    const res = await fetch(`${API_BASE}/scripted-tests/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ policy_doc, allowed_recipient }),
    });
    return handleResponse(res);
  },

  // Gmail OAuth and Email Reading APIs
  async getGmailStatus() {
    const res = await fetch(`${API_BASE}/gmail/status`);
    return handleResponse(res);
  },

  async getGmailAuthUrl() {
    const res = await fetch(`${API_BASE}/gmail/auth`);
    return handleResponse(res);
  },

  async disconnectGmail() {
    const res = await fetch(`${API_BASE}/gmail/disconnect`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async getEmails(max_results = 20) {
    const res = await fetch(`${API_BASE}/emails?max_results=${max_results}`);
    return handleResponse(res);
  },

  async analyzeEmail({ email_id, subject, body, sender, recipient }) {
    const res = await fetch(`${API_BASE}/emails/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email_id, subject, body, sender, recipient }),
    });
    return handleResponse(res);
  },
};
