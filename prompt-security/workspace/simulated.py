import hashlib
import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from workspace.ledger import EmailLedger

from core.security import check_action


class SimWorkspace:
    def __init__(self, ledger_path=None, run_id=None, documents=None):
        path = Path(__file__).resolve().parent.parent / "data" / "documents.json"
        self._documents = json.loads(path.read_text(encoding="utf-8-sig"))
        inbox_path = path.with_name("inbox_fixtures.json")
        if inbox_path.exists():
            self._documents.update(json.loads(inbox_path.read_text(encoding="utf-8")))
        if documents is not None:
            import copy
            self._documents.update(copy.deepcopy(documents))
        self.outbox = []
        self.audit = []
        self._sent_fingerprints = set()
        self.run_id = run_id or uuid4().hex
        self.sources = {}
        self.requests = []
        self.metadata = {}
        self.on_progress = None
        self.ledger = EmailLedger(ledger_path) if ledger_path else None
        if self.ledger:
            self.outbox = self.ledger.emails(self.run_id)
            self._sent_fingerprints = {self.fingerprint(e) for e in self.outbox}

    def notify(self, message):
        if self.on_progress:
            self.on_progress(message)

    @staticmethod
    def fingerprint(arguments):
        return hashlib.sha256(json.dumps(arguments, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


    def preview(self, policy, tool, arguments):
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

        if allowed and tool == 'send_email':
            if policy.require_source_read and not self.sources:
                return False, 'Read an authorized source before emailing', fingerprint
            if policy.block_restricted_egress and any(s['classification'] == 'restricted' for s in self.sources.values()):
                return False, 'Restricted source was read; external email is disabled for this run', fingerprint
        return allowed, reason, fingerprint

    def execute(self, policy, tool, arguments):
        allowed, reason, fingerprint = self.preview(policy, tool, arguments)

        event = {
            "event_id": uuid4().hex,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "source_documents": sorted(self.sources),
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

        if tool in {"read_doc", "read_email"}:
            source_id = arguments["email_id" if tool == "read_email" else "doc_id"]
            document = self._documents.get(source_id)

            if document is None:
                return {"status": "error", "reason": "Document not found"}

            self.sources[source_id] = {
                'sha256': hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest(),
                'classification': document.get('classification', 'internal'),
                'trust': 'untrusted_external_content',
            }
            event['source_documents'] = sorted(self.sources)
            event["executed"] = True
            return {
                "source_id": source_id,
                "status": "ok",
                "trust": "untrusted_external_content",
                "document": dict(document),
            }

        if tool == "send_email":
            if self.ledger:
                committed, reason = self.ledger.commit(self.run_id, fingerprint, arguments, policy.max_emails)
                if not committed:
                    event.update(decision='BLOCK', reason=reason)
                    return {'status': 'blocked', 'reason': reason}
                self.outbox = self.ledger.emails(self.run_id)
            else:
                self.outbox.append(dict(arguments))
            self._sent_fingerprints.add(fingerprint)
            event["executed"] = True
            return {
                "status": "ok",
                "message": "Email saved to simulated outbox",
            }
