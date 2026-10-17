"""Workspace adapter that sends approved email actions through Gmail."""
import hashlib
import json
from datetime import datetime, timezone

from app.services import gmail_service
from core.email_security import analyze_email_content
from workspace.simulated import SimWorkspace

GMAIL_SEND_SCOPE = ("https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.send")
GMAIL_READ_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class GmailWorkspace(SimWorkspace):
    """Keep document reads scoped while executing approved mail through Gmail."""

    def __init__(self, documents_path=None):
        super().__init__(documents_path)
        self._send_attempts = set()

    def preview(self, policy, tool, arguments):
        allowed, reason, fingerprint = super().preview(policy, tool, arguments)
        if not allowed or tool != "send_email":
            return allowed, reason, fingerprint

        if not gmail_service.has_scope(GMAIL_SEND_SCOPE):
            return False, "Gmail send access has not been granted", fingerprint

        if fingerprint in self._send_attempts:
            return False, "Duplicate email blocked", fingerprint

        if policy.max_emails is not None and len(self._send_attempts) >= policy.max_emails:
            return False, "Email limit reached for this run", fingerprint

        return True, "Action permitted by task policy and Gmail authorization", fingerprint

    def execute(self, policy, tool, arguments):
        if tool == "read_email":
            allowed, reason, _ = self.preview(policy, tool, arguments)
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": tool,
                "arguments": {"email_id": arguments.get("email_id")},
                "decision": "ALLOW" if allowed else "BLOCK",
                "reason": reason,
                "executed": False,
            }
            self.audit.append(event)
            if not allowed:
                return {"status": "blocked", "reason": reason}
            if not gmail_service.has_scope(GMAIL_READ_SCOPE):
                event["decision"] = "BLOCK"
                event["reason"] = "Gmail read access is unavailable"
                return {"status": "blocked", "reason": event["reason"]}
            try:
                email = gmail_service.fetch_single_email(arguments["email_id"])
            except Exception as exc:
                event["decision"] = "ERROR"
                event["reason"] = str(exc)
                return {"status": "error", "reason": str(exc)}
            security = analyze_email_content(
                email.get("subject", ""), email.get("body") or email.get("snippet", "")
            )
            event["action_decision"] = "ALLOW"
            event["security_decision"] = (
                "SUSPICIOUS" if security["decision"] != "ALLOW" else "ALLOW"
            )
            event["threat_level"] = security["threat_level"]
            event["security_reason"] = security["reason"]
            event["indicators"] = security["indicators"]
            event["prompt_injection_signals"] = security["prompt_injection_signals"]
            event["reason"] = (
                "Read permitted for inspection. " + security["reason"]
                if security["decision"] != "ALLOW"
                else "Read permitted; no known phishing or prompt-injection signals detected."
            )
            event["decision"] = event["security_decision"]
            event["executed"] = True
            return {
                "status": "ok",
                "trust": "untrusted_external_content",
                "email": email,
                "security": security,
            }

        if tool != "send_email":
            return super().execute(policy, tool, arguments)

        allowed, reason, fingerprint = self.preview(policy, tool, arguments)
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "arguments": dict(arguments) if isinstance(arguments, dict) else {"invalid_input": repr(arguments)},
            "decision": "ALLOW" if allowed else "BLOCK",
            "reason": reason,
            "executed": False,
        }
        self.audit.append(event)
        if not allowed:
            return {"status": "blocked", "reason": reason}

        # Reserve this message before the network call. If the request times out
        # after Gmail accepted it, the same run cannot accidentally retry it.
        self._send_attempts.add(fingerprint)
        try:
            sent = gmail_service.send_email(
                recipient=arguments["recipient"],
                subject=arguments["subject"],
                body=arguments["body"],
            )
        except Exception as exc:
            event["decision"] = "ERROR"
            event["reason"] = str(exc)
            return {"status": "error", "reason": str(exc)}

        self._sent_fingerprints.add(fingerprint)
        record = {
            **arguments,
            "gmail_message_id": sent.get("message_id"),
            "gmail_thread_id": sent.get("thread_id"),
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "status": "sent",
        }
        self.outbox.append(record)
        event["executed"] = True
        event["gmail_message_id"] = sent.get("message_id")
        return {"status": "ok", "message": "Email sent through Gmail", **sent}
