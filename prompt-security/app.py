import hashlib
import json
from pathlib import Path
import streamlit as st
from core.security import TaskPolicy
from core.uploads import ingest
from core.inspection import spans, highlighted_html
from approval_ui import start_run, render_approval, policy_snapshot, save
from workspace.simulated import SimWorkspace
from ui.theme import apply
from ui.components import html, esc, section, badge, scores, empty, actions, answer

st.set_page_config(page_title='Agent Security | Angry Birds',page_icon='◈',layout='wide',initial_sidebar_state='collapsed')
root=Path(__file__).resolve().parent
apply()
def protection_changed():
    previous=st.session_state.get('approval_run')
    if previous and previous.status=='awaiting_approval':
        previous.cancel();save(root,previous)
protection=st.toggle('Protection ON',value=True,key='protection_enabled',on_change=protection_changed,help='ON: enforce permissions and exact email approval. OFF: bypass these controls in the simulated workspace only.')
if not protection:
    st.warning('PROTECTION OFF · Permission checks and email approval are bypassed. Unauthorized actions may execute in the simulated workspace. No real emails are sent.')
html('<div class="brandbar"><div class="brand"><div class="brand-icon">◈</div><div><div class="brand-name">Agent Security</div><div class="eyebrow">Angry Birds / Genesis 2.0</div></div></div><div>'+badge('PROTECTION ON' if protection else 'PROTECTION OFF', '' if protection else 'red')+' &nbsp; '+badge('SIMULATED WORKSPACE','neutral')+'</div></div>')
with st.sidebar:
    st.markdown('### Agent Security')
    st.page_link('app.py',label='Security workspace')
    st.page_link('pages/1_Inbox_Defense.py',label='Inbox Defense')
    st.page_link('pages/2_Scripted_Gate_Tests.py',label='Scripted gate tests')
    st.caption('Live Gemini agent · simulated email delivery')

@st.dialog('Document reader',width='large')
def full_reader(doc):
    st.subheader(doc.get('title','Source document'))
    marks=spans(doc['content'])
    enabled=st.toggle('Highlight suspicious passages',value=True)
    html(highlighted_html(doc['content'],marks if enabled else []))
    st.caption('Extracted text · heuristic highlights are not confirmed vulnerabilities.')
    st.download_button('Download extracted text',doc['content'],'extracted-source.txt','text/plain')

workspace,history,evaluations=st.tabs(['Security workspace','Run history','Evaluation lab'])
with workspace:
    html('<div class="hero"><div><h1>Keep the task. Stop the detour.</h1><p>Inspect the source, constrain the agent, and follow every action.</p></div></div>')
    html('<div class="flow">'+''.join(f'<div class="flow-step"><span class="step-num">{i:02}</span><div><strong>{t}</strong><small>{s}</small></div></div>'+('<div class="arrow">→</div>' if i<4 else '') for i,t,s in [(1,'Source content','Untrusted input'),(2,'Agent proposal','Gemini tool call'),(3,'Permission gate' if protection else 'Gate bypassed','Check before execution' if protection else 'Simulation only'),(4,'Task result','Answer + action evidence')])+'</div>')
    imported=st.session_state.get('uploaded_documents',{})
    demo=SimWorkspace()._documents
    catalog={k:v for k,v in demo.items() if k!='confidential_budget'}
    catalog.update(imported)
    with st.expander('＋ Add files to the workspace · PDF, DOCX, ZIP and more',expanded=False):
        upcol,infocol=st.columns([2,1])
        with upcol:
            uploads=st.file_uploader('Drop multiple files here',type=['pdf','docx','txt','md','csv','json','log','eml','zip'],accept_multiple_files=True)
            if st.button('Import selected files',disabled=not uploads):
                with st.spinner('Extracting document text…'):
                    docs,errors=ingest([(u.name,u.getvalue()) for u in uploads])
                # Accumulate batches instead of discarding earlier uploaded files.
                merged=dict(imported)
                for sid,doc in docs.items():
                    if sid not in merged and len(merged)>=20:
                        errors.append({'file':doc.get('filename',sid),'reason':'Workspace limit: 20 uploaded documents. Clear files to import more.'})
                    elif sid not in merged and sum(len(d['content']) for d in merged.values())+len(doc['content'])>1_000_000:
                        errors.append({'file':doc.get('filename',sid),'reason':'Workspace extracted-text limit reached. Clear files before importing more.'})
                    else:merged[sid]=doc
                st.session_state['uploaded_documents']=merged;st.session_state['import_errors']=errors;st.rerun()
        with infocol:
            st.markdown('**Bring your own reports**')
            st.caption('PDF · DOCX · TXT · MD · CSV · JSON · LOG · EML · ZIP\n\n20 files · 10 MB each · 30 MB per import. Text extraction only; scanned PDFs need OCR. Files stay in this session; source text goes to Gemini when read.')
            if imported and st.button('Clear uploaded files'):
                previous=st.session_state.get('approval_run')
                if previous and previous.status=='awaiting_approval':previous.cancel();save(root,previous)
                st.session_state['uploaded_documents']={};st.session_state['import_errors']=[];st.rerun()
        for err in st.session_state.get('import_errors',[]):st.warning(err['file']+': '+err['reason'])
    left,right=st.columns([1.08,1],gap='large')
    with left:
        with st.container(border=True):
            section('01','Source workspace',badge(f'{len(imported)} UPLOADED','neutral'))
            group=st.radio('Source collection',['Uploaded files','Demo documents'],index=0 if imported else 1,horizontal=True,key='source_group_'+str(bool(imported)),label_visibility='collapsed')
            choices=list(imported) if group=='Uploaded files' else [k for k in catalog if k not in imported]
            selected=st.multiselect('Files the agent may read',choices,default=choices if group=='Uploaded files' else ['project_report_injected'],format_func=lambda k:catalog[k].get('title',k)+' · '+k[-6:],key='selection_'+group+'_'+hashlib.sha256('|'.join(choices).encode()).hexdigest()[:10])
            if selected:
                viewing=st.selectbox('Open document',selected,format_func=lambda k:catalog[k].get('title',k),label_visibility='collapsed')
                doc=catalog[viewing];text=doc['content'];findings=spans(text)
                html('<div class="source-title">'+esc(doc.get('title',viewing))+'</div><div class="source-meta">'+esc(doc.get('filename','DEMO SOURCE'))+f' · {len(text):,} characters · '+str(len(selected))+' sources in scope</div>')
                html(highlighted_html(text,findings))
                if findings:
                    html('<div class="signal-note"><b>'+str(len(findings))+' suspicious instruction signals</b><br>Highlighted text may try to redirect the agent. The gate checks actions separately.</div>')
                else:st.caption('No configured warning patterns matched. This is not a safety verdict.')
                a,b=st.columns(2)
                if a.button('Open full reader',width='stretch'):full_reader(doc)
                with b.popover('Inspect highlights',width='stretch'):
                    for f in findings:st.markdown('**'+f['signal']+'**');st.text(f['matched_text'])
                    if not findings:st.caption('No pattern matches.')
                with st.expander('Extraction details'):
                    st.caption('This is the text the agent receives. PDF page labels are retained. Original layout, images and DOCX headers/footers are not included. Highlights are heuristic and may miss attacks or flag quotations.')
                    st.download_button('Download source text',text,'source.txt','text/plain')
            else:empty('Your sources appear here','Choose demo documents or upload a report to begin.')
        with st.container(border=True):
            section('02','Task & permissions',badge('FROZEN AT RUN START','neutral'))
            task=st.text_area('What should the agent do?',value='Summarize the delayed milestones and their reasons. Name the source for each finding.',height=90)
            mode=st.radio('Allowed action',['Read and summarize','Read and prepare an email'],horizontal=True)
            email=mode=='Read and prepare an email'
            if email:
                r,s=st.columns(2)
                recipient=r.text_input('Authorized recipient',value='manager@example.com')
                subject=s.text_input('Required subject',value='Milestone update')
                st.caption('Ask for an email in your task. You review the exact draft before simulated sending.')
            else:recipient='manager@example.com';subject='Milestone update'
            tools={'read_doc'}
            if any(catalog[k].get('kind')=='email' for k in selected):tools.add('read_email')
            if email:tools.add('send_email')
            size=sum(len(catalog[k]['content']) for k in selected)
            invalid=email and (not recipient.strip() or '@' not in recipient or any(c in recipient+subject for c in '\r\n\x00') or not subject.strip() or len(subject)>200 or len(recipient)>254)
            if invalid:st.error('Enter a valid recipient and single-line subject.')
            if size>300_000:st.error('Select fewer sources: maximum 300,000 characters per task.')
            policy=TaskPolicy(frozenset(tools),frozenset(selected),frozenset({recipient.strip()} if email and not invalid else set()),max_emails=1 if email else 0,required_subject=subject.strip() if email and not invalid else None,require_source_read=True)
            source_id=selected[0] if selected else '';snapshot=policy_snapshot(policy)
            html('<div class="scope"><span>'+str(len(selected))+' allowed sources</span><span>'+('Other sources blocked' if protection else 'Scope NOT enforced')+'</span><span>'+(('1 email · exact recipient · approval' if email else 'Email disabled') if protection else 'Email restrictions bypassed')+'</span></div>')
            run_now=st.button('Run protected task' if protection else 'Run unprotected simulation',type='primary',width='stretch',disabled=not selected or not task.strip() or invalid or size>300_000)
            if run_now:start_run(root,task,source_id,policy,documents={k:catalog[k] for k in selected},protection_enabled=protection)
    with right:
        with st.container(border=True):
            run=st.session_state.get('last_run')
            status=run.get('status','not run') if run else 'not run'
            section('03','Live action trace',badge(status.replace('_',' ').upper(),'amber' if status=='awaiting_approval' else ('neutral' if not run else '')))
            if run:
                if run['document']!=source_id or run['task']!=task or run.get('policy')!=snapshot or run.get('protection_enabled',True)!=protection:st.warning('Showing a previous run. Run the current task to update this panel.')
                st.caption('Recorded run: Protection '+('ON' if run.get('protection_enabled',True) else 'OFF')+' · simulated tools')
                audit=run.get('audit',[])
                scores([('Actions executed',sum(bool(e.get('executed')) for e in audit)),('Blocked / denied',sum(e.get('decision') in ('BLOCK','DENY') for e in audit)),('Simulated emails',len(run.get('outbox',[])))])
                actions(audit)
                if not audit:empty('No tool actions recorded','The request has not produced an executable tool call.')
                if audit and not any(e.get('decision') in ('BLOCK','DENY') for e in audit):st.caption('No blocked action in this run. A clean outcome alone does not prove the gate stopped an attack.')
                render_approval(root,task,source_id,snapshot)
                outbox=run.get('outbox',[])
                if outbox:
                    html('<div class="answer-label">SIMULATED OUTBOX · '+str(len(outbox))+' EMAIL(S)</div>')
                    for message in outbox:
                        html('<div class="mail-head"><b>To:</b> '+esc(message.get('recipient',''))+'<br><b>Subject:</b> '+esc(message.get('subject',''))+'</div><div class="answer-box">'+esc(message.get('body',''))+'</div>')
                if run.get('error'):st.error(run['error'])
                if run.get('answer'):answer(run['answer'])
                elif status=='awaiting_approval':st.caption('Agent paused at the email approval step.')
                elif status=='completed':st.caption('Run completed without a final text answer.')
                st.caption('Run '+run['run_id'][:8]+' · '+str(len(run.get('sources',{})))+' sources read')
                if st.session_state.get('save_error'):st.warning('Local log could not be saved. Download the evidence below.')
                with st.expander('Inspect run evidence'):
                    st.json({k:run.get(k) for k in ('policy','audit','outbox','sources','source_catalog','approvals','model','requests')},expanded=False)
                    st.download_button('Download run evidence',json.dumps(run,indent=2),run['run_id']+'.json','application/json',key='run_download_'+run['run_id']+'_'+status)
            else:
                scores([('Actions executed','—'),('Blocked / denied','—'),('Simulated emails','—')])
                empty('Ready to trace the agent','Run a task to see real tool calls, policy decisions and the final response here.')
                html('<div class="answer-label">WHAT THIS RUN WILL SHOW</div><div class="action-row"><div class="action-number">1</div><div class="action-main"><strong>Which source was read</strong><div class="action-reason">Only the selected files are authorized.</div></div></div><div class="action-row"><div class="action-number">2</div><div class="action-main"><strong>What the agent tried to do</strong><div class="action-reason">Every tool proposal receives a policy decision.</div></div></div><div class="action-row"><div class="action-number">3</div><div class="action-main"><strong>What actually executed</strong><div class="action-reason">The trace separates attempts from completed actions.</div></div></div>')
        with st.expander('Demo controls & independent checks'):
            st.caption('Use scripted tests for deterministic gate evidence. Use live runs to assess the agent. These are separate types of evidence.')
            st.page_link('pages/2_Scripted_Gate_Tests.py',label='Open scripted gate tests')
            st.page_link('pages/1_Inbox_Defense.py',label='Open inbox scenarios')
with history:
    st.subheader('Run history')
    records=[]
    for path in sorted((root/'logs').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:100]:
        try:
            r=json.loads(path.read_text(encoding='utf-8-sig'))
            if r.get('run_type')=='live_agent':records.append(r)
        except (OSError,ValueError):continue
    if records:
        i=st.selectbox('Saved run',range(len(records)),format_func=lambda i:records[i].get('recorded_at','')+' · '+records[i]['status']+' · '+records[i]['task'][:65])
        r=records[i];l,c=st.columns(2)
        with l:answer(r.get('answer') or r.get('error') or 'No final answer recorded.')
        with c:actions(r.get('audit',[]))
        with st.expander('Raw evidence'):st.json(r,expanded=False)
        st.download_button('Download saved run',json.dumps(r,indent=2),r['run_id']+'.json','application/json')
    else:empty('No saved runs yet','Your completed and paused runs will appear here.')
with evaluations:
    from batch_view import render_batches
    from evaluation_view import render_saved_results
    from comparison import render_comparison
    st.subheader('Evaluation lab')
    st.caption('Measure behavior with paired runs. Review answer correctness before claiming success.')
    with st.expander('Batch results & manual reviews'):render_batches(root)
    with st.expander('Saved live comparisons'):render_saved_results(root)
    with st.expander('Compare current task · gate ON / OFF'):
        st.caption('Two live runs with identical task and source text. Human approval is disabled for evaluation. Email remains simulated.')
        if selected and not invalid and size<=300_000:render_comparison(root,task,source_id,policy,documents={k:catalog[k] for k in selected})
        else:st.info('Select valid sources and permissions first.')
html('<div class="footer"><span>GENESIS 2.0 · TEAM ANGRY BIRDS</span><span>Heuristic inspection · Deterministic permissions · Exact-call approval</span></div>')
