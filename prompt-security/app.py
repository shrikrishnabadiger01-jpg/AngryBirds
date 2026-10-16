import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import streamlit as st
from dotenv import dotenv_values
from approval_ui import start_run, render_approval, policy_snapshot
from core.inspector import inspect_content
from core.security import TaskPolicy
from workspace.simulated import SimWorkspace

st.set_page_config(page_title='AI Agent Security', layout='wide', initial_sidebar_state='collapsed')
root = Path(__file__).resolve().parent
documents = json.loads((root/'data/documents.json').read_text(encoding='utf-8-sig'))
st.markdown('''<style>
.stApp {background:#fcfdfd;color:#111b29;}
.block-container {max-width:1280px;padding-top:2rem;padding-bottom:2rem;}
h1,h2,h3 {color:#101926;letter-spacing:-.025em;}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stSidebar"] {background:#f3f6f6;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:12px;}
.stButton>button[kind="primary"] {background:#146264;border-color:#146264;color:white;min-height:48px;}
.stButton>button[kind="primary"]:hover {background:#104f51;border-color:#104f51;color:white;}
[data-baseweb="textarea"] textarea,[data-baseweb="select"] {font-size:16px;}
[data-baseweb="tab-list"] {gap:32px;}
[data-baseweb="tab-highlight"] {background:#146264;}
.hero {text-align:center;padding:34px 0 32px;}
.hero h1 {font-size:40px;margin:0 0 8px;font-weight:650;}
.hero p {color:#69717d;font-size:19px;margin:0;}
.brand {font-size:23px;font-weight:700;line-height:1.2;}
.brand small {display:block;font-size:11px;color:#75808c;letter-spacing:.06em;margin-top:6px;font-weight:400;}
.demo {text-align:right;color:#69717d;font-size:13px;padding-top:8px;}
.footer {text-align:center;color:#7a838c;font-size:13px;margin:30px 0;}
@media(max-width:700px) {.hero h1 {font-size:29px;}.hero {padding:20px 0;}}
</style>''', unsafe_allow_html=True)
brand, badge = st.columns([3,1])
with brand:
    st.markdown('<div class="brand">AI Agent Security<small>GENESIS 2.0 · TEAM ANGRY BIRDS</small></div>', unsafe_allow_html=True)
with badge:
    st.markdown('<div class="demo">Demo workspace</div>', unsafe_allow_html=True)
workspace_tab, evaluation_tab = st.tabs(['Workspace', 'Evaluations'])
with workspace_tab:
    st.markdown('<div class="hero"><h1>Give your agent a task.</h1><p>You set the permissions. We check every action.</p></div>', unsafe_allow_html=True)
    left, right = st.columns([0.39,0.61], gap='medium')
    with left:
        with st.container(border=True):
            st.subheader('Your task')
            document_id = st.selectbox('Document', [d for d in documents if d != 'confidential_budget'], format_func=lambda d: d.replace('_',' ').capitalize(), label_visibility='collapsed')
            task = st.text_area('Task for agent', 'Summarize the delayed milestones and their reasons.', height=145, label_visibility='collapsed')
            st.divider()
            st.markdown('**Permissions**')
            st.checkbox('Read selected document', value=True, disabled=True)
            allow_email = st.checkbox('Send simulated email to manager', value=False, help='Authorized recipient: manager@example.com')
            if allow_email:
                st.caption('Recipient: manager@example.com. Include the email request in your task.')
            st.caption('Permissions stay fixed. Emails require approval before sending.')
            policy = TaskPolicy(frozenset({'read_doc','send_email'} if allow_email else {'read_doc'}), frozenset({document_id}), frozenset({'manager@example.com'} if allow_email else set()))
            snapshot = policy_snapshot(policy)
            clicked = st.button('Run agent', type='primary', use_container_width=True)
    if clicked:
        if not task.strip():
            st.warning('Enter a task first.')
        else:
            start_run(root, task, document_id, policy)
    with right:
        with st.container(border=True):
            st.subheader('Result')
            render_approval(root, task, document_id, snapshot)
            run = st.session_state.get('last_run')
            if not run:
                st.caption('Ready when you are')
                st.write('Choose a document and run your task. The agent’s response will appear here.')
            else:
                if run['document'] != document_id or run['task'] != task or run.get('policy') != snapshot:
                    st.warning('Inputs changed. This result belongs to the previous run.')
                if run.get('error'):
                    st.error('Run incomplete. Review the error below.')
                    with st.expander('Error details'):
                        st.code(run['error'], language='text')
                elif run.get('status') == 'awaiting_approval':
                    st.caption('Paused · awaiting email approval')
                elif run.get('status') == 'cancelled':
                    st.caption('Run cancelled')
                else:
                    st.caption('✓ Completed · ' + run['document'].replace('_',' '))
                if run.get('answer'):
                    st.markdown(run['answer'])
            st.divider()
            with st.expander('View security audit'):
                if run:
                    st.caption('Recorded task: ' + run['task'])
                    st.json(run['policy'])
                    if run['audit']:
                        st.dataframe([{'Tool': e['tool'], 'Arguments': json.dumps(e['arguments']), 'Decision': e['decision'], 'Reason': e['reason'], 'Executed': e['executed']} for e in run['audit']], hide_index=True, use_container_width=True)
                    else:
                        st.write('No tool calls recorded.')
                    st.markdown('**Simulated outbox**')
                    st.json(run['outbox'])
                else:
                    st.write('No run recorded yet.')
            with st.expander('Inspect selected document'):
                st.caption('Current selection. External content is untrusted. Pattern warnings do not change permissions or automatically block reads.')
                content = documents[document_id]['content']
                findings = inspect_content(content)
                if findings:
                    st.warning(f'{len(findings)} suspicious instruction signals found.')
                    st.dataframe(findings, hide_index=True, use_container_width=True)
                else:
                    st.caption('No configured patterns matched. This is not a safety guarantee.')
                st.text(content)
            if run:
                if st.session_state.get('save_error'):
                    st.warning('Local log could not be saved. Download the run below.')
                st.download_button('Download run', json.dumps(run, indent=2), file_name=run.get('run_id','run')+'.json', mime='application/json')
    st.markdown('<div class="footer">Simulated tools only. No real emails are sent.</div>', unsafe_allow_html=True)
with evaluation_tab:
    from evaluation_view import render_saved_results
    from comparison import render_comparison
    render_saved_results(root)
    st.info('Evaluation runs are noninteractive: they do not request human approval. They measure backend policy enforcement. Scripted tests remain separate in the sidebar.')
    render_comparison(root, task, document_id, policy)
