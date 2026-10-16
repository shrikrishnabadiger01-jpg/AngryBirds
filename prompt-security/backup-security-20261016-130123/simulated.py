import json
from pathlib import Path

from core.security import check_action


class SimWorkspace:
    def __init__(self):
        path = Path(__file__).resolve().parent.parent / "data" / "documents.json"
        self._documents = json.loads(path.read_text(encoding="utf-8-sig"))
        self.outbox = []
        self.audit = []

    def execute(self, policy, tool, arguments):
        allowed, reason = check_action(policy, tool, arguments)

        event = {
            "tool": tool,
            "arguments": dict(arguments),
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
            event["executed"] = True
            return {"status": "ok", "message": "Email saved to simulated outbox"}
