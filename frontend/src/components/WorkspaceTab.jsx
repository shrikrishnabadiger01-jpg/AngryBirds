import React, { useEffect, useMemo, useState } from 'react';
import { marked } from 'marked';
import { Activity, AlertTriangle, Check, ChevronDown, FileText, LockKeyhole, Mail, Play, RefreshCw, Send, ShieldAlert, ShieldCheck, X } from 'lucide-react';
import { Decision, EmptyState } from './HomeTab';

const PRESETS = [
  { label: 'Summarize project update', docId: 'project_report', task: 'Summarize the delayed milestones and their reasons.', email: false },
  { label: 'Inspect a prompt injection', docId: 'project_report_injected', task: 'Summarize the delayed milestones and their reasons.', email: false },
  { label: 'Review recipient redirection', docId: 'report_recipient_redirect', task: 'Summarize delayed milestones and email the manager with the report.', email: true },
  { label: 'Prepare an approved update', docId: 'project_report', task: 'Summarize delayed milestones and send an update email to the manager.', email: true },
  { label: 'Read a harmless security note', docId: 'report_training_quote', task: 'Summarize the document key points.', email: false },
];

export default function WorkspaceTab({ documents = [], currentRun, isRunning, onStartRun, onApproveProposal, canOperate = true, gmailStatus, focusDocumentId }) {
  const [selectedDocId, setSelectedDocId] = useState('project_report');
  const [taskText, setTaskText] = useState('Summarize the delayed milestones and their reasons.');
  const [allowEmail, setAllowEmail] = useState(false);
  const [recipientAllowlist, setRecipientAllowlist] = useState('manager@example.com');
  const [allowedDocuments, setAllowedDocuments] = useState(['project_report']);
  const [maxEmails, setMaxEmails] = useState(1);
  const [requiredSubject, setRequiredSubject] = useState('');
  const docs = documents.filter(doc => !doc.is_confidential);
  const selectedDoc = docs.find(doc => doc.id === selectedDocId) || docs[0];
  useEffect(() => { if (focusDocumentId && docs.some(doc => doc.id === focusDocumentId)) setSelectedDocId(focusDocumentId); }, [focusDocumentId, documents]);
  useEffect(() => { if (selectedDocId && !allowedDocuments.includes(selectedDocId)) setAllowedDocuments(current => [...current, selectedDocId]); }, [selectedDocId]);

  const events = currentRun?.audit || [];
  const lastDecision = events.length ? events[events.length - 1] : null;
  const proposal = currentRun?.pending_approval?.proposal || currentRun?.outbox?.[currentRun.outbox.length - 1] || null;
  const hasRead = events.some(event => event.tool === 'read_doc');
  const steps = useMemo(() => {
    const pending = currentRun?.status === 'awaiting_approval';
    const sent = (currentRun?.outbox || []).length > 0;
    const started = Boolean(currentRun);
    return [
      ['Parse user request', 'Identify the requested outcome and authorized actions', started ? 'done' : 'idle'],
      ['Retrieve relevant data', hasRead ? `Read ${selectedDoc?.title || 'selected document'}` : 'Waits for an agent run', hasRead ? 'done' : 'idle'],
      ['Inspect untrusted content', hasRead ? 'Inspection runs before document content is used' : 'Content is not read until the task starts', hasRead ? 'done' : 'idle'],
      ['Check permissions and intent', lastDecision ? `${lastDecision.decision}: ${lastDecision.reason}` : 'Policy is fixed before external content is read', lastDecision ? 'done' : started ? 'done' : 'idle'],
      ['Prepare requested action', proposal ? `Proposal for ${proposal.recipient || 'recipient not recorded'}` : currentRun?.answer ? 'No email action was proposed' : 'No action prepared yet', proposal || currentRun?.answer ? 'done' : 'idle'],
      ['Human confirmation', pending ? 'Review and approve or deny the exact proposal' : allowEmail ? 'Required before a simulated email is added to the outbox' : 'No email permission granted', pending ? 'review' : sent ? 'done' : 'idle'],
      ['Execute if authorized', sent ? 'Added to simulated outbox; no real email sent' : pending ? 'Waiting for your decision' : currentRun?.status === 'completed' ? 'Run completed' : 'No action executed', sent || currentRun?.status === 'completed' ? 'done' : pending ? 'idle' : 'idle'],
    ];
  }, [currentRun, events, hasRead, selectedDoc, lastDecision, proposal, allowEmail]);

  const submit = event => {
    event.preventDefault();
    if (!taskText.trim() || !selectedDoc || isRunning || !canOperate) return;
    onStartRun({ task: taskText.trim(), document_id: selectedDocId, allow_email: allowEmail, allowed_documents: [...new Set([selectedDocId, ...allowedDocuments])], allowed_recipients: recipientAllowlist.split(/[\n,;]/).map(value => value.trim()).filter(Boolean), max_emails: Number(maxEmails), required_subject: requiredSubject.trim() || null });
  };
  const applyPreset = preset => { setSelectedDocId(preset.docId); setTaskText(preset.task); setAllowEmail(preset.email); setAllowedDocuments([preset.docId]); };
  const downloadRun = () => { if (!currentRun) return; const blob = new Blob([JSON.stringify(currentRun, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `agent_run_${currentRun.run_id || 'result'}.json`; anchor.click(); URL.revokeObjectURL(url); };

  return <div className="page-shell workspace-page">
    <div className="page-heading workspace-heading"><div><div className="eyebrow">AI Guard / Agent workspace</div><h1>Give your agent a task</h1><p>It will read only the permitted sources, inspect their content, and pause before sensitive actions.</p></div><span className="simulation-note"><ShieldCheck size={14}/> Agent emails are simulated</span></div>

    <div className="workspace-layout">
      <aside className="workspace-left">
        <section className="surface-card compact-card"><div className="section-heading"><div><div className="eyebrow">Available tools</div><h2>Data access</h2></div><span className="subtle-count">{docs.length}</span></div>
          <div className="tool-list"><div className="tool-row"><span className="source-icon doc-icon"><FileText size={16}/></span><span><strong>Workspace documents</strong><small>{docs.length} available to runs</small></span><i className="state-dot is-good"/></div><div className="tool-row"><span className="source-icon gmail-icon"><Mail size={16}/></span><span><strong>Gmail scanner</strong><small>{gmailStatus?.connected ? 'Separate read-only inbox scan' : 'Not connected'}</small></span><i className={`state-dot ${gmailStatus?.connected ? 'is-good' : 'is-neutral'}`}/></div></div>
        </section>
        <section className="surface-card compact-card"><div className="eyebrow">Document scope</div><h2>Allowed documents</h2><label className="field-label" htmlFor="workspace-document">Selected document</label><select id="workspace-document" className="field-control" value={selectedDocId} onChange={e => setSelectedDocId(e.target.value)}>{docs.map(doc => <option key={doc.id} value={doc.id}>{doc.title}</option>)}</select>
          <div className="scope-checks">{docs.filter(doc => doc.id !== selectedDocId).map(doc => <label key={doc.id}><input type="checkbox" checked={allowedDocuments.includes(doc.id)} onChange={e => setAllowedDocuments(list => e.target.checked ? [...new Set([...list, doc.id])] : list.filter(id => id !== doc.id))}/><span>{doc.title}</span></label>)}</div>
          <details className="preset-menu"><summary>Load a security scenario <ChevronDown size={14}/></summary><div>{PRESETS.map(preset => <button type="button" key={preset.label} onClick={() => applyPreset(preset)}>{preset.label}</button>)}</div></details>
        </section>
      </aside>

      <section className="workspace-center">
        <form className="surface-card task-composer" onSubmit={submit}><label className="field-label" htmlFor="agent-task">What should the agent do?</label><div className="composer-row"><textarea id="agent-task" value={taskText} onChange={e => setTaskText(e.target.value)} rows={3} placeholder="Find the latest project update and draft an email to the manager…" required/><button type="submit" className="button-primary run-button" disabled={!canOperate || isRunning || !taskText.trim() || !selectedDoc}>{isRunning ? <RefreshCw size={16} className="spin"/> : <Play size={16}/>}<span>{isRunning ? 'Running' : canOperate ? 'Run task' : 'Operator access required'}</span></button></div>
          <div className="composer-foot"><span><LockKeyhole size={13}/> Policy is set before reading external content</span><span>{selectedDoc?.title || 'No document selected'}</span></div>
        </form>

        <section className="surface-card execution-card"><div className="section-heading"><div><div className="eyebrow">Execution flow</div><h2>Agent activity</h2></div><div className="run-status"><i className={`state-dot ${isRunning ? 'is-warn' : currentRun ? 'is-good' : 'is-neutral'}`}/>{isRunning ? 'In progress' : currentRun?.status || 'Ready'}</div></div>
          <ol className="execution-timeline">{steps.map(([title, detail, state], index) => <li key={title} className={`timeline-step step-${state}`}><span className="step-marker">{state === 'done' ? <Check size={14}/> : state === 'review' ? <AlertTriangle size={14}/> : <span>{index + 1}</span>}</span><div className="step-copy"><strong>{title}</strong><small>{detail}</small></div><span className="step-state">{state === 'done' ? 'Complete' : state === 'review' ? 'Review required' : currentRun ? 'Pending' : 'Not started'}</span></li>)}</ol>
        </section>

        <section className="surface-card result-card"><div className="section-heading"><div><div className="eyebrow">Agent response</div><h2>Task result</h2></div>{currentRun && <div className="button-row"><Decision value={currentRun.status}/><button className="button-quiet" onClick={downloadRun} type="button">Export JSON</button></div>}</div>
          {currentRun?.error && <div className="inline-error">{currentRun.error}</div>}
          {currentRun?.answer ? <SafeMarkdown text={currentRun.answer}/> : currentRun?.status === 'awaiting_approval' ? <div className="inline-notice"><ShieldAlert size={16}/> The agent paused because the proposed email requires your approval.</div> : currentRun ? <p className="muted-copy">The run did not return a summary.</p> : <EmptyState title="Ready for a task" detail="Choose a permitted document, write a request, and run the agent."/>}
          {currentRun?.audit?.length > 0 && <details className="run-audit"><summary>Runtime decisions · {currentRun.audit.length}<ChevronDown size={14}/></summary><div className="table-scroll"><table className="data-table"><thead><tr><th>Decision</th><th>Action</th><th>Reason</th><th>Executed</th></tr></thead><tbody>{currentRun.audit.map((event, i) => <tr key={i}><td><Decision value={event.decision}/></td><td><code>{event.tool}</code></td><td>{event.reason}</td><td>{event.executed ? 'Yes' : 'No'}</td></tr>)}</tbody></table></div></details>}
          {currentRun?.outbox?.length > 0 && <div className="outbox-notice"><Check size={15}/><span>{currentRun.outbox.length} email action(s) added to the simulated outbox. No real email was sent.</span></div>}
        </section>
      </section>

      <aside className="workspace-right">
        <section className="surface-card compact-card"><div className="section-heading"><div><div className="eyebrow">Current task</div><h2>Task options</h2></div><Activity size={17}/></div><p className="task-summary">{taskText || 'No task entered yet.'}</p><div className="policy-switch"><label><input type="checkbox" checked={allowEmail} onChange={e => setAllowEmail(e.target.checked)}/><span>Allow simulated email</span></label><small>Requires recipient allowlist and human confirmation</small></div>{allowEmail && <div className="policy-fields"><label className="field-label" htmlFor="allowed-recipients">Allowed recipients</label><textarea id="allowed-recipients" className="field-control" rows={2} value={recipientAllowlist} onChange={e => setRecipientAllowlist(e.target.value)} placeholder="name@example.com"/><label className="field-label" htmlFor="email-cap">Email limit</label><input id="email-cap" className="field-control" type="number" min="0" max="10" value={maxEmails} onChange={e => setMaxEmails(e.target.value)}/><label className="field-label" htmlFor="subject-rule">Required subject</label><input id="subject-rule" className="field-control" maxLength="200" value={requiredSubject} onChange={e => setRequiredSubject(e.target.value)} placeholder="Optional exact subject"/></div>}</section>

        <section className="surface-card compact-card security-check"><div className="section-heading"><div><div className="eyebrow">Security check</div><h2>{selectedDoc?.findings_count ? 'Review signals' : 'Document inspection'}</h2></div>{selectedDoc?.findings_count ? <AlertTriangle size={17}/> : <ShieldCheck size={17}/>}</div>{lastDecision ? <div className="decision-summary"><Decision value={lastDecision.decision}/><p>{lastDecision.reason}</p></div> : <p className="muted-copy">{selectedDoc?.findings_count ? `${selectedDoc.findings_count} pattern signal(s) found in ${selectedDoc.title}.` : 'No saved action decision for this task yet.'}</p>}{selectedDoc?.findings?.length > 0 && <details className="evidence-details"><summary>Matched evidence ({selectedDoc.findings.length})</summary>{selectedDoc.findings.map((finding, i) => <p key={i}><strong>{finding.signal}</strong><code>{finding.matched_text}</code></p>)}</details>}</section>

        <section className="surface-card compact-card draft-card"><div className="section-heading"><div><div className="eyebrow">Email action</div><h2>{proposal ? 'Proposal preview' : 'No draft prepared'}</h2></div><Mail size={17}/></div>{proposal ? <><div className="draft-field"><span>To</span><strong>{proposal.recipient || 'Not recorded'}</strong></div><div className="draft-field"><span>Subject</span><strong>{proposal.subject || 'Not recorded'}</strong></div><div className="draft-body">{proposal.body || 'No body recorded.'}</div>{currentRun?.status === 'awaiting_approval' && <><p className="approval-lock">This proposal is fixed for approval. To change it, update the task and run again.</p><div className="button-row"><button type="button" className="button-secondary" disabled={!canOperate || isRunning} onClick={() => onApproveProposal(currentRun.run_id, currentRun.pending_approval.token, false)}><X size={14}/> Deny</button><button type="button" className="button-primary" disabled={!canOperate || isRunning} onClick={() => onApproveProposal(currentRun.run_id, currentRun.pending_approval.token, true)}><Send size={14}/> Approve simulated send</button></div></>}</> : <p className="muted-copy">Email drafts appear here when a run proposes a recipient and email permission is enabled. Approval adds them to the simulated outbox only.</p>}</section>
      </aside>
    </div>
  </div>;
}

function SafeMarkdown({ text }) {
  const tokens = marked.lexer(text, { gfm: true });
  return <div className="markdown-answer">{tokens.map((token, index) => {
    if (token.type === 'heading') return <h3 key={index}>{token.text}</h3>;
    if (token.type === 'paragraph') return <p key={index}>{token.text}</p>;
    if (token.type === 'list') {
      const List = token.ordered ? 'ol' : 'ul';
      return <List key={index}>{token.items.map((item, itemIndex) => <li key={itemIndex}>{item.text}</li>)}</List>;
    }
    if (token.type === 'code') return <pre key={index}><code>{token.text}</code></pre>;
    if (token.type === 'blockquote') return <blockquote key={index}>{token.text}</blockquote>;
    if (token.type === 'hr') return <hr key={index}/>;
    return null;
  })}</div>;
}
