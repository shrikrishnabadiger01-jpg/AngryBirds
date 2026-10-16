import re

RULES = [
    (
        "Claims system authority",
        r"\b(?:important\s+)?system\s+update\b",
    ),
    (
        "Requests instruction override",
        r"\bignore\s+(?:all\s+)?(?:previous|prior)\s+instructions\b",
    ),
    (
        "Requests secrecy from the user",
        r"\bdo\s+not\s+(?:mention|tell|reveal)\b",
    ),
    (
        "Requests sending document contents",
        r"\bsend\b.{0,100}\bcontents\b",
    ),
]


def inspect_content(text):
    findings = []
    for label, pattern in RULES:
        match = re.search(pattern, text, flags=re.I | re.S)
        if match:
            findings.append({
                "signal": label,
                "matched_text": match.group(0),
            })
    return findings
