import json
from datetime import datetime, timezone
import streamlit as st
from dotenv import dotenv_values
from agent.approval import ApprovalRun
from workspace.simulated import SimWorkspace


def policy_snapshot(policy):
    return {
        'allowed_tools': sorted(policy.allowed_tools),
        'allowed_documents': sorted(policy.allowed_documents),
        'allowed_recipients': sorted(policy.allowed_recipients),
        'max_emails': policy.max_emails,
        'required_subject': policy.required_subject,
    }


def save(root, session):
    record = dict(
        run_id=session.run_id,
        recorded_at=datetime.now(timezone.utc).isoformat(),
        run_type='live_agent', approval_required=True,
        status=session.status, document=session.document_id,
        task=session.task, policy=policy_snapshot(session.policy),
        answer=session.answer, error=session.error,
        audit=session.workspace.audit, outbox=session.workspace.outbox,
        approvals=list(session.approvals),
        pending_email=session.proposal(),
    )
    st.session_state['last_run'] = record
    try:
        (root/'logs').mkdir(exist_ok=True)
        (root/'logs'/f'{session.run_id}.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
        st.session_state['save_error'] = None
    except OSError as exc:
        st.session_state['save_error'] = str(exc)


def invoke(root, session, action):
    try:
        with st.spinner('Running agent and checking permissions…'):
            action()
    except Exception as exc:
        key = dotenv_values(root/'.env').get('GEMINI_API_KEY')
        error = f'{type(exc).__name__}: {exc}'
        session.error = error.replace(key, '[REDACTED]') if key else error
        session.cancel()
        session.status = 'error'
    save(root, session)


def start_run(root, task, document_id, policy):
    previous = st.session_state.get('approval_run')
    if previous and previous.status == 'awaiting_approval':
        previous.cancel()
        save(root, previous)
    session = ApprovalRun(task, document_id, policy, SimWorkspace())
    st.session_state['approval_run'] = session
    invoke(root, session, session.start)


def render_approval(root, task, document_id, snapshot):
    session = st.session_state.get('approval_run')
    if not session or session.status != 'awaiting_approval':
        return
    changed = task != session.task or document_id != session.document_id or snapshot != policy_snapshot(session.policy)
    st.warning('Email waiting for your approval. Nothing has been sent for this proposal.')
    st.caption('Review the exact email below. Approval expires after 10 minutes. Denial prevents further email sends in this run.')
    proposal = session.proposal()
    st.text('To: ' + proposal['recipient'])
    st.text('Subject: ' + proposal['subject'])
    st.text(proposal['body'])
    if changed:
        st.info('Inputs changed. Restore the original inputs to approve, or deny this proposal and start a new run.')
    approve_col, deny_col = st.columns(2)
    approve = approve_col.button('Approve this email', type='primary', disabled=changed, key='approve_'+session.run_id)
    deny = deny_col.button('Deny email', key='deny_'+session.run_id)
    if approve or deny:
        token = session.pending['token']
        invoke(root, session, lambda: session.resolve(token, approve))
        st.rerun()
