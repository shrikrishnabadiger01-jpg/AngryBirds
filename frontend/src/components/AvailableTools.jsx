import React from 'react';
import { CalendarDays, FileText, Globe2, Mail, MessagesSquare } from 'lucide-react';

function Toggle({ checked, disabled = false, label, onChange }) {
  return <button type="button" role="switch" aria-checked={checked} aria-label={label} disabled={disabled} onClick={() => onChange(!checked)} className={`tool-toggle ${checked ? 'checked' : ''}`}><span/></button>;
}

function GmailMark() {
  return <svg className="gmail-mark" viewBox="0 0 24 20" aria-hidden="true"><path fill="#4285f4" d="M2 5.1v12.1c0 .9.7 1.6 1.6 1.6H6V8.1z"/><path fill="#34a853" d="M18 18.8h2.4c.9 0 1.6-.7 1.6-1.6V5.1L18 8.1z"/><path fill="#fbbc04" d="M18 8.1l4-3V3.6c0-1.3-1.5-2-2.5-1.2L18 3.5z"/><path fill="#ea4335" d="M2 5.1l10 7.5 10-7.5V3.6c0-1.3-1.5-2-2.5-1.2L12 8.1 4.5 2.4C3.5 1.6 2 2.3 2 3.6z"/><path fill="#c5221f" d="M2 5.1l4 3V3.5l-1.5-1.1C3.5 1.6 2 2.3 2 3.6z"/></svg>;
}

export default function AvailableTools({ documents = [], documentsEnabled, onDocumentsEnabledChange, gmailStatus, canOperate = true, onConnectGmail, onDisconnectGmail }) {
  const connected = Boolean(gmailStatus?.connected);
  const setGmail = enabled => {
    if (!canOperate) return;
    if (enabled) onConnectGmail?.();
    else if (window.confirm('Disconnect Gmail? This removes the saved Gmail connection and its permissions.')) onDisconnectGmail?.();
  };
  const tools = [
    { name: 'Gmail', detail: 'Read inbox (read-only)', status: connected ? 'Connected' : 'Not connected', connected, icon: <GmailMark/>, iconClass: 'gmail-tool-icon', enabled: connected, action: setGmail, disabled: !canOperate },
    { name: 'Documents', detail: 'Read local files (PDF, TXT)', status: documents.length ? (documentsEnabled ? 'Connected' : 'Paused') : 'Not connected', connected: documents.length > 0, icon: <FileText size={19}/>, iconClass: 'documents-tool-icon', enabled: documentsEnabled, action: onDocumentsEnabledChange, disabled: documents.length === 0 },
    { name: 'Web Search', detail: 'Search the web for information', status: 'Not connected', connected: false, icon: <Globe2 size={20}/>, iconClass: 'web-tool-icon', enabled: false, action: () => {}, disabled: true },
    { name: 'Messages (Slack)', detail: 'Read channel messages', status: 'Not connected', connected: false, icon: <MessagesSquare size={19}/>, iconClass: 'slack-tool-icon', enabled: false, action: () => {}, disabled: true },
    { name: 'Calendar', detail: 'Read calendar events', status: 'Not connected', connected: false, icon: <CalendarDays size={19}/>, iconClass: 'calendar-tool-icon', enabled: false, action: () => {}, disabled: true },
  ];

  return <section className="surface-card available-tools-card"><div className="available-tools-heading"><h2>Available Tools</h2><p>Select the data sources and actions the agent can use.</p></div><div className="available-tools-list">{tools.map(tool => <article className="available-tool-row" key={tool.name}><span className={`available-tool-icon ${tool.iconClass}`}>{tool.icon}</span><div className="available-tool-copy"><strong>{tool.name}</strong><small>{tool.detail}</small><span className={`tool-connection ${tool.connected && tool.enabled ? 'connected' : 'disconnected'}`}><i/>{tool.connected && !tool.enabled ? 'Paused' : tool.status}</span></div><Toggle checked={tool.enabled} disabled={tool.disabled} label={`${tool.name} ${tool.enabled ? 'enabled' : 'disabled'}`} onChange={tool.action}/></article>)}</div></section>;
}
