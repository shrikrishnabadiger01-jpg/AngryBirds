import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
from fastapi import APIRouter, HTTPException

from agent.approval import ApprovalRun
from app.schemas import RunTaskRequest, ApprovalDecisionRequest
from core.inspector import inspect_content
from core.security import TaskPolicy
from workspace.simulated import SimWorkspace

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


@router.get("/documents")
def get_documents():
    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="Documents file not found")
    data = json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))

    results = []
    for doc_id, item in data.items():
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


@router.post("/run")
def start_task_run(req: RunTaskRequest):
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="Task text cannot be empty")

    allowed_tools = {"read_doc", "send_email"} if req.allow_email else {"read_doc"}
    allowed_recipients = {req.recipient.strip()} if req.allow_email and req.recipient else set()

    policy = TaskPolicy(
        allowed_tools=frozenset(allowed_tools),
        allowed_documents=frozenset({req.document_id}),
        allowed_recipients=frozenset(allowed_recipients),
        max_emails=1 if req.allow_email else 0
    )

    workspace = SimWorkspace(DATA_FILE)
    run = ApprovalRun(req.task, req.document_id, policy, workspace)
    RUNS[run.run_id] = run

    try:
        run.start()
    except Exception as e:
        _save_run_log(run)
        return run.to_dict()

    _save_run_log(run)
    return run.to_dict()


@router.get("/run/{run_id}")
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


@router.post("/run/{run_id}/approval")
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


@router.post("/run/{run_id}/cancel")
def cancel_run(run_id: str):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    run.cancel()
    _save_run_log(run)
    return run.to_dict()


@router.get("/runs")
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
