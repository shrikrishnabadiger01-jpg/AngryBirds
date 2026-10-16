from html import escape
import streamlit as st

def html(value):st.markdown(value,unsafe_allow_html=True)
def esc(value):return escape(str(value))
def section(number,title,badge=''):
    html(f'<div class="section-top"><div><span class="section-id">{number} / </span><span class="section-title">{esc(title)}</span></div>{badge}</div>')
def badge(text,tone=''):
    return f'<span class="badge {tone}">{esc(text)}</span>'
def scores(values):
    html('<div class="score-strip">'+''.join(f'<div class="score"><b>{esc(v)}</b><small>{esc(k)}</small></div>' for k,v in values)+'</div>')
def empty(title,body):
    html(f'<div class="empty-state"><div class="empty-icon">◇</div><strong>{esc(title)}</strong><p>{esc(body)}</p></div>')
def actions(audit):
    for i,e in enumerate(audit,1):
        decision=e.get('decision','UNKNOWN');args=e.get('arguments',{})
        title={'read_doc':'Read document','read_email':'Read email','send_email':'Send email'}.get(e.get('tool'),e.get('tool','Tool action'))
        target=args.get('doc_id') or args.get('email_id') or args.get('recipient') or 'Tool request'
        tone='red' if decision in ('BLOCK','DENY') else ('amber' if decision=='BYPASS' else '')
        html(f'<div class="action-row"><div class="action-number">{i:02}</div><div class="action-main"><div class="action-head"><strong>{esc(title)}</strong>{badge(decision,tone)}</div><div class="action-target">{esc(target)}</div><div class="action-reason">{esc(e.get("reason",""))} · {"Executed" if e.get("executed") else "Not executed"}</div></div></div>')
def answer(text):
    html('<div class="answer-label">AGENT RESPONSE</div><div class="answer-box">'+esc(text)+'</div>')
