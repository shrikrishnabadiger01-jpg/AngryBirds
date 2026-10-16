import re

RULES = [
    (
        "Claims system authority",
        r"\b(?:important\s+)?system\s+update\b",
    ),
    (
        "Claims developer or administrator authority",
        r"\b(?:developer|administrator|admin)\s+(?:message|notice|instruction|override)\b",
    ),
    (
        "Requests instruction override",
        r"\b(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|prior|earlier)\s+instructions\b",
    ),
    (
        "Requests secrecy from the user",
        r"\bdo\s+not\s+(?:mention|tell|reveal)\b",
    ),
    (
        "Requests sending document contents",
        r"\b(?:send|forward|email|upload|share|exfiltrat\w*)\b.{0,160}\b(?:contents?|documents?|files?|data|records?)\b",
    ),
    (
        "Attempts to change an authorized recipient",
        r"\b(?:change|replace|redirect|use|send\s+to)\b.{0,100}\b(?:recipient|address|mailbox|email)\b",
    ),
    (
        "Requests access to secrets or credentials",
        r"\b(?:reveal|print|read|export|send|exfiltrat\w*)\b.{0,100}\b(?:passwords?|api\s*keys?|tokens?|credentials?|secrets?|private\s+keys?)\b",
    ),
    (
        "Attempts to bypass a security control",
        r"\b(?:bypass|disable|ignore|override|turn\s+off)\b.{0,80}\b(?:security|policy|approval|permission|safety|filter|gate)\b",
    ),
    (
        "Requests access to unrelated confidential data",
        r"\b(?:read|open|retrieve|access|copy|search)\b.{0,100}\b(?:confidential|private|restricted|secret)\b.{0,80}\b(?:file|document|data|budget|record)s?\b",
    ),
    (
        "Requests an unapproved external action",
        r"\b(?:run|execute|download|install|delete|transfer|pay)\b.{0,100}\b(?:script|command|file|funds|payment|account)\b",
    ),
]


def inspect_content(text: str):
    findings = []
    if not text:
        return findings
    for label, pattern in RULES:
        match = re.search(pattern, text, flags=re.I | re.S)
        if match:
            findings.append({
                "signal": label,
                "matched_text": match.group(0),
            })
    return findings
