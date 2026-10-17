"""Deterministic security classification for untrusted email content."""

from core.inspector import inspect_content
from core.phishing import inspect_phishing_indicators


def analyze_email_content(subject: str = "", body: str = "") -> dict:
    text_to_scan = f"{subject}\n\n{body}"
    injection_findings = inspect_content(text_to_scan)
    indicators = inspect_phishing_indicators(text_to_scan)

    for finding in injection_findings:
        indicators.append({
            "type": "PROMPT_INJECTION",
            "description": (
                f"Directive detected: '{finding['signal']}' in matched text: "
                f"'{finding['matched_text']}'"
            ),
            "matched_text": finding["matched_text"],
        })

    has_injection = bool(injection_findings)
    has_phishing = any(item["type"] == "CREDENTIAL_PHISHING" for item in indicators)
    has_suspicious_url = any(item["type"] == "SUSPICIOUS_LINK" for item in indicators)

    if has_injection:
        decision = "BLOCK"
        threat_level = "critical"
        reason = "High-risk prompt injection signals detected; embedded directives must not be followed."
    elif has_phishing or has_suspicious_url:
        decision = "BLOCK"
        threat_level = "high"
        reason = "Phishing or suspicious-link indicators detected; treat the message as untrusted."
    elif indicators:
        decision = "SUSPICIOUS"
        threat_level = "medium"
        reason = "Moderate risk indicators detected; treat the message with caution."
    else:
        decision = "ALLOW"
        threat_level = "safe"
        reason = "No known phishing or prompt-injection signals detected."

    return {
        "decision": decision,
        "threat_level": threat_level,
        "reason": reason,
        "prompt_injection_signals": injection_findings,
        "indicators": indicators,
    }
