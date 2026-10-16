"""Server-session approval state for Human-in-the-Loop email execution."""
import hashlib
import json
import secrets
import time
from datetime import datetime, timezone
from uuid import uuid4
from agent.runner import _steps
from core.security import TaskPolicy


class ApprovalRun:
    def __init__(self, task: str, document_id: str, policy: TaskPolicy, workspace):
        self.run_id = uuid4().hex
        self.task = task
        self.document_id = document_id
        self.policy = policy
        self.workspace = workspace
        self.status = "ready"
        self.answer = None
        self.error = None
        self.pending = None
        self.approvals = []
        self._steps = _steps(task, document_id, policy, workspace, require_approval=True)

    def _advance(self, decision=None, first=False):
        try:
            payload = next(self._steps) if first else self._steps.send(decision)
            self.pending = {
                "token": secrets.token_urlsafe(24),
                "payload": payload,
                "digest": hashlib.sha256(payload.encode()).hexdigest(),
                "expires": time.monotonic() + 600,
            }
            self.status = "awaiting_approval"
        except StopIteration as done:
            self.answer = done.value
            self.status = "completed"
            self.pending = None
        except Exception as exc:
            self.status = "error"
            self.error = str(exc)
            self.pending = None
            if hasattr(self._steps, "close"):
                self._steps.close()
            raise exc

    def start(self):
        if self.status != "ready":
            raise ValueError("Run has already started")
        self._advance(first=True)

    def proposal(self):
        if self.pending is None:
            return None
        return json.loads(self.pending["payload"])

    def resolve(self, token: str, approved: bool):
        if type(approved) is not bool:
            raise ValueError("Decision must be a boolean")
        if self.status != "awaiting_approval" or self.pending is None:
            raise ValueError("No pending approval")
        if not secrets.compare_digest(token, self.pending["token"]):
            raise ValueError("Approval token does not match pending call")
        if hashlib.sha256(self.pending["payload"].encode()).hexdigest() != self.pending["digest"]:
            self.cancel()
            raise ValueError("Pending call altered; run cancelled")
        expired = time.monotonic() > self.pending["expires"]
        approved = approved and not expired
        self.approvals.append({
            "run_id": self.run_id,
            "payload_sha256": self.pending["digest"],
            "decision": "expired" if expired else "approved" if approved else "denied",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
        self.pending = None
        self.status = "running"
        self._advance(approved)

    def cancel(self):
        self.pending = None
        self.status = "cancelled"
        if hasattr(self._steps, "close"):
            self._steps.close()

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "status": self.status,
            "task": self.task,
            "document": self.document_id,
            "answer": self.answer,
            "error": self.error,
            "pending_approval": {
                "token": self.pending["token"],
                "proposal": self.proposal(),
                "expires_in": max(0, int(self.pending["expires"] - time.monotonic()))
            } if self.pending else None,
            "approvals": self.approvals,
            "audit": self.workspace.audit,
            "outbox": self.workspace.outbox,
            "policy": {
                "allowed_tools": sorted(self.policy.allowed_tools),
                "allowed_documents": sorted(self.policy.allowed_documents),
                "allowed_recipients": sorted(self.policy.allowed_recipients),
                "max_emails": self.policy.max_emails,
                "required_subject": self.policy.required_subject,
            }
        }
