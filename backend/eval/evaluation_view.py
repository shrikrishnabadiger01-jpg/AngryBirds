import csv
import io
import json
from pathlib import Path


def load_comparisons(logs_dir: Path):
    rows, errors = [], []
    if not logs_dir.exists():
        return rows, errors

    for path in sorted(logs_dir.glob("comparison_*.json"), reverse=True):
        try:
            comparison = json.loads(path.read_text(encoding="utf-8-sig"))
            runs = comparison.get("runs", [])
            if not isinstance(runs, list) or not runs:
                continue
            for run in runs:
                audit = run.get("audit", [])
                rows.append({
                    "comparison_id": comparison.get("comparison_id"),
                    "recorded_at": comparison.get("started_at"),
                    "document": comparison.get("document"),
                    "task": comparison.get("task"),
                    "mode": run.get("mode"),
                    "status": run.get("status"),
                    "unauthorized_executed": run.get("unauthorized_actions_executed", 0),
                    "blocked_calls": sum(1 for e in audit if e.get("decision") == "BLOCK"),
                    "simulated_emails": len(run.get("outbox", [])),
                    "marker_in_answer": run.get("secret_marker_in_answer", False),
                    "marker_sent_to_attacker": run.get("secret_marker_sent_to_attacker", False),
                    "log_file": path.name,
                })
        except Exception as exc:
            errors.append(f"{path.name}: {type(exc).__name__}")

    return rows, errors


def export_comparisons_csv(logs_dir: Path) -> str:
    rows, _ = load_comparisons(logs_dir)
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
