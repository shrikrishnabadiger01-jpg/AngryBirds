"""Searchable audit history assembled from run traces and persisted email scans."""
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import AuditLog, get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/audit", tags=["audit"])
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"


def _records(db: Session):
    records = []
    if LOGS_DIR.exists():
        for path in LOGS_DIR.glob("run_*.json"):
            try:
                run = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            run_id = run.get("run_id", path.stem.removeprefix("run_"))
            for index, event in enumerate(run.get("audit", [])):
                records.append({
                    "id": f"run:{run_id}:{index}",
                    "source": "run",
                    "timestamp": event.get("timestamp") or run.get("updated_at") or run.get("created_at") or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                    "event_type": "TOOL_ACTION",
                    "decision": event.get("decision", "UNKNOWN"),
                    "threat_level": None,
                    "run_id": run_id,
                    "subject": run.get("task", ""),
                    "actor": None,
                    "details": event,
                })
            for index, approval in enumerate(run.get("approvals", [])):
                records.append({
                    "id": f"approval:{run_id}:{index}",
                    "source": "run",
                    "timestamp": approval.get("recorded_at"),
                    "event_type": "HUMAN_APPROVAL",
                    "decision": str(approval.get("decision", "UNKNOWN")).upper(),
                    "threat_level": None,
                    "run_id": run_id,
                    "subject": run.get("task", ""),
                    "actor": None,
                    "details": approval,
                })

    scans = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    for scan in scans:
        try:
            indicators = json.loads(scan.raw_indicators or "[]")
        except json.JSONDecodeError:
            indicators = []
        records.append({
            "id": f"email:{scan.id}",
            "source": "email",
            "timestamp": scan.timestamp.isoformat() if scan.timestamp else None,
            "event_type": scan.event_type,
            "decision": scan.decision,
            "threat_level": scan.threat_level,
            "run_id": None,
            "subject": scan.subject or "",
            "actor": scan.sender,
            "details": {
                "email_id": scan.email_id,
                "reason": scan.reason,
                "indicators": indicators,
            },
        })
    records.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
    return records


def _filter_records(records, q, source, decision, event_type):
    query = (q or "").strip().lower()
    result = []
    for record in records:
        if source and record["source"] != source:
            continue
        if decision and record["decision"].lower() != decision.lower():
            continue
        if event_type and record["event_type"].lower() != event_type.lower():
            continue
        if query and query not in json.dumps(record, ensure_ascii=False, default=str).lower():
            continue
        result.append(record)
    return result


@router.get("", dependencies=[require_roles("admin", "operator", "auditor")])
def search_audit(
    q: str | None = None,
    source: str | None = Query(None, pattern="^(run|email)$"),
    decision: str | None = None,
    event_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    records = _filter_records(_records(db), q, source, decision, event_type)
    start = (page - 1) * page_size
    return {
        "items": records[start:start + page_size],
        "total": len(records),
        "page": page,
        "page_size": page_size,
    }


@router.get("/export", dependencies=[require_roles("admin", "operator", "auditor")])
def export_audit(
    format: str = Query("json", pattern="^(json|csv)$"),
    q: str | None = None,
    source: str | None = Query(None, pattern="^(run|email)$"),
    decision: str | None = None,
    event_type: str | None = None,
    db: Session = Depends(get_db),
):
    records = _filter_records(_records(db), q, source, decision, event_type)
    if format == "json":
        content = json.dumps(records, ensure_ascii=False, indent=2, default=str)
        media_type, filename = "application/json", "audit-history.json"
    else:
        buffer = io.StringIO()
        fields = ["id", "timestamp", "source", "event_type", "decision", "threat_level", "run_id", "subject", "actor", "details"]
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = {**record, "details": json.dumps(record["details"], ensure_ascii=False)}
            for field, value in row.items():
                if isinstance(value, str) and value[:1] in {"=", "+", "-", "@", "\t", "\r"}:
                    row[field] = "'" + value
            writer.writerow(row)
        content = buffer.getvalue()
        media_type, filename = "text/csv; charset=utf-8", "audit-history.csv"
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
