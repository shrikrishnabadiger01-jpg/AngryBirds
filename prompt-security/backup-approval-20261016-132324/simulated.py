import hashlib
import json
from pathlib import Path

from core.security import check_action


class SimWorkspace:
    def __init__(self):
        path = Path(__file__).resolve().parent.parent / "data" / "documents.json"
        self._documents = json.loads(path.read_text(encoding="utf-8-sig"))
        self.outbox = []
        self.audit = []
        self._sent_fingerprints = set()

    def execute(self, policy, tool, arguments):
        allowed, reason = check_action(policy, tool, arguments)
        fingerprint = None

        if allowed and tool == "send_email":
            fingerprint = hashlib.sha256(
                json.dumps(
                    arguments, sort_keys=True, ensure_ascii=False
                ).encode("utf-8")
            ).hexdigest()

            if fingerprint in self._sent_fingerprints:
                allowed = False
                reason = "Duplicate email blocked"
            elif (
                policy.max_emails is not None
                and len(self.outbox) >= policy.max_emails
            ):
                allowed = False
                reason = "Email limit reached for this run"

        event = {
            "tool": tool,
            "arguments": (
                dict(arguments)
                if isinstance(arguments, dict)
                else {"invalid_input": repr(arguments)}
            ),
            "decision": "ALLOW" if allowed else "BLOCK",
            "reason": reason,
            "executed": False,
        }
        self.audit.append(event)

        if not allowed:
            return {"status": "blocked", "reason": reason}

        if tool == "read_doc":
            document = self._documents.get(arguments["doc_id"])

            if document is None:
                return {"status": "error", "reason": "Document not found"}

            event["executed"] = True
            return {
                "status": "ok",
                "trust": "untrusted_external_content",
                "document": dict(document),
            }

        if tool == "send_email":
            self.outbox.append(dict(arguments))
            self._sent_fingerprints.add(fingerprint)
            event["executed"] = True
            return {
                "status": "ok",
                "message": "Email saved to simulated outbox",
            }
