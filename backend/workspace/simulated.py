import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from core.security import check_action, TaskPolicy


class SimWorkspace:
    def __init__(self, documents_path=None):
        if documents_path is None:
            documents_path = Path(__file__).resolve().parent.parent / "data" / "documents.json"
        self._documents = json.loads(Path(documents_path).read_text(encoding="utf-8-sig"))
        self.outbox = []
        self.audit = []
        self._sent_fingerprints = set()

    def get_documents(self):
        return self._documents

    def preview(self, policy: TaskPolicy, tool: str, arguments: dict):
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

        return allowed, reason, fingerprint

    def execute(self, policy: TaskPolicy, tool: str, arguments: dict):
        allowed, reason, fingerprint = self.preview(policy, tool, arguments)

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
            document = self._documents.get(arguments.get("doc_id"))

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

        return {"status": "error", "reason": f"Unhandled tool {tool}"}


class GateDisabledWorkspace(SimWorkspace):
    """Evaluation only: permissions disabled; tool validation retained."""

    def execute(self, policy: TaskPolicy, tool: str, arguments: dict):
        permitted, reason = check_action(policy, tool, arguments)

        evaluation_policy = TaskPolicy(
            max_emails=None,
            allowed_tools=frozenset({"read_doc", "send_email"}),
            allowed_documents=frozenset(self._documents),
            allowed_recipients=frozenset(
                [arguments["recipient"]]
                if isinstance(arguments.get("recipient"), str)
                else []
            ),
        )

        result = super().execute(evaluation_policy, tool, arguments)
        event = self.audit[-1]
        event["gate_enabled"] = False
        event["original_policy_allowed"] = permitted
        event["original_policy_reason"] = reason

        if event["decision"] == "ALLOW":
            event["decision"] = "BYPASS"
            event["reason"] = "Permission enforcement disabled for evaluation"

        return result
