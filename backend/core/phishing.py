"""Deterministic phishing indicators used by the Gmail message scanner."""
import re

RULES = [
    (r"\b(password|passcode|pin|credentials?)\s*(reset|expired|update|verify)\b", "Credential harvesting attempt", "CREDENTIAL_PHISHING"),
    (r"\b(bank\s*account|credit\s*card|ssn|social\s*security)\b", "Sensitive financial / PII request", "CREDENTIAL_PHISHING"),
    (r"\b(verify\s*your\s*identity|account\s*suspended|security\s*alert)\b", "Urgency / account suspension trigger", "CREDENTIAL_PHISHING"),
    (r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "Direct IP address URL found", "SUSPICIOUS_LINK"),
    (r"https?://[^\s]+\.(ru|xyz|top|work|click)/", "Suspicious TLD link detected", "SUSPICIOUS_LINK"),
]


def inspect_phishing_indicators(text: str):
    if not text:
        return []
    findings = []
    for pattern, description, kind in RULES:
        match = re.search(pattern, text, flags=re.I | re.S)
        if match:
            findings.append({"type": kind, "description": description, "matched_text": match.group(0)})
    return findings
