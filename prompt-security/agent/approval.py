"""Server-session approval state. Never accepts replacement call arguments."""
import hashlib
import json
import secrets
import time
from datetime import datetime, timezone
from uuid import uuid4
from agent.runner import _steps


class ApprovalRun:
    def __init__(self, task, document_id, policy, workspace, require_approval=True):
        self.require_approval = require_approval
        self.run_id = workspace.run_id
        self.task = task
        self.document_id = document_id
        self.policy = policy
        self.workspace = workspace
        self.status = 'ready'
        self.answer = None
        self.error = None
        self.pending = None
        self.approvals = []
        self._steps = _steps(task, document_id, policy, workspace, require_approval=require_approval)

    def _advance(self, decision=None, first=False):
        try:
            payload = next(self._steps) if first else self._steps.send(decision)
            self.pending = {
                'token': secrets.token_urlsafe(24),
                'payload': payload,
                'digest': hashlib.sha256(payload.encode()).hexdigest(),
                'expires': time.monotonic() + 600,
            }
            self.status = 'awaiting_approval'
        except StopIteration as done:
            self.answer = done.value
            self.status = 'completed'
            self.pending = None
        except Exception as exc:
            self.status = 'error'
            self.pending = None
            self._steps.close()
            raise exc

    def start(self):
        if self.status != 'ready':
            raise ValueError('Run has already started')
        self._advance(first=True)

    def proposal(self):
        if self.pending is None:
            return None
        # Fresh copy prevents display callers from changing the saved arguments.
        return json.loads(self.pending['payload'])

    def resolve(self, token, approved):
        if type(approved) is not bool:
            raise ValueError('Decision must be a boolean')
        if self.status != 'awaiting_approval' or self.pending is None:
            raise ValueError('No pending approval')
        if not secrets.compare_digest(token, self.pending['token']):
            raise ValueError('Approval does not belong to this pending call')
        if hashlib.sha256(self.pending['payload'].encode()).hexdigest() != self.pending['digest']:
            self.cancel()
            raise ValueError('Pending call changed; run cancelled')
        expired = time.monotonic() > self.pending['expires']
        approved = approved and not expired
        self.approvals.append({
            'run_id': self.run_id,
            'payload_sha256': self.pending['digest'],
            'decision': 'expired' if expired else 'approved' if approved else 'denied',
            'recorded_at': datetime.now(timezone.utc).isoformat(),
        })
        # Consume before resuming, including if the next model request fails.
        self.pending = None
        self.status = 'running'
        self._advance(approved)

    def cancel(self):
        self.pending = None
        self.status = 'cancelled'
        self._steps.close()
