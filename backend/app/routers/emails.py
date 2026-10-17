"""
AI Agent Security — Email Router & Security Analysis Pipeline
Handles listing real emails from Gmail API and running security analysis.
Treats all email content strictly as untrusted external data.
"""

import json
import datetime
import asyncio
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db, AuditLog
from app.auth import require_roles
from app.services import gmail_service
from app.services.email_summary import summarize_suspicious_email
from core.email_security import analyze_email_content

router = APIRouter(prefix="/api/emails", tags=["Emails"])


class AnalyzeEmailRequest(BaseModel):
    email_id: Optional[str] = None
    subject: str = ""
    body: str = ""
    sender: str = "unknown@domain.com"
    recipient: Optional[str] = None


@router.get("", dependencies=[require_roles("admin", "operator", "auditor")])
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


@router.post("/analyze", dependencies=[require_roles("admin", "operator")])
async def analyze_email_security(req: AnalyzeEmailRequest, db: Session = Depends(get_db)):
    """
    Run security analysis on a real Gmail message.
    Inspects for prompt injection, phishing triggers, and runtime policy violations.
    Records every security decision in the SQLite AuditLog.
    """
    analysis = analyze_email_content(req.subject, req.body)
    decision = analysis["decision"]
    threat_level = analysis["threat_level"]
    reason = analysis["reason"]
    injection_findings = analysis["prompt_injection_signals"]
    indicators = analysis["indicators"]

    # Summarize suspicious mail as untrusted content; the model cannot act on it.
    email_summary = None
    if decision != "ALLOW" or threat_level != "safe":
        email_summary = await asyncio.to_thread(
            summarize_suspicious_email, req.subject, req.body
        )

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
        "summary": email_summary,
        "prompt_injection_signals": injection_findings,
        "indicators": indicators,
        "scanned_at": datetime.datetime.utcnow().isoformat() + "Z",
        "untrusted_content_notice": (
            "Email data is treated strictly as untrusted external content. "
            "Instructions within this email are prohibited from triggering system actions."
        ),
    }
