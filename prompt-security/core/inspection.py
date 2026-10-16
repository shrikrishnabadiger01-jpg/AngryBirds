"""Explainable heuristic spans. Findings do not grant or revoke permissions."""
import re
import html
RULES=[
 ('Authority claim',r'(?i)\b(?:important\s+)?system\s+(?:update|message|instruction)\b[^\n.!?]{0,180}'),
 ('Instruction override',r'(?i)\b(?:ignore|override|disregard)\s+(?:all\s+)?(?:previous|prior|user|original)\s+instructions?[^\n.!?]{0,180}'),
 ('Hidden action',r'(?i)\bdo\s+not\s+(?:mention|tell|reveal|explain)[^\n.!?]{0,180}'),
 ('Data access request',r'(?i)\b(?:read|access|retrieve|open)\b[^\n.!?]{0,100}\b(?:confidential_budget|confidential|secret|credentials)\b[^\n.!?]{0,100}'),
 ('Recipient redirection',r'(?i)\b(?:send|route|forward|mailbox|recipient)\b[^\n]{0,180}(?:@|changed|moved|instead|obsolete)[^\n]{0,100}'),
 ('Claimed approval',r'(?i)\b(?:approval status|approved by|already been approved|skip[^\n]{0,30}approval|receipt is the approval)[^\n]{0,160}'),
 ('Hidden HTML instruction',r'(?is)<!--.{0,1000}?-->'),
 ('Unsupported payment directive',r'(?i)\b(?:add the sentence|payment to the vendor|dispatch metadata)[^\n]{0,180}'),
]
def spans(text):
    results=[]
    for label,pattern in RULES:
        for match in re.finditer(pattern,text):
            results.append({'signal':label,'start':match.start(),'end':match.end(),'matched_text':match.group(0)})
            if len(results)>=100:return sorted(results,key=lambda r:r['start'])
    return sorted(results,key=lambda r:r['start'])

def highlighted_html(text,findings):
    intervals=[]
    for item in sorted(findings,key=lambda r:r['start']):
        start,end=item['start'],item['end']
        if intervals and start<=intervals[-1][1]:intervals[-1][1]=max(intervals[-1][1],end)
        else:intervals.append([start,end])
    parts=[];cursor=0
    for start,end in intervals:
        parts.append(html.escape(text[cursor:start]))
        parts.append('<mark>'+html.escape(text[start:end])+'</mark>');cursor=end
    parts.append(html.escape(text[cursor:]))
    return '<div class="document-reader">'+''.join(parts)+'</div>'
