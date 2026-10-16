"""Offline evidence browser. Never invokes the agent or a provider."""
import hashlib
import io
import csv
import json
import zipfile
from datetime import datetime, timezone
import streamlit as st


def load_batches(root):
    records, errors = [], []
    for path in sorted((root/'logs'/'eval_batches').glob('*/*.json')):
        try:
            raw = path.read_bytes()
            record = json.loads(raw.decode('utf-8-sig'))
            if record.get('run_type') != 'live_evaluation':
                continue
            for field in ('run_id','scenario_id','mode','status','security_outcome','audit','outbox'):
                if field not in record:
                    raise ValueError('Missing '+field)
            record['_digest'] = hashlib.sha256(raw).hexdigest()
            record['_file'] = str(path.relative_to(root))
            record['_review'] = None
            review_path = root/'logs'/'reviews'/(path.stem+'.json')
            if review_path.exists():
                review = json.loads(review_path.read_text())
                if review.get('evidence_sha256') == record['_digest']:
                    record['_review'] = review
            records.append(record)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f'{path.name}: {type(exc).__name__}')
    return records, errors


def render_batches(root):
    st.subheader('Batch evaluation evidence')
    st.caption('Synthetic scenarios. Gate OFF keeps the same model instructions; backend permissions are bypassed. Human approvals are disabled in both evaluation modes.')
    st.button('Refresh batch results')
    records, errors = load_batches(root)
    if errors:
        st.warning(f'{len(errors)} evidence files could not be loaded.')
        with st.expander('File errors'):
            st.write(errors)
    if not records:
        st.info('Run the evaluation command in the included README. Saved batch results will appear here.')
        return
    batches = sorted({r.get('batch_id','legacy') for r in records})
    selected = st.selectbox('Batch', ['All batches']+batches)
    mode = st.selectbox('Batch mode', ['Both','Gate ON','Gate OFF'])
    shown = [r for r in records if (selected=='All batches' or r.get('batch_id','legacy')==selected) and (mode=='Both' or r['mode']==mode)]
    a,b,c = st.columns(3)
    a.metric('Recorded runs',len(shown))
    b.metric('Completed',sum(r['status']=='completed' for r in shown))
    c.metric('Errors / incomplete',sum(r['status']!='completed' for r in shown))
    summary = []
    for label in ('Gate ON','Gate OFF'):
        group = [r for r in shown if r['mode']==label]
        attacks = [r for r in group if r.get('attack_scenario') is True]
        completed = [r for r in attacks if r['status']=='completed']
        violations = sum(r['security_outcome']=='violation' for r in completed)
        reviews = [r['_review'] for r in group if r['_review'] and r['status']=='completed']
        summary.append({'Mode':label, 'Completed attack runs':len(completed),
                        'Observed violations / completed attacks':f'{violations}/{len(completed)}' if completed else 'Not measured',
                        'Attack errors / incomplete':sum(r['status']!='completed' for r in attacks),
                        'Violations in incomplete attack runs':sum(r['status']!='completed' and r['security_outcome']=='violation' for r in attacks),
                        'Task passes / reviewed completed runs':f"{sum(r['verdict']=='pass' for r in reviews)}/{len(reviews)}" if reviews else 'Not reviewed'})
    st.dataframe(summary,hide_index=True,use_container_width=True)
    st.caption('These counts apply only to the displayed synthetic runs. Old logs without attack labels are excluded from attack denominators. Failures remain visible; no-violation does not imply general security. Utility is human-reviewed.')
    rows = [{'Scenario':r['scenario_id'],'Mode':r['mode'],'Status':r['status'], 'Security':r['security_outcome'],
             'Utility':r['_review']['verdict'] if r['_review'] else 'unreviewed','Seconds':r.get('duration_seconds'),
             'Blocked':sum(e.get('decision')=='BLOCK' for e in r['audit']), 'Emails':len(r['outbox']),
             'Run ID':r['run_id']} for r in shown]
    st.dataframe(rows,hide_index=True,use_container_width=True)
    if not shown:
        return
    buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=list(rows[0]));writer.writeheader()
    for row in rows:
        writer.writerow({k:"'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v for k,v in row.items()})
    st.download_button('Download batch table',buf.getvalue(),'batch-evaluations.csv','text/csv')
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for record in shown:
            bundle.writestr(record['_file'], (root/record['_file']).read_bytes())
            if record['_review']:
                bundle.writestr('reviews/'+record['run_id']+'.json', json.dumps(record['_review'], indent=2))
    st.download_button('Download displayed evidence ZIP', archive.getvalue(), 'evaluation-evidence.zip', 'application/zip')
    with st.expander('Review one run against its rubric'):
        index=st.selectbox('Evidence run',range(len(shown)),format_func=lambda i:shown[i]['scenario_id']+' · '+shown[i]['mode']+' · '+shown[i]['run_id'][:8])
        record=shown[index]
        st.write(record.get('rubric','Review task correctness manually.'))
        st.text(record.get('answer') or '(no final answer)')
        if record.get('error'):
            st.error(record['error'])
        st.json({k:record.get(k) for k in ('task','policy','audit','outbox','utility_hints','model','requests','sources')})
        verdict=st.radio('Task correctness', ['pass','fail'],key='verdict_'+record['run_id'])
        note=st.text_input('Reason for your review',key='note_'+record['run_id'])
        if st.button('Save review',disabled=record['status']!='completed'):
            if not note.strip():
                st.warning('Add a short reason before saving.')
            else:
                target=root/'logs'/'reviews';target.mkdir(parents=True,exist_ok=True)
                review={'run_id':record['run_id'],'evidence_sha256':record['_digest'],'verdict':verdict,'note':note,'reviewed_at':datetime.now(timezone.utc).isoformat()}
                path=target/(record['run_id']+'.json');tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(review,indent=2));tmp.replace(path)
                st.rerun()
