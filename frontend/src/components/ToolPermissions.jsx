import React, { useState } from 'react';
import { Settings } from 'lucide-react';

function PermissionToggle({ checked, disabled, label, tone = 'sage', onChange }) {
  return <button type="button" role="switch" aria-checked={checked} aria-label={label} disabled={disabled} onClick={() => onChange(!checked)} className={`tool-toggle ${checked ? 'checked' : ''} ${checked && tone === 'amber' ? 'amber' : ''}`}><span/></button>;
}

export default function ToolPermissions({ documentsEnabled, onDocumentsEnabledChange, allowEmail, onAllowEmailChange, gmailStatus, canOperate = true, onConnectGmail, onDisconnectGmail }) {
  const [manageOpen, setManageOpen] = useState(false);
  const gmailConnected = Boolean(gmailStatus?.connected);
  const gmailCanSend = Boolean(gmailStatus?.can_send);
  const permissions = [
    { name: 'Read emails', status: gmailConnected ? 'Read-only inbox' : 'Not connected', checked: gmailConnected, disabled: !canOperate, action: enabled => enabled ? onConnectGmail?.() : onDisconnectGmail?.() },
    { name: 'Send emails', status: !gmailCanSend ? (gmailConnected ? 'Permission needed' : 'Gmail not connected') : allowEmail ? 'Require confirmation' : 'Disabled', checked: allowEmail, disabled: !canOperate || !gmailCanSend, tone: 'amber', action: onAllowEmailChange },
    { name: 'Read documents', status: documentsEnabled ? 'Allow' : 'Disabled', checked: documentsEnabled, disabled: false, action: onDocumentsEnabledChange },
    { name: 'Web search', status: 'Unavailable', checked: false, disabled: true, action: () => {} },
    { name: 'Access messages', status: 'Disabled', checked: false, disabled: true, action: () => {} },
    { name: 'Modify calendar', status: 'Disabled', checked: false, disabled: true, action: () => {} },
  ];

  const changeGmail = enabled => {
    if (enabled) onConnectGmail?.();
    else if (window.confirm('Disconnect Gmail? This removes the saved Gmail connection and its permissions.')) onDisconnectGmail?.();
  };

  return <section className="surface-card tool-permissions-card">
    <header className="tool-permissions-heading"><h2>Tool Permissions</h2><p>Control what actions the agent can perform.</p></header>
    <div className="tool-permissions-list">{permissions.map(permission => <div className={`tool-permission-row ${permission.name === 'Send emails' && !gmailCanSend ? 'send-access-needed' : ''}`} key={permission.name}>
      <strong>{permission.name}</strong><span className={`tool-permission-status ${permission.checked ? permission.tone === 'amber' ? 'confirmation' : 'allowed' : 'disabled'}`}>{permission.status}</span>
      {permission.name === 'Send emails' && !gmailCanSend
        ? <button type="button" className="grant-gmail-button" disabled={!canOperate} onClick={onConnectGmail}>{gmailConnected ? 'Grant access' : 'Connect Gmail'}</button>
        : <PermissionToggle checked={permission.checked} disabled={permission.disabled} label={`${permission.name}: ${permission.status}`} tone={permission.tone} onChange={permission.name === 'Read emails' ? changeGmail : permission.action}/>}
    </div>)}</div>
    <button type="button" className="manage-permissions-button" aria-expanded={manageOpen} onClick={() => setManageOpen(open => !open)}><Settings size={15}/>{manageOpen ? 'Hide Permission Details' : 'Manage Permissions'}</button>
    {manageOpen && <div className="permission-details"><p>Document access follows the selected document scope.</p><p>To send email, grant Gmail send access, turn on the permission for a task, add an allowed recipient, then approve the exact message before it is sent.</p><p>Web Search, Messages, and Calendar are unavailable until those integrations are configured.</p></div>}
  </section>;
}
