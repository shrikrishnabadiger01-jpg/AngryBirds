import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
from fastapi import APIRouter, HTTPException

from agent.approval import ApprovalRun
from app.schemas import RunTaskRequest, ApprovalDecisionRequest
from app.auth import require_roles
from core.inspector import inspect_content
from core.security import TaskPolicy
from workspace.simulated import SimWorkspace
from workspace.gmail import GmailWorkspace
from app.services import gmail_service

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "documents.json"

# In-memory registry of active and completed runs
RUNS: Dict[str, ApprovalRun] = {}


def _save_run_log(run: ApprovalRun):
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOGS_DIR / f"run_{run.run_id}.json"
        log_path.write_text(json.dumps(run.to_dict(), indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Error saving run log: {e}")


@router.get("/documents", dependencies=[require_roles("admin", "operator", "auditor")])
def get_documents():
    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="Documents file not found")
    data = json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))

    results = []
    for doc_id, item in data.items():
        if doc_id == "confidential_budget" or item.get("is_confidential"):
            continue
        content = item.get("content", "")
        findings = inspect_content(content)
        results.append({
            "id": doc_id,
            "title": item.get("title", doc_id.replace("_", " ").title()),
            "content": content,
            "is_confidential": doc_id == "confidential_budget",
            "findings_count": len(findings),
            "findings": findings,
        })
    return results


@router.post("/run", dependencies=[require_roles("admin", "operator")])
def start_task_run(req: RunTaskRequest):
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="Task text cannot be empty")

    if req.allow_email:
        gmail_status = gmail_service.get_connection_status()
        if not gmail_status.get("connected"):
            raise HTTPException(status_code=409, detail="Connect Gmail before enabling email sending.")
        if not gmail_status.get("can_send"):
            raise HTTPException(status_code=403, detail="Gmail send access is missing. Reconnect Gmail and grant the send permission.")
    if req.email_id:
        gmail_status = gmail_service.get_connection_status()
        if not gmail_status.get("connected") or not gmail_service.has_scope("https://www.googleapis.com/auth/gmail.readonly"):
            raise HTTPException(status_code=403, detail="Connect Gmail with read access before summarizing an email.")
        allowed_tools = {"read_email"}
    else:
        allowed_tools = {"read_doc"}
    if req.allow_email:
        allowed_tools.add("send_email")
    known_documents = json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))
    requested_documents = set(req.allowed_documents or [req.document_id])
    requested_documents.add(req.document_id)
    unknown_documents = requested_documents - set(known_documents)
    confidential_documents = {
        doc_id for doc_id in requested_documents
        if known_documents.get(doc_id, {}).get("is_confidential") or doc_id == "confidential_budget"
    }
    if unknown_documents or confidential_documents:
        raise HTTPException(status_code=422, detail="Policy document scope contains unknown or restricted documents")

    recipient_values = req.allowed_recipients
    if recipient_values is None:
        recipient_values = [req.recipient] if req.recipient else []
    allowed_recipients = {
        address.strip().lower() for address in recipient_values
        if isinstance(address, str) and address.strip()
    } if req.allow_email else set()
    if req.allow_email and not allowed_recipients:
        raise HTTPException(status_code=422, detail="Email permission requires at least one allowed recipient")
    if req.allow_email and any(
        len(address) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", address)
        for address in allowed_recipients
    ):
        raise HTTPException(status_code=422, detail="Policy contains an invalid email recipient")

    policy = TaskPolicy(
        allowed_tools=frozenset(allowed_tools),
        allowed_documents=frozenset(requested_documents),
        allowed_recipients=frozenset(allowed_recipients),
        max_emails=req.max_emails if req.allow_email else 0,
        required_subject=req.required_subject or None,
        allowed_email_ids=frozenset({req.email_id}) if req.email_id else frozenset(),
    )

    workspace = GmailWorkspace(DATA_FILE) if req.allow_email or req.email_id else SimWorkspace(DATA_FILE)
    run = ApprovalRun(req.task, req.document_id, policy, workspace)
    RUNS[run.run_id] = run

    try:
        run.start()
    except Exception as e:
        _save_run_log(run)
        return run.to_dict()

    _save_run_log(run)
    return run.to_dict()


@router.get("/run/{run_id}", dependencies=[require_roles("admin", "operator", "auditor")])
def get_run_status(run_id: str):
    run = RUNS.get(run_id)
    if run:
        return run.to_dict()

    # Check disk logs
    log_path = LOGS_DIR / f"run_{run_id}.json"
    if log_path.exists():
        try:
            return json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@router.post("/run/{run_id}/approval", dependencies=[require_roles("admin", "operator")])
def handle_approval(run_id: str, req: ApprovalDecisionRequest):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Active run {run_id} not found")

    if run.status != "awaiting_approval":
        raise HTTPException(status_code=400, detail=f"Run is not awaiting approval (status: {run.status})")

    try:
        run.resolve(req.token, req.approved)
    except Exception as e:
        _save_run_log(run)
        raise HTTPException(status_code=400, detail=str(e))

    _save_run_log(run)
    return run.to_dict()


@router.post("/run/{run_id}/cancel", dependencies=[require_roles("admin", "operator")])
def cancel_run(run_id: str):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    run.cancel()
    _save_run_log(run)
    return run.to_dict()


@router.get("/runs", dependencies=[require_roles("admin", "operator", "auditor")])
def list_runs():
    results = []
    if LOGS_DIR.exists():
        for path in sorted(LOGS_DIR.glob("run_*.json"), reverse=True)[:25]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                results.append({
                    "run_id": data.get("run_id"),
                    "status": data.get("status"),
                    "task": data.get("task"),
                    "document": data.get("document"),
                    "audit_events": len(data.get("audit", [])),
                    "outbox_count": len(data.get("outbox", [])),
                })
            except Exception:
                pass
    return results
