"""
AI Agent Security — Email Router & Security Analysis Pipeline
Handles listing real emails from Gmail API and running security analysis.
Treats all email content strictly as untrusted external data.
"""

import re
import json
import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db, AuditLog
from app.services import gmail_service
from core.inspector import inspect_content

router = APIRouter(prefix="/api/emails", tags=["Emails"])


class AnalyzeEmailRequest(BaseModel):
    email_id: Optional[str] = None
    subject: str = ""
    body: str = ""
    sender: str = "unknown@domain.com"
    recipient: Optional[str] = None


@router.get("")
async def list_emails(
    max_results: int = Query(15, ge=1, le=50),
    page_token: Optional[str] = None,
    query: Optional[str] = None,
):
    """
    List real messages from the authorized user's Gmail inbox.
    Never returns fake or mock emails.
    """
    status = gmail_service.get_connection_status()
    if not status["connected"]:
        return {
            "connected": False,
            "emails": [],
            "configured": status["configured"],
            "message": "Gmail is not connected. Authenticate via Google OAuth to inspect real inbox messages.",
        }

    try:
        data = gmail_service.fetch_emails(
            max_results=max_results,
            page_token=page_token,
            query=query,
        )
        return {
            "connected": True,
            "emails": data.get("emails", []),
            "next_page_token": data.get("next_page_token"),
            "connected_email": data.get("connected_email"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Gmail inbox: {str(e)}")


@router.post("/analyze")
async def analyze_email_security(req: AnalyzeEmailRequest, db: Session = Depends(get_db)):
    """
    Run security analysis on a real Gmail message.
    Inspects for prompt injection, phishing triggers, and runtime policy violations.
    Records every security decision in the SQLite AuditLog.
    """
    text_to_scan = f"{req.subject}\n\n{req.body}"

    # 1. Prompt Injection Pattern Inspector
    injection_findings = inspect_content(text_to_scan)

    # 2. Phishing & Malicious Indicator Rules
    indicators = []

    # Credential Harvesting / Account Takeover
    cred_patterns = [
        (r"\b(password|passcode|pin|credentials?)\s*(reset|expired|update|verify)\b", "Credential harvesting attempt"),
        (r"\b(bank\s*account|credit\s*card|ssn|social\s*security)\b", "Sensitive financial / PII request"),
        (r"\b(verify\s*your\s*identity|account\s*suspended|security\s*alert)\b", "Urgency / account suspension trigger"),
    ]
    for pattern, desc in cred_patterns:
        if re.search(pattern, text_to_scan, re.I):
            indicators.append({"type": "CREDENTIAL_PHISHING", "description": desc})

    # Malicious URLs / IP Links
    url_patterns = [
        (r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "Direct IP address URL found"),
        (r"https?://[^\s]+\.(ru|xyz|top|work|click)/", "Suspicious TLD link detected"),
    ]
    for pattern, desc in url_patterns:
        if re.search(pattern, text_to_scan, re.I):
            indicators.append({"type": "SUSPICIOUS_LINK", "description": desc})

    # Prompt Injection & Directive Overrides
    for finding in injection_findings:
        indicators.append({
            "type": "PROMPT_INJECTION",
            "description": f"Directive detected: '{finding['signal']}' in matched text: '{finding['matched_text']}'"
        })

    # 3. Decision Determination
    has_injection = len(injection_findings) > 0
    has_phishing = any(i["type"] == "CREDENTIAL_PHISHING" for i in indicators)
    has_suspicious_url = any(i["type"] == "SUSPICIOUS_LINK" for i in indicators)

    if has_injection:
        decision = "BLOCK"
        threat_level = "critical"
        reason = "Blocked: High-risk prompt injection signals detected aiming to hijack agent execution."
    elif has_phishing or has_suspicious_url:
        decision = "BLOCK"
        threat_level = "high"
        reason = "Blocked: Malicious phishing / credential harvesting indicators detected."
    elif len(indicators) > 0:
        decision = "SUSPICIOUS"
        threat_level = "medium"
        reason = "Warning: Moderate risk indicators identified. Treat with caution."
    else:
        decision = "ALLOW"
        threat_level = "safe"
        reason = "No malicious directives or prompt injection patterns detected."

    # 4. Save Audit Log to SQLite
    try:
        audit_entry = AuditLog(
            timestamp=datetime.datetime.utcnow(),
            event_type="EMAIL_SECURITY_SCAN",
            email_id=req.email_id or "adhoc",
            sender=req.sender,
            subject=req.subject,
            decision=decision,
            reason=reason,
            threat_level=threat_level,
            raw_indicators=json.dumps(indicators),
        )
        db.add(audit_entry)
        db.commit()
    except Exception as db_err:
        print(f"[IgnisGuard] Database audit log error: {db_err}")

    return {
        "email_id": req.email_id,
        "sender": req.sender,
        "subject": req.subject,
        "decision": decision,
        "threat_level": threat_level,
        "reason": reason,
        "prompt_injection_signals": injection_findings,
        "indicators": indicators,
        "scanned_at": datetime.datetime.utcnow().isoformat() + "Z",
        "untrusted_content_notice": (
            "Email data is treated strictly as untrusted external content. "
            "Instructions within this email are prohibited from triggering system actions."
        ),
    }
