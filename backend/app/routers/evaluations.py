from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.schemas import ComparisonRequest
from app.auth import require_roles
from core.security import TaskPolicy
from eval.comparison import run_gate_comparison
from eval.evaluation_view import load_comparisons, export_comparisons_csv

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])

LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"


@router.get("", dependencies=[require_roles("admin", "operator", "auditor")])
def get_evaluations():
    rows, errors = load_comparisons(LOGS_DIR)
    total_runs = len(rows)
    completed_runs = sum(1 for r in rows if r.get("status") == "completed")
    blocked_calls = sum(r.get("blocked_calls", 0) for r in rows)
    unauthorized_executed = sum(r.get("unauthorized_executed", 0) for r in rows)
    marker_leaked = sum(1 for r in rows if r.get("marker_sent_to_attacker") or r.get("marker_in_answer"))

    return {
        "metrics": {
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "error_runs": total_runs - completed_runs,
            "blocked_calls": blocked_calls,
            "unauthorized_executed": unauthorized_executed,
            "marker_leaked": marker_leaked,
        },
        "rows": rows,
        "errors": errors,
    }


@router.post("/compare", dependencies=[require_roles("admin", "operator")])
def run_comparison(req: ComparisonRequest):
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="Task text cannot be empty")

    policy = TaskPolicy(
        allowed_tools=frozenset({"read_doc", "send_email"} if req.allow_email else {"read_doc"}),
        allowed_documents=frozenset({req.document_id}),
        allowed_recipients=frozenset({"manager@example.com"} if req.allow_email else set()),
        max_emails=1 if req.allow_email else 0
    )

    comparison = run_gate_comparison(req.task, req.document_id, policy, LOGS_DIR)
    return comparison


@router.get("/export-csv", dependencies=[require_roles("admin", "operator", "auditor")])
def export_csv():
    csv_content = export_comparisons_csv(LOGS_DIR)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=evaluations_report.csv"}
    )
