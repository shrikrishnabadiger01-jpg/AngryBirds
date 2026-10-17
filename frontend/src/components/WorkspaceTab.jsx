import React, { useEffect, useMemo, useState } from 'react';
import { marked } from 'marked';
import { Activity, AlertTriangle, Check, ChevronDown, LockKeyhole, Mail, Play, RefreshCw, Send, ShieldAlert, ShieldCheck, X } from 'lucide-react';
import { Decision, EmptyState } from './HomeTab';
import AvailableTools from './AvailableTools';
import ToolPermissions from './ToolPermissions';
import { api } from '../services/api';

export default function WorkspaceTab({ documents = [], currentRun, isRunning, onStartRun, onApproveProposal, canOperate = true, gmailStatus, focusDocumentId, onConnectGmail, onDisconnectGmail }) {
  const [selectedDocId, setSelectedDocId] = useState('');
  const [taskText, setTaskText] = useState('');
  const [allowEmail, setAllowEmail] = useState(false);
  const [recipientAllowlist, setRecipientAllowlist] = useState('');
  const [allowedDocuments, setAllowedDocuments] = useState([]);
  const [maxEmails, setMaxEmails] = useState(1);
  const [requiredSubject, setRequiredSubject] = useState('');
  const [documentsEnabled, setDocumentsEnabled] = useState(documents.length > 0);
  const [sourceType, setSourceType] = useState('document');
  const [inboxEmails, setInboxEmails] = useState([]);
  const [selectedEmailIds, setSelectedEmailIds] = useState([]);
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailSecurityReview, setEmailSecurityReview] = useState(null);
  const [emailSecurityRunId, setEmailSecurityRunId] = useState('');
  const docs = documents.filter(doc => !doc.is_confidential);
  const emailSummaryRequest = /\b(?:summari[sz]e|summary)\b.{0,40}\b(?:emails?|inboxes?|messages?)\b|\b(?:emails?|inboxes?|messages?)\b.{0,40}\b(?:summari[sz]e|summary)\b/i.test(taskText);
  useEffect(() => { if (docs.length > 0) setDocumentsEnabled(true); }, [docs.length]);
  const selectedDoc = docs.find(doc => doc.id === selectedDocId) || docs[0];
  useEffect(() => { if (docs.length && !docs.some(doc => doc.id === selectedDocId)) setSelectedDocId(docs[0].id); }, [documents, selectedDocId]);
  useEffect(() => { if (focusDocumentId && docs.some(doc => doc.id === focusDocumentId)) setSelectedDocId(focusDocumentId); }, [focusDocumentId, documents]);
  useEffect(() => { if (selectedDocId && !allowedDocuments.includes(selectedDocId)) setAllowedDocuments(current => [...current, selectedDocId]); }, [selectedDocId]);
  useEffect(() => {
    let active = true;
    if (!gmailStatus?.connected) { setInboxEmails([]); setSelectedEmailIds([]); return () => { active = false; }; }
    setEmailLoading(true);
    api.getEmails(20).then(result => {
      if (!active) return;
      const messages = result.emails || [];
      setInboxEmails(messages);
      setSelectedEmailIds(current => {
        const stillAvailable = current.filter(id => messages.some(email => email.id === id));
        return stillAvailable.length ? stillAvailable : messages.slice(0, 5).map(email => email.id);
      });
    }).catch(() => { if (active) setInboxEmails([]); }).finally(() => { if (active) setEmailLoading(false); });
    return () => { active = false; };
  }, [gmailStatus?.connected]);
  useEffect(() => {
    if (!emailSummaryRequest || inboxEmails.length === 0) return;
    const requestedCount = taskText.match(/\b(\d{1,2})\s+emails?\b/i)?.[1];
    if (requestedCount) {
      const count = Math.max(1, Math.min(Number(requestedCount), 20));
      setSelectedEmailIds(inboxEmails.slice(0, count).map(email => email.id));
    }
  }, [emailSummaryRequest, taskText, inboxEmails]);

  useEffect(() => {
    if (!canOperate || currentRun?.status !== 'completed' || !currentRun?.answer || !currentRun?.run_id || emailSecurityRunId === currentRun.run_id) return;
    const emailIds = [...new Set((currentRun.audit || [])
      .filter(event => event.tool === 'read_email' && event.executed && event.arguments?.email_id)
      .map(event => event.arguments.email_id))];
    const analyzedEmails = emailIds.map(id => ({ id, email: inboxEmails.find(item => item.id === id) })).filter(item => item.email);
    if (emailIds.length === 0) return;
    setEmailSecurityRunId(currentRun.run_id);
    if (analyzedEmails.length === 0) {
      setEmailSecurityReview({ runId: currentRun.run_id, loading: false, suspicious: [], failed: true, checkedCount: 0 });
      return;
    }
    setEmailSecurityReview({ runId: currentRun.run_id, loading: true, suspicious: [], failed: false, checkedCount: 0 });
    Promise.all(analyzedEmails.map(async ({ id, email }) => {
      try {
        return await api.analyzeEmail({
          email_id: id,
          subject: email.subject || '',
          body: email.body || email.snippet || '',
          sender: email.sender || 'unknown@domain.com',
          recipient: email.recipient,
        });
      } catch {
        return null;
      }
    })).then(results => {
      const validResults = results.filter(Boolean);
      setEmailSecurityReview({
        runId: currentRun.run_id,
        loading: false,
        failed: validResults.length !== emailIds.length,
        checkedCount: validResults.length,
        suspicious: validResults.filter(result => result.decision !== 'ALLOW' || result.threat_level !== 'safe'),
      });
    });
  }, [canOperate, currentRun?.run_id, currentRun?.status, currentRun?.answer, currentRun?.audit, inboxEmails, emailSecurityRunId]);

  const events = currentRun?.audit || [];
  const emailThreats = (() => {
    const threats = events
      .filter(event => event.tool === 'read_email' && event.security_decision === 'SUSPICIOUS')
      .map(event => ({ subject: event.subject, threat_level: event.threat_level, reason: event.security_reason || event.reason }));
    if (emailSecurityReview && emailSecurityReview.runId === currentRun?.run_id) {
      threats.push(...emailSecurityReview.suspicious.map(email => ({ subject: email.subject, threat_level: email.threat_level, reason: email.reason })));
    }
    const seen = new Set();
    return threats.filter(threat => {
      const key = (threat.subject || '').trim().toLowerCase();
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  })();
  const lastDecision = events.length ? events[events.length - 1] : null;
  const proposal = currentRun?.pending_approval?.proposal || currentRun?.outbox?.[currentRun.outbox.length - 1] || null;
  const hasRead = events.some(event => event.tool === 'read_doc');
  const hasReadEmail = events.some(event => event.tool === 'read_email');
  const hasWebSearch = events.some(event => event.tool === 'web_search' && event.executed);
  const steps = useMemo(() => {
    const pending = currentRun?.status === 'awaiting_approval';
    const sent = (currentRun?.outbox || []).length > 0;
    const started = Boolean(currentRun);
    return [
      ['Parse user request', 'Identify the requested outcome and authorized actions', started ? 'done' : 'idle'],
      ['Retrieve relevant data', hasReadEmail && hasWebSearch ? 'Read email and grounded web results' : hasReadEmail ? 'Read the selected Gmail message' : hasRead ? `Read ${selectedDoc?.title || 'selected document'}` : hasWebSearch ? 'Retrieved grounded web results' : 'Waits for an agent run', hasRead || hasReadEmail || hasWebSearch ? 'done' : 'idle'],
      ['Inspect untrusted content', hasReadEmail && hasWebSearch ? 'Email and web results are treated as untrusted' : hasReadEmail ? 'Email content is treated as untrusted' : hasRead ? 'Inspection runs before document content is used' : hasWebSearch ? 'Search results and tool outputs are treated as untrusted' : 'Content is not read until the task starts', hasRead || hasReadEmail || hasWebSearch ? 'done' : 'idle'],
      ['Check permissions and intent', lastDecision ? `${lastDecision.decision}: ${lastDecision.reason}` : 'Policy is fixed before external content is read', lastDecision ? 'done' : started ? 'done' : 'idle'],
      ['Prepare requested action', proposal ? `Proposal for ${proposal.recipient || 'recipient not recorded'}` : currentRun?.answer ? 'No email action was proposed' : 'No action prepared yet', proposal || currentRun?.answer ? 'done' : 'idle'],
      ['Human confirmation', pending ? 'Review and approve or deny the exact proposal' : allowEmail ? 'Required before Gmail sends a message' : 'No email permission granted', pending ? 'review' : sent ? 'done' : 'idle'],
      ['Execute if authorized', sent ? 'Sent through Gmail' : pending ? 'Waiting for your decision' : currentRun?.status === 'completed' ? 'Run completed' : 'No action executed', sent || currentRun?.status === 'completed' ? 'done' : pending ? 'idle' : 'idle'],
    ];
  }, [currentRun, events, hasRead, hasReadEmail, hasWebSearch, selectedDoc, lastDecision, proposal, allowEmail]);

  useEffect(() => { if (emailSummaryRequest) setSourceType('email'); }, [emailSummaryRequest]);

  const submit = event => {
    event.preventDefault();
    if (!taskText.trim() || isRunning || !canOperate) return;
    if (sourceType === 'email' ? selectedEmailIds.length === 0 : (!selectedDoc || !documentsEnabled)) return;
    onStartRun({ task: taskText.trim(), document_id: selectedDocId || docs[0]?.id || 'project_report', email_ids: sourceType === 'email' ? selectedEmailIds : [], allow_email: allowEmail, allowed_documents: [...new Set([selectedDocId, ...allowedDocuments].filter(Boolean))], allowed_recipients: recipientAllowlist.split(/[\n,;]/).map(value => value.trim()).filter(Boolean), max_emails: Number(maxEmails), required_subject: requiredSubject.trim() || null });
  };
  const downloadRun = () => { if (!currentRun) return; const blob = new Blob([JSON.stringify(currentRun, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `agent_run_${currentRun.run_id || 'result'}.json`; anchor.click(); URL.revokeObjectURL(url); };

  return <div className="page-shell workspace-page">
    <div className="page-heading workspace-heading"><div><div className="eyebrow">AI Guard / Agent workspace</div><h1>Give your agent a task</h1><p>It will read only the permitted sources, inspect their content, and pause before sensitive actions.</p></div><span className="simulation-note"><ShieldCheck size={14}/>{gmailStatus?.can_send ? 'Email requires your approval' : 'Authorize Gmail to send email'}</span></div>

    <div className="workspace-layout">
      <aside className="workspace-left">
        <AvailableTools documents={docs} documentsEnabled={documentsEnabled} onDocumentsEnabledChange={setDocumentsEnabled} gmailStatus={gmailStatus} canOperate={canOperate} onConnectGmail={onConnectGmail} onDisconnectGmail={onDisconnectGmail}/>
        <ToolPermissions documentsEnabled={documentsEnabled} onDocumentsEnabledChange={setDocumentsEnabled} allowEmail={allowEmail} onAllowEmailChange={setAllowEmail} gmailStatus={gmailStatus} canOperate={canOperate} onConnectGmail={onConnectGmail} onDisconnectGmail={onDisconnectGmail}/>
        <section className="surface-card compact-card"><div className="eyebrow">Task source</div><h2>Choose what to read</h2><label className="field-label" htmlFor="workspace-source">Source type</label><select id="workspace-source" className="field-control" value={sourceType} onChange={e => setSourceType(e.target.value)}><option value="document">Workspace document</option><option value="email">Gmail inbox email</option></select>
          {sourceType === 'document' ? <><label className="field-label" htmlFor="workspace-document">Selected document</label><select id="workspace-document" className="field-control" value={selectedDocId} onChange={e => setSelectedDocId(e.target.value)}>{docs.map(doc => <option key={doc.id} value={doc.id}>{doc.title}</option>)}</select><div className="scope-checks">{docs.filter(doc => doc.id !== selectedDocId).map(doc => <label key={doc.id}><input type="checkbox" checked={allowedDocuments.includes(doc.id)} onChange={e => setAllowedDocuments(list => e.target.checked ? [...new Set([...list, doc.id])] : list.filter(id => id !== doc.id))}/><span>{doc.title}</span></label>)}</div></> : <><span className="field-label">Inbox emails to include</span>{gmailStatus?.connected ? <div className="scope-checks">{emailLoading ? <small>Loading inbox…</small> : inboxEmails.length ? inboxEmails.map(email => <label key={email.id}><input type="checkbox" checked={selectedEmailIds.includes(email.id)} onChange={e => setSelectedEmailIds(current => e.target.checked ? [...new Set([...current, email.id])] : current.filter(id => id !== email.id))}/><span>{email.subject || '(No subject)'} — {email.senderName || email.sender}</span></label>) : <small>No inbox emails found.</small>}</div> : <><p className="muted-copy">Connect Gmail with read access to summarize inbox emails.</p><button type="button" className="button-secondary" onClick={onConnectGmail} disabled={!canOperate}>Connect Gmail</button></>}</>}
        </section>
      </aside>

      <section className="workspace-center">
        <form className="surface-card task-composer" onSubmit={submit}><label className="field-label" htmlFor="agent-task">What should the agent do?</label><div className="composer-row"><textarea id="agent-task" value={taskText} onChange={e => setTaskText(e.target.value)} rows={3} placeholder="Describe the task you want the agent to perform…" required/><button type="submit" className="button-primary run-button" disabled={!canOperate || isRunning || !taskText.trim() || (sourceType === 'email' ? selectedEmailIds.length === 0 : (!selectedDoc || !documentsEnabled))}>{isRunning ? <RefreshCw size={16} className="spin"/> : <Play size={16}/>}<span>{isRunning ? 'Running' : canOperate ? 'Run task' : 'Operator access required'}</span></button></div>
          <div className="composer-foot"><span><LockKeyhole size={13}/> Policy is set before reading external content</span><span>{sourceType === 'email' ? `${selectedEmailIds.length} inbox email${selectedEmailIds.length === 1 ? '' : 's'} selected` : selectedDoc?.title || 'No document selected'}</span></div>
        </form>

        <section className="surface-card execution-card"><div className="section-heading"><div><div className="eyebrow">Execution flow</div><h2>Agent activity</h2></div><div className="run-status"><i className={`state-dot ${isRunning ? 'is-warn' : currentRun ? 'is-good' : 'is-neutral'}`}/>{isRunning ? 'In progress' : currentRun?.status || 'Ready'}</div></div>
          <ol className="execution-timeline">{steps.map(([title, detail, state], index) => <li key={title} className={`timeline-step step-${state}`}><span className="step-marker">{state === 'done' ? <Check size={14}/> : state === 'review' ? <AlertTriangle size={14}/> : <span>{index + 1}</span>}</span><div className="step-copy"><strong>{title}</strong><small>{detail}</small></div><span className="step-state">{state === 'done' ? 'Complete' : state === 'review' ? 'Review required' : currentRun ? 'Pending' : 'Not started'}</span></li>)}</ol>
        </section>

        <section className="surface-card result-card"><div className="section-heading"><div><div className="eyebrow">Agent response</div><h2>Task result</h2></div>{currentRun && <div className="button-row"><Decision value={currentRun.status}/><button className="button-quiet" onClick={downloadRun} type="button">Export JSON</button></div>}</div>
          {currentRun?.error && <div className="inline-error">{currentRun.error}</div>}
          {currentRun?.answer ? <SafeMarkdown text={currentRun.answer} emailThreats={emailThreats}/> : currentRun?.status === 'awaiting_approval' ? <div className="inline-notice"><ShieldAlert size={16}/> The agent paused because the proposed email requires your approval.</div> : currentRun ? <p className="muted-copy">The run did not return a summary.</p> : <EmptyState title="Ready for a task" detail="Choose a permitted document, write a request, and run the agent."/>}
          {currentRun?.audit?.length > 0 && <details className="run-audit"><summary>Runtime decisions · {currentRun.audit.length}<ChevronDown size={14}/></summary><div className="table-scroll"><table className="data-table"><thead><tr><th>Decision</th><th>Action</th><th>Reason</th><th>Executed</th></tr></thead><tbody>{currentRun.audit.map((event, i) => <tr key={i}><td><Decision value={event.decision}/></td><td><code>{event.tool}</code></td><td>{event.reason}</td><td>{event.executed ? 'Yes' : 'No'}</td></tr>)}</tbody></table></div></details>}
          {currentRun?.outbox?.length > 0 && <div className="outbox-notice"><Check size={15}/><span>{currentRun.outbox.filter(item => item.status === 'sent').length} email(s) sent through Gmail.</span></div>}
        </section>
      </section>

      <aside className="workspace-right">
        <section className="surface-card compact-card"><div className="section-heading"><div><div className="eyebrow">Current task</div><h2>Task options</h2></div><Activity size={17}/></div><p className="task-summary">{taskText || 'No task entered yet.'}</p><div className="policy-switch"><label><input type="checkbox" checked={allowEmail} onChange={e => setAllowEmail(e.target.checked)} disabled={!gmailStatus?.can_send}/><span>Allow email sending</span></label><small>{!gmailStatus?.can_send ? (gmailStatus?.connected ? 'Reconnect Gmail with the send permission under Tool Permissions' : 'Connect Gmail with send access under Tool Permissions first') : 'Requires an allowed recipient and your approval before sending'}</small></div>{allowEmail && <div className="policy-fields"><label className="field-label" htmlFor="allowed-recipients">Allowed recipients</label><textarea id="allowed-recipients" className="field-control" rows={2} value={recipientAllowlist} onChange={e => setRecipientAllowlist(e.target.value)} placeholder="name@example.com"/><label className="field-label" htmlFor="email-cap">Email limit</label><input id="email-cap" className="field-control" type="number" min="0" max="10" value={maxEmails} onChange={e => setMaxEmails(e.target.value)}/><label className="field-label" htmlFor="subject-rule">Required subject</label><input id="subject-rule" className="field-control" maxLength="200" value={requiredSubject} onChange={e => setRequiredSubject(e.target.value)} placeholder="Optional exact subject"/></div>}</section>

        <section className="surface-card compact-card security-check"><div className="section-heading"><div><div className="eyebrow">Security check</div><h2>{emailSecurityReview && emailSecurityReview.runId === currentRun?.run_id ? 'Email security results' : selectedDoc?.findings_count ? 'Review signals' : 'Document inspection'}</h2></div>{selectedDoc?.findings_count || emailSecurityReview?.suspicious?.length ? <AlertTriangle size={17}/> : <ShieldCheck size={17}/>}</div>{lastDecision ? <div className="decision-summary"><Decision value={lastDecision.decision}/><p>{lastDecision.reason}</p></div> : <p className="muted-copy">{selectedDoc?.findings_count ? `${selectedDoc.findings_count} pattern signal(s) found in ${selectedDoc.title}.` : 'No saved action decision for this task yet.'}</p>}{selectedDoc?.findings?.length > 0 && <details className="evidence-details"><summary>Matched evidence ({selectedDoc.findings.length})</summary>{selectedDoc.findings.map((finding, i) => <p key={i}><strong>{finding.signal}</strong><code>{finding.matched_text}</code></p>)}</details>}
          {emailSecurityReview && emailSecurityReview.runId === currentRun?.run_id && <div className="email-security-review"><div className="eyebrow">Emails in this summary</div><strong>{emailSecurityReview.loading ? 'Checking selected emails…' : `Suspicious emails · ${emailSecurityReview.suspicious.length}`}</strong>{emailSecurityReview.loading ? <p className="muted-copy">Reviewing the selected messages for phishing and prompt injection.</p> : emailSecurityReview.suspicious.length === 0 && emailSecurityReview.failed && emailSecurityReview.checkedCount === 0 ? <p className="muted-copy">Could not analyze the selected emails.</p> : emailSecurityReview.suspicious.length === 0 ? <p className="muted-copy">No suspicious emails found among {emailSecurityReview.checkedCount} analyzed email(s).</p> : emailSecurityReview.suspicious.map((email, index) => <div className="email-security-item" key={email.email_id || index}><strong>{email.subject || '(No subject)'}</strong><small>{email.sender} · {email.threat_level?.toUpperCase()}</small><p className="email-security-summary"><strong>Summary:</strong> {email.summary || 'AI summary unavailable. The security warning is still available below.'}</p><p>{email.reason}</p>{(email.indicators || []).map((indicator, findingIndex) => <small key={findingIndex}>{indicator.description}</small>)}</div>)}{emailSecurityReview.failed && emailSecurityReview.checkedCount > 0 && <small>Some selected emails could not be checked.</small>}</div>}
        </section>

        <section className="surface-card compact-card draft-card"><div className="section-heading"><div><div className="eyebrow">Email action</div><h2>{proposal ? 'Proposal preview' : 'No email proposed'}</h2></div><Mail size={17}/></div>{proposal ? <><div className="draft-field"><span>To</span><strong>{proposal.recipient || 'Not recorded'}</strong></div><div className="draft-field"><span>Subject</span><strong>{proposal.subject || 'Not recorded'}</strong></div><div className="draft-body">{proposal.body || 'No body recorded.'}</div>{currentRun?.status === 'awaiting_approval' && <><p className="approval-lock">Review the exact message before allowing Gmail to send it.</p><div className="button-row"><button type="button" className="button-secondary" disabled={!canOperate || isRunning} onClick={() => onApproveProposal(currentRun.run_id, currentRun.pending_approval.token, false)}><X size={14}/> Deny</button><button type="button" className="button-primary" disabled={!canOperate || isRunning} onClick={() => onApproveProposal(currentRun.run_id, currentRun.pending_approval.token, true)}><Send size={14}/> Approve and send</button></div></>}</> : <p className="muted-copy">A proposed email appears here when you enable email sending and the agent prepares a message. Gmail sends only after you approve it.</p>}</section>
      </aside>
    </div>
  </div>;
}

function SafeMarkdown({ text, emailThreats = [] }) {
  const tokens = marked.lexer(text, { gfm: true });
  const renderInline = (parts, prefix) => (parts || []).map((part, index) => {
    const key = `${prefix}-${index}`;
    const children = renderInline(part.tokens, key);
    switch (part.type) {
      case 'strong': return <strong key={key}>{children}</strong>;
      case 'em': return <em key={key}>{children}</em>;
      case 'del': return <del key={key}>{children}</del>;
      case 'codespan': return <code key={key}>{part.text}</code>;
      case 'br': return <br key={key}/>;
      case 'link': {
        const href = /^(https?:|mailto:)/i.test(part.href || '') ? part.href : null;
        return href ? <a key={key} href={href} target="_blank" rel="noreferrer">{children}</a> : <React.Fragment key={key}>{children}</React.Fragment>;
      }
      case 'image': return <React.Fragment key={key}>{part.text}</React.Fragment>;
      case 'text': return part.tokens ? <React.Fragment key={key}>{children}</React.Fragment> : part.text;
      case 'escape':
      case 'html': return <React.Fragment key={key}>{part.text}</React.Fragment>;
      default: return <React.Fragment key={key}>{part.tokens ? children : (part.text || '')}</React.Fragment>;
    }
  });
  const renderListItem = (item, prefix) => item.tokens?.length
    ? item.tokens.map((part, index) => part.type === 'paragraph'
      ? <p key={`${prefix}-${index}`}>{renderInline(part.tokens, `${prefix}-${index}`)}</p>
      : <React.Fragment key={`${prefix}-${index}`}>{renderInline(part.tokens || [], `${prefix}-${index}`)}</React.Fragment>)
    : renderInline(marked.Lexer.lexInline(item.text || ''), prefix);
  return <div className="markdown-answer">{tokens.map((token, index) => {
    const key = `block-${index}`;
    if (token.type === 'heading') return <h3 key={key}>{renderInline(token.tokens, key)}</h3>;
    if (token.type === 'paragraph') return <p key={key}>{renderInline(token.tokens, key)}</p>;
    if (token.type === 'list') {
      const List = token.ordered ? 'ol' : 'ul';
      return <List key={key}>{token.items.map((item, itemIndex) => {
        const itemText = (item.text || '').toLowerCase();
        const threat = emailThreats.find(email => itemText.includes((email.subject || '').toLowerCase()));
        return <li key={`${key}-${itemIndex}`}>{threat ? <div className="threat-marked-line"><span className={`threat-indicator threat-${threat.threat_level || 'medium'}`} title={threat.reason || 'This email was flagged by the security scan'}><AlertTriangle size={12}/><span>{(threat.threat_level || 'suspicious').toUpperCase()} THREAT</span></span><div>{renderListItem(item, `${key}-${itemIndex}`)}</div></div> : renderListItem(item, `${key}-${itemIndex}`)}</li>;
      })}</List>;
    }
    if (token.type === 'code') return <pre key={key}><code>{token.text}</code></pre>;
    if (token.type === 'blockquote') return <blockquote key={key}>{(token.tokens || []).map((part, partIndex) => <p key={`${key}-${partIndex}`}>{renderInline(part.tokens, `${key}-${partIndex}`)}</p>)}</blockquote>;
    if (token.type === 'hr') return <hr key={key}/>;
    return null;
  })}</div>;
}
