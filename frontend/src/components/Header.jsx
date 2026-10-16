import React from 'react';
import { Shield, House, UsersRound, Database, ShieldCheck, ClipboardCheck, FileSearch, LogOut, Mail } from 'lucide-react';

const ITEMS = [
  ['home', House, 'Home'], ['workspace', UsersRound, 'Agent Workspace'],
  ['sources', Database, 'Data Sources'], ['security', ShieldCheck, 'Security Center'],
  ['evaluations', ClipboardCheck, 'Evaluations'], ['audit', FileSearch, 'Audit Logs'],
];

export default function Header({ activeTab, onSelectTab, health, gmailStatus, authUser, onLogout, onOpenGmail }) {
  const active = activeTab === 'gmail' ? 'sources' : activeTab === 'scripted' ? 'security' : activeTab;
  const healthy = health?.status === 'healthy';
  return <header className="app-header"><div className="header-container">
    <button className="brand-section" onClick={() => onSelectTab('home')} aria-label="AI Guard home"><span className="brand-logo"><Shield size={21}/></span><span className="brand-copy"><strong>AI Guard</strong><small>Secure AI Agents</small></span></button>
    <nav className="nav-tab-list" aria-label="Main navigation">{ITEMS.map(([id, Icon, label]) => <button key={id} type="button" onClick={() => onSelectTab(id)} className={`nav-tab-btn ${active === id ? 'active' : ''}`}><Icon size={15}/><span>{label}</span></button>)}</nav>
    <div className="header-controls"><div className="header-system"><span className={`state-dot ${!health ? 'is-neutral' : healthy ? 'is-good' : 'is-bad'}`}/>{!health ? 'Checking system' : healthy ? 'System online' : 'System unavailable'}</div><button className="header-mail" title={gmailStatus?.connected ? `Gmail connected: ${gmailStatus.email || ''}` : 'Gmail not connected'} onClick={onOpenGmail} aria-label="Open Gmail inbox"><Mail size={17}/><span className={`state-dot ${gmailStatus?.connected ? 'is-good' : 'is-neutral'}`}/></button>{authUser && <button type="button" onClick={onLogout} className="user-menu" title={`Sign out ${authUser.username}`}><span className="user-avatar">{authUser.username.slice(0, 2).toUpperCase()}</span><span>{authUser.username} · {authUser.role}</span><LogOut size={14}/></button>}</div>
  </div></header>;
}
